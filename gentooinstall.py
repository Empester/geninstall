#!/usr/bin/env python3
"""
gentooinstall - A guided installer for Gentoo Linux
Inspired by archinstall's architecture and design principles
"""

import os
import sys
import json
import subprocess
import shutil
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum


# ============================================================================
# CONFIGURATION CLASSES
# ============================================================================

class DiskEncryption(Enum):
    NONE = "none"
    LUKS = "luks"


class FilesystemType(Enum):
    EXT4 = "ext4"
    BTRFS = "btrfs"
    XFS = "xfs"
    F2FS = "f2fs"


class BootloaderType(Enum):
    GRUB = "grub"
    SYSTEMD_BOOT = "systemd-boot"


class ProfileType(Enum):
    DESKTOP = "desktop"
    SERVER = "server"
    MINIMAL = "minimal"


class InitSystem(Enum):
    OPENRC = "openrc"
    SYSTEMD = "systemd"


@dataclass
class DiskConfig:
    device: str
    boot_partition: str
    root_partition: str
    swap_partition: Optional[str] = None
    filesystem: FilesystemType = FilesystemType.EXT4
    encryption: DiskEncryption = DiskEncryption.NONE
    encryption_password: Optional[str] = None


@dataclass
class SystemConfig:
    hostname: str
    timezone: str
    locale: str = "en_US.UTF-8"
    keymap: str = "us"


@dataclass
class UserConfig:
    username: str
    password: str
    shell: str = "/bin/bash"
    groups: List[str] = None

    def __post_init__(self):
        if self.groups is None:
            self.groups = ["wheel", "audio", "video", "usb", "users"]


@dataclass
class InstallConfig:
    disk_config: DiskConfig
    system_config: SystemConfig
    root_password: str
    users: List[UserConfig]
    bootloader: BootloaderType = BootloaderType.GRUB
    init_system: InitSystem = InitSystem.OPENRC
    profile: ProfileType = ProfileType.MINIMAL
    stage3_mirror: str = "https://distfiles.gentoo.org/releases/amd64/autobuilds"
    additional_packages: List[str] = None
    kernel_config: str = "genkernel"
    make_opts: str = "-j$(nproc)"

    def __post_init__(self):
        if self.additional_packages is None:
            self.additional_packages = []


# ============================================================================
# LOGGING SETUP
# ============================================================================

class GentooInstallLogger:
    def __init__(self, log_dir: str = "/var/log/gentooinstall"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_dir / "install.log"
        
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger("gentooinstall")

    def info(self, msg: str):
        self.logger.info(msg)

    def error(self, msg: str):
        self.logger.error(msg)

    def debug(self, msg: str):
        self.logger.debug(msg)

    def warning(self, msg: str):
        self.logger.warning(msg)


logger = GentooInstallLogger()


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def run_command(cmd: List[str], check: bool = True, capture: bool = False) -> subprocess.CompletedProcess:
    """Execute a shell command with logging"""
    logger.debug(f"Executing: {' '.join(cmd)}")
    try:
        if capture:
            result = subprocess.run(cmd, check=check, capture_output=True, text=True)
            logger.debug(f"Output: {result.stdout}")
            return result
        else:
            return subprocess.run(cmd, check=check)
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed: {' '.join(cmd)}")
        logger.error(f"Error: {e}")
        if check:
            raise
        return e


def chroot_command(mount_point: str, cmd: List[str]) -> subprocess.CompletedProcess:
    """Execute command in chroot environment"""
    chroot_cmd = ["chroot", mount_point] + cmd
    return run_command(chroot_cmd)


def is_uefi() -> bool:
    """Check if system is booted in UEFI mode"""
    return Path("/sys/firmware/efi").exists()


def download_file(url: str, destination: str):
    """Download file using wget"""
    run_command(["wget", "-O", destination, url])


# ============================================================================
# DISK MANAGEMENT
# ============================================================================

class DiskManager:
    def __init__(self, config: DiskConfig):
        self.config = config

    def partition_disk(self):
        """Partition the disk"""
        logger.info(f"Partitioning disk: {self.config.device}")
        
        # Clear existing partitions
        run_command(["wipefs", "-a", self.config.device])
        
        if is_uefi():
            # GPT partition table for UEFI
            run_command(["parted", "-s", self.config.device, "mklabel", "gpt"])
            run_command(["parted", "-s", self.config.device, "mkpart", "ESP", "fat32", "1MiB", "512MiB"])
            run_command(["parted", "-s", self.config.device, "set", "1", "boot", "on"])
            
            if self.config.swap_partition:
                run_command(["parted", "-s", self.config.device, "mkpart", "swap", "linux-swap", "512MiB", "4GiB"])
                run_command(["parted", "-s", self.config.device, "mkpart", "root", "ext4", "4GiB", "100%"])
            else:
                run_command(["parted", "-s", self.config.device, "mkpart", "root", "ext4", "512MiB", "100%"])
        else:
            # MBR partition table for BIOS
            run_command(["parted", "-s", self.config.device, "mklabel", "msdos"])
            run_command(["parted", "-s", self.config.device, "mkpart", "primary", "1MiB", "512MiB"])
            
            if self.config.swap_partition:
                run_command(["parted", "-s", self.config.device, "mkpart", "primary", "linux-swap", "512MiB", "4GiB"])
                run_command(["parted", "-s", self.config.device, "mkpart", "primary", "ext4", "4GiB", "100%"])
            else:
                run_command(["parted", "-s", self.config.device, "mkpart", "primary", "ext4", "512MiB", "100%"])

        logger.info("Disk partitioning completed")

    def setup_encryption(self):
        """Setup LUKS encryption if configured"""
        if self.config.encryption == DiskEncryption.LUKS:
            logger.info("Setting up LUKS encryption")
            
            # Format LUKS partition
            proc = subprocess.Popen(
                ["cryptsetup", "luksFormat", self.config.root_partition],
                stdin=subprocess.PIPE,
                text=True
            )
            proc.communicate(input=f"{self.config.encryption_password}\n")
            
            # Open LUKS partition
            proc = subprocess.Popen(
                ["cryptsetup", "open", self.config.root_partition, "gentoo_root"],
                stdin=subprocess.PIPE,
                text=True
            )
            proc.communicate(input=f"{self.config.encryption_password}\n")
            
            # Update root partition to mapper device
            self.config.root_partition = "/dev/mapper/gentoo_root"
            logger.info("LUKS encryption setup completed")

    def format_partitions(self):
        """Format all partitions"""
        logger.info("Formatting partitions")
        
        # Format boot partition
        if is_uefi():
            run_command(["mkfs.fat", "-F32", self.config.boot_partition])
        else:
            run_command(["mkfs.ext2", self.config.boot_partition])
        
        # Format swap if configured
        if self.config.swap_partition:
            run_command(["mkswap", self.config.swap_partition])
            run_command(["swapon", self.config.swap_partition])
        
        # Format root partition
        fs_type = self.config.filesystem.value
        if fs_type == "ext4":
            run_command(["mkfs.ext4", "-F", self.config.root_partition])
        elif fs_type == "btrfs":
            run_command(["mkfs.btrfs", "-f", self.config.root_partition])
        elif fs_type == "xfs":
            run_command(["mkfs.xfs", "-f", self.config.root_partition])
        elif fs_type == "f2fs":
            run_command(["mkfs.f2fs", "-f", self.config.root_partition])
        
        logger.info("Partition formatting completed")

    def mount_partitions(self, mount_point: str = "/mnt/gentoo"):
        """Mount all partitions"""
        logger.info(f"Mounting partitions at {mount_point}")
        
        # Create mount point
        Path(mount_point).mkdir(parents=True, exist_ok=True)
        
        # Mount root
        run_command(["mount", self.config.root_partition, mount_point])
        
        # Mount boot
        boot_mount = Path(mount_point) / "boot"
        boot_mount.mkdir(exist_ok=True)
        run_command(["mount", self.config.boot_partition, str(boot_mount)])
        
        logger.info("Partitions mounted successfully")


# ============================================================================
# STAGE3 INSTALLATION
# ============================================================================

class Stage3Installer:
    def __init__(self, config: InstallConfig, mount_point: str = "/mnt/gentoo"):
        self.config = config
        self.mount_point = mount_point

    def download_stage3(self):
        """Download and extract stage3 tarball"""
        logger.info("Downloading stage3 tarball")
        
        # Get latest stage3 URL
        if self.config.init_system == InitSystem.SYSTEMD:
            stage3_pattern = "stage3-amd64-systemd"
        else:
            stage3_pattern = "stage3-amd64-openrc"
        
        # For simplicity, using a recent stage3 - in production, parse latest-stage3.txt
        stage3_url = f"{self.config.stage3_mirror}/current-stage3-amd64/{stage3_pattern}-*.tar.xz"
        
        logger.info(f"Stage3 URL pattern: {stage3_url}")
        logger.info("Note: In production, parse latest-stage3.txt for exact URL")
        
        # Download (simplified - would need proper latest file detection)
        stage3_file = f"/tmp/{stage3_pattern}.tar.xz"
        
        logger.info("Extracting stage3 tarball")
        # Would download here in real implementation
        # For now, assume stage3 is available
        
        # Extract stage3
        run_command([
            "tar", "xpvf", stage3_file,
            "--xattrs-include='*.*'",
            "--numeric-owner",
            "-C", self.mount_point
        ])
        
        logger.info("Stage3 extraction completed")

    def configure_make_conf(self):
        """Configure /etc/portage/make.conf"""
        logger.info("Configuring make.conf")
        
        make_conf = Path(self.mount_point) / "etc/portage/make.conf"
        
        # Read existing make.conf
        content = make_conf.read_text()
        
        # Add/update MAKEOPTS
        if "MAKEOPTS" not in content:
            content += f'\nMAKEOPTS="{self.config.make_opts}"\n'
        
        # Add USE flags based on profile
        if self.config.profile == ProfileType.DESKTOP:
            if "USE" not in content:
                content += '\nUSE="X gtk qt5 alsa pulseaudio networkmanager"\n'
        
        make_conf.write_text(content)
        logger.info("make.conf configured")

    def setup_repos(self):
        """Setup Gentoo repositories"""
        logger.info("Setting up repositories")
        
        # Copy DNS info
        resolv_conf = Path(self.mount_point) / "etc/resolv.conf"
        shutil.copy("/etc/resolv.conf", resolv_conf)
        
        # Mount necessary filesystems
        run_command(["mount", "-t", "proc", "/proc", f"{self.mount_point}/proc"])
        run_command(["mount", "--rbind", "/sys", f"{self.mount_point}/sys"])
        run_command(["mount", "--make-rslave", f"{self.mount_point}/sys"])
        run_command(["mount", "--rbind", "/dev", f"{self.mount_point}/dev"])
        run_command(["mount", "--make-rslave", f"{self.mount_point}/dev"])
        run_command(["mount", "--bind", "/run", f"{self.mount_point}/run"])
        run_command(["mount", "--make-slave", f"{self.mount_point}/run"])
        
        # Sync portage tree
        logger.info("Syncing portage tree (this may take a while)...")
        chroot_command(self.mount_point, ["emerge-webrsync"])
        
        logger.info("Repository setup completed")


# ============================================================================
# SYSTEM CONFIGURATION
# ============================================================================

class SystemConfigurator:
    def __init__(self, config: InstallConfig, mount_point: str = "/mnt/gentoo"):
        self.config = config
        self.mount_point = mount_point

    def configure_locale(self):
        """Configure system locale"""
        logger.info("Configuring locale")
        
        # Configure locale.gen
        locale_gen = Path(self.mount_point) / "etc/locale.gen"
        content = locale_gen.read_text()
        
        # Uncomment selected locale
        locale = self.config.system_config.locale
        content = content.replace(f"#{locale}", locale)
        locale_gen.write_text(content)
        
        # Generate locales
        chroot_command(self.mount_point, ["locale-gen"])
        
        # Set system locale
        locale_conf = Path(self.mount_point) / "etc/locale.conf"
        locale_conf.write_text(f"LANG={locale}\n")
        
        logger.info("Locale configuration completed")

    def configure_timezone(self):
        """Configure system timezone"""
        logger.info(f"Setting timezone to {self.config.system_config.timezone}")
        
        timezone_src = f"/usr/share/zoneinfo/{self.config.system_config.timezone}"
        timezone_dst = Path(self.mount_point) / "etc/localtime"
        
        chroot_command(self.mount_point, ["ln", "-sf", timezone_src, "/etc/localtime"])
        chroot_command(self.mount_point, ["hwclock", "--systohc"])
        
        logger.info("Timezone configuration completed")

    def configure_network(self):
        """Configure networking"""
        logger.info("Configuring network")
        
        # Set hostname
        hostname_file = Path(self.mount_point) / "etc/hostname"
        hostname_file.write_text(f"{self.config.system_config.hostname}\n")
        
        # Configure hosts file
        hosts_file = Path(self.mount_point) / "etc/hosts"
        hosts_content = f"""127.0.0.1    localhost
::1          localhost
127.0.1.1    {self.config.system_config.hostname}.localdomain {self.config.system_config.hostname}
"""
        hosts_file.write_text(hosts_content)
        
        logger.info("Network configuration completed")

    def configure_fstab(self):
        """Generate and configure fstab"""
        logger.info("Generating fstab")
        
        # Generate fstab
        result = run_command(["genfstab", "-U", self.mount_point], capture=True)
        
        fstab_file = Path(self.mount_point) / "etc/fstab"
        fstab_file.write_text(result.stdout)
        
        logger.info("fstab generated")

    def create_users(self):
        """Create user accounts"""
        logger.info("Creating user accounts")
        
        # Set root password
        proc = subprocess.Popen(
            ["chroot", self.mount_point, "passwd"],
            stdin=subprocess.PIPE,
            text=True
        )
        proc.communicate(input=f"{self.config.root_password}\n{self.config.root_password}\n")
        
        # Create users
        for user in self.config.users:
            logger.info(f"Creating user: {user.username}")
            
            chroot_command(self.mount_point, [
                "useradd", "-m", "-G", ",".join(user.groups),
                "-s", user.shell, user.username
            ])
            
            # Set user password
            proc = subprocess.Popen(
                ["chroot", self.mount_point, "passwd", user.username],
                stdin=subprocess.PIPE,
                text=True
            )
            proc.communicate(input=f"{user.password}\n{user.password}\n")
        
        logger.info("User creation completed")


# ============================================================================
# KERNEL INSTALLATION
# ============================================================================

class KernelInstaller:
    def __init__(self, config: InstallConfig, mount_point: str = "/mnt/gentoo"):
        self.config = config
        self.mount_point = mount_point

    def install_kernel(self):
        """Install and configure kernel"""
        logger.info("Installing kernel")
        
        if self.config.kernel_config == "genkernel":
            self.install_with_genkernel()
        else:
            self.install_manual_kernel()

    def install_with_genkernel(self):
        """Install kernel using genkernel"""
        logger.info("Installing kernel with genkernel")
        
        # Install kernel sources
        chroot_command(self.mount_point, ["emerge", "sys-kernel/gentoo-sources"])
        
        # Install genkernel
        chroot_command(self.mount_point, ["emerge", "sys-kernel/genkernel"])
        
        # Generate kernel
        chroot_command(self.mount_point, ["genkernel", "all"])
        
        logger.info("Kernel installation completed")

    def install_manual_kernel(self):
        """Install kernel manually"""
        logger.info("Installing kernel manually")
        
        # Install kernel sources
        chroot_command(self.mount_point, ["emerge", "sys-kernel/gentoo-sources"])
        
        # This would require manual configuration
        logger.warning("Manual kernel configuration requires user interaction")
        logger.info("Kernel sources installed")


# ============================================================================
# BOOTLOADER INSTALLATION
# ============================================================================

class BootloaderInstaller:
    def __init__(self, config: InstallConfig, mount_point: str = "/mnt/gentoo"):
        self.config = config
        self.mount_point = mount_point

    def install_bootloader(self):
        """Install configured bootloader"""
        if self.config.bootloader == BootloaderType.GRUB:
            self.install_grub()
        elif self.config.bootloader == BootloaderType.SYSTEMD_BOOT:
            self.install_systemd_boot()

    def install_grub(self):
        """Install GRUB bootloader"""
        logger.info("Installing GRUB")
        
        # Install GRUB package
        if is_uefi():
            chroot_command(self.mount_point, ["emerge", "sys-boot/grub:2"])
            chroot_command(self.mount_point, [
                "grub-install", "--target=x86_64-efi",
                "--efi-directory=/boot", "--bootloader-id=GRUB"
            ])
        else:
            chroot_command(self.mount_point, ["emerge", "sys-boot/grub:2"])
            chroot_command(self.mount_point, [
                "grub-install", self.config.disk_config.device
            ])
        
        # Generate GRUB config
        chroot_command(self.mount_point, ["grub-mkconfig", "-o", "/boot/grub/grub.cfg"])
        
        logger.info("GRUB installation completed")

    def install_systemd_boot(self):
        """Install systemd-boot"""
        logger.info("Installing systemd-boot")
        
        if not is_uefi():
            logger.error("systemd-boot requires UEFI")
            raise RuntimeError("systemd-boot requires UEFI")
        
        chroot_command(self.mount_point, ["bootctl", "install"])
        
        logger.info("systemd-boot installation completed")


# ============================================================================
# MAIN INSTALLER
# ============================================================================

class GentooInstaller:
    def __init__(self, config: InstallConfig, mount_point: str = "/mnt/gentoo"):
        self.config = config
        self.mount_point = mount_point

    def perform_installation(self):
        """Execute complete installation process"""
        logger.info("=" * 60)
        logger.info("Starting Gentoo Installation")
        logger.info("=" * 60)
        
        try:
            # Step 1: Disk preparation
            logger.info("Step 1: Preparing disks")
            disk_mgr = DiskManager(self.config.disk_config)
            disk_mgr.partition_disk()
            disk_mgr.setup_encryption()
            disk_mgr.format_partitions()
            disk_mgr.mount_partitions(self.mount_point)
            
            # Step 2: Stage3 installation
            logger.info("Step 2: Installing stage3")
            stage3 = Stage3Installer(self.config, self.mount_point)
            stage3.download_stage3()
            stage3.configure_make_conf()
            stage3.setup_repos()
            
            # Step 3: System configuration
            logger.info("Step 3: Configuring system")
            sys_config = SystemConfigurator(self.config, self.mount_point)
            sys_config.configure_locale()
            sys_config.configure_timezone()
            sys_config.configure_network()
            sys_config.configure_fstab()
            sys_config.create_users()
            
            # Step 4: Kernel installation
            logger.info("Step 4: Installing kernel")
            kernel = KernelInstaller(self.config, self.mount_point)
            kernel.install_kernel()
            
            # Step 5: Bootloader installation
            logger.info("Step 5: Installing bootloader")
            bootloader = BootloaderInstaller(self.config, self.mount_point)
            bootloader.install_bootloader()
            
            # Step 6: Additional packages
            if self.config.additional_packages:
                logger.info("Step 6: Installing additional packages")
                chroot_command(self.mount_point, [
                    "emerge", *self.config.additional_packages
                ])
            
            logger.info("=" * 60)
            logger.info("Gentoo Installation Completed Successfully!")
            logger.info("=" * 60)
            logger.info("You can now reboot into your new Gentoo system")
            
        except Exception as e:
            logger.error(f"Installation failed: {e}")
            logger.error("Check /var/log/gentooinstall/install.log for details")
            raise


# ============================================================================
# CLI INTERFACE
# ============================================================================

def load_config_from_file(config_file: str) -> InstallConfig:
    """Load installation configuration from JSON file"""
    with open(config_file, 'r') as f:
        data = json.load(f)
    
    # Parse configuration
    disk_config = DiskConfig(**data['disk_config'])
    system_config = SystemConfig(**data['system_config'])
    users = [UserConfig(**u) for u in data['users']]
    
    config = InstallConfig(
        disk_config=disk_config,
        system_config=system_config,
        root_password=data['root_password'],
        users=users,
        bootloader=BootloaderType(data.get('bootloader', 'grub')),
        init_system=InitSystem(data.get('init_system', 'openrc')),
        profile=ProfileType(data.get('profile', 'minimal')),
        additional_packages=data.get('additional_packages', []),
        kernel_config=data.get('kernel_config', 'genkernel'),
        make_opts=data.get('make_opts', '-j$(nproc)')
    )
    
    return config


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Gentoo Linux Installer")
    parser.add_argument("--config", help="Path to configuration JSON file")
    parser.add_argument("--guided", action="store_true", help="Run guided installation")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode")
    
    args = parser.parse_args()
    
    if args.config:
        logger.info(f"Loading configuration from {args.config}")
        config = load_config_from_file(args.config)
        
        if not args.dry_run:
            installer = GentooInstaller(config)
            installer.perform_installation()
        else:
            logger.info("Dry run mode - configuration loaded successfully")
            logger.info(json.dumps(asdict(config), indent=2, default=str))
    
    elif args.guided:
        logger.info("Guided installation not yet implemented")
        logger.info("Please use --config with a JSON configuration file")
        sys.exit(1)
    
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
