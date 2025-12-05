#!/usr/bin/env python3
"""
Interactive guided installer for Gentoo Linux
Provides a menu-driven interface similar to archinstall
"""

import os
import sys
import subprocess
from typing import Optional, List, Dict, Any
from pathlib import Path

# Import from main installer
from gentooinstall import (
    DiskConfig, SystemConfig, UserConfig, InstallConfig,
    DiskEncryption, FilesystemType, BootloaderType, ProfileType, InitSystem,
    GentooInstaller, logger
)


class Colors:
    """ANSI color codes for terminal output"""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


class GuidedInstaller:
    """Interactive guided installer"""
    
    def __init__(self):
        self.config: Optional[InstallConfig] = None
        self.disk_config: Optional[DiskConfig] = None
        self.system_config: Optional[SystemConfig] = None
        self.users: List[UserConfig] = []
        self.root_password: Optional[str] = None

    def clear_screen(self):
        """Clear the terminal screen"""
        os.system('clear')

    def print_header(self, text: str):
        """Print a styled header"""
        print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 60}{Colors.ENDC}")
        print(f"{Colors.HEADER}{Colors.BOLD}{text.center(60)}{Colors.ENDC}")
        print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 60}{Colors.ENDC}\n")

    def print_section(self, text: str):
        """Print a section header"""
        print(f"\n{Colors.OKBLUE}{Colors.BOLD}>>> {text}{Colors.ENDC}\n")

    def print_success(self, text: str):
        """Print success message"""
        print(f"{Colors.OKGREEN}✓ {text}{Colors.ENDC}")

    def print_warning(self, text: str):
        """Print warning message"""
        print(f"{Colors.WARNING}⚠ {text}{Colors.ENDC}")

    def print_error(self, text: str):
        """Print error message"""
        print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")

    def ask_question(self, question: str, default: Optional[str] = None) -> str:
        """Ask a question and return the answer"""
        if default:
            prompt = f"{question} [{default}]: "
        else:
            prompt = f"{question}: "
        
        answer = input(f"{Colors.OKCYAN}{prompt}{Colors.ENDC}").strip()
        return answer if answer else (default or "")

    def ask_yes_no(self, question: str, default: bool = True) -> bool:
        """Ask a yes/no question"""
        default_str = "Y/n" if default else "y/N"
        answer = self.ask_question(f"{question}", default_str)
        
        if not answer or answer.lower() in ['y', 'yes']:
            return True if default else False
        return answer.lower() in ['y', 'yes']

    def select_from_list(self, options: List[str], prompt: str, default: int = 0) -> int:
        """Display a list and let user select an option"""
        print(f"\n{Colors.OKCYAN}{prompt}{Colors.ENDC}\n")
        
        for i, option in enumerate(options, 1):
            marker = "→" if i - 1 == default else " "
            print(f"  {marker} {i}. {option}")
        
        while True:
            try:
                choice = input(f"\n{Colors.OKCYAN}Enter choice [1-{len(options)}]: {Colors.ENDC}").strip()
                if not choice:
                    return default
                
                choice_num = int(choice)
                if 1 <= choice_num <= len(options):
                    return choice_num - 1
                else:
                    self.print_error(f"Please enter a number between 1 and {len(options)}")
            except ValueError:
                self.print_error("Please enter a valid number")

    def detect_disks(self) -> List[str]:
        """Detect available disks"""
        result = subprocess.run(
            ["lsblk", "-d", "-n", "-o", "NAME,SIZE,TYPE"],
            capture_output=True,
            text=True
        )
        
        disks = []
        for line in result.stdout.strip().split('\n'):
            parts = line.split()
            if len(parts) >= 3 and parts[2] == "disk":
                disks.append(f"/dev/{parts[0]} ({parts[1]})")
        
        return disks

    def configure_disks(self):
        """Interactive disk configuration"""
        self.print_section("Disk Configuration")
        
        # Select disk
        disks = self.detect_disks()
        if not disks:
            self.print_error("No disks detected!")
            sys.exit(1)
        
        disk_idx = self.select_from_list(disks, "Select installation disk:")
        device = disks[disk_idx].split()[0]
        
        self.print_warning(f"Selected disk: {device}")
        self.print_warning("ALL DATA ON THIS DISK WILL BE DESTROYED!")
        
        if not self.ask_yes_no("Continue?", default=False):
            sys.exit(0)
        
        # Filesystem selection
        fs_options = [fs.value for fs in FilesystemType]
        fs_idx = self.select_from_list(
            fs_options,
            "Select root filesystem:",
            default=0
        )
        filesystem = FilesystemType(fs_options[fs_idx])
        
        # Swap partition
        use_swap = self.ask_yes_no("Create swap partition?", default=True)
        
        # Encryption
        use_encryption = self.ask_yes_no("Enable disk encryption (LUKS)?", default=False)
        encryption = DiskEncryption.LUKS if use_encryption else DiskEncryption.NONE
        encryption_password = None
        
        if use_encryption:
            while True:
                password1 = input(f"{Colors.OKCYAN}Enter encryption password: {Colors.ENDC}")
                password2 = input(f"{Colors.OKCYAN}Confirm encryption password: {Colors.ENDC}")
                
                if password1 == password2:
                    encryption_password = password1
                    break
                else:
                    self.print_error("Passwords do not match!")
        
        # Set partition names (these will be created during installation)
        boot_partition = f"{device}1"
        swap_partition = f"{device}2" if use_swap else None
        root_partition = f"{device}3" if use_swap else f"{device}2"
        
        self.disk_config = DiskConfig(
            device=device,
            boot_partition=boot_partition,
            root_partition=root_partition,
            swap_partition=swap_partition,
            filesystem=filesystem,
            encryption=encryption,
            encryption_password=encryption_password
        )
        
        self.print_success("Disk configuration completed")

    def configure_system(self):
        """Interactive system configuration"""
        self.print_section("System Configuration")
        
        # Hostname
        hostname = self.ask_question("Enter hostname", "gentoo")
        
        # Timezone
        print("\nCommon timezones:")
        print("  - America/New_York")
        print("  - America/Los_Angeles")
        print("  - Europe/London")
        print("  - Europe/Berlin")
        print("  - Asia/Tokyo")
        print("  - UTC")
        timezone = self.ask_question("Enter timezone", "UTC")
        
        # Locale
        locale = self.ask_question("Enter locale", "en_US.UTF-8")
        
        # Keymap
        keymap = self.ask_question("Enter keymap", "us")
        
        self.system_config = SystemConfig(
            hostname=hostname,
            timezone=timezone,
            locale=locale,
            keymap=keymap
        )
        
        self.print_success("System configuration completed")

    def configure_users(self):
        """Interactive user configuration"""
        self.print_section("User Configuration")
        
        # Root password
        while True:
            password1 = input(f"{Colors.OKCYAN}Enter root password: {Colors.ENDC}")
            password2 = input(f"{Colors.OKCYAN}Confirm root password: {Colors.ENDC}")
            
            if password1 == password2:
                self.root_password = password1
                break
            else:
                self.print_error("Passwords do not match!")
        
        self.print_success("Root password set")
        
        # User accounts
        self.users = []
        while self.ask_yes_no("\nCreate a user account?", default=True):
            username = self.ask_question("Username")
            
            while True:
                password1 = input(f"{Colors.OKCYAN}Enter user password: {Colors.ENDC}")
                password2 = input(f"{Colors.OKCYAN}Confirm user password: {Colors.ENDC}")
                
                if password1 == password2:
                    break
                else:
                    self.print_error("Passwords do not match!")
            
            shell = self.ask_question("Shell", "/bin/bash")
            
            user = UserConfig(
                username=username,
                password=password1,
                shell=shell
            )
            
            self.users.append(user)
            self.print_success(f"User '{username}' created")
            
            if len(self.users) >= 1:
                if not self.ask_yes_no("Create another user?", default=False):
                    break

    def configure_boot(self):
        """Interactive bootloader configuration"""
        self.print_section("Bootloader Configuration")
        
        # Bootloader selection
        bootloaders = [bl.value for bl in BootloaderType]
        bl_idx = self.select_from_list(
            bootloaders,
            "Select bootloader:",
            default=0
        )
        bootloader = BootloaderType(bootloaders[bl_idx])
        
        # Init system
        init_systems = [init.value for init in InitSystem]
        init_idx = self.select_from_list(
            init_systems,
            "Select init system:",
            default=0
        )
        init_system = InitSystem(init_systems[init_idx])
        
        self.bootloader = bootloader
        self.init_system = init_system
        
        self.print_success("Boot configuration completed")

    def configure_profile(self):
        """Interactive profile configuration"""
        self.print_section("Profile & Packages")
        
        # Profile selection
        profiles = [p.value for p in ProfileType]
        profile_idx = self.select_from_list(
            profiles,
            "Select installation profile:",
            default=0
        )
        self.profile = ProfileType(profiles[profile_idx])
        
        # Kernel configuration
        kernel_options = ["genkernel (automatic)", "manual"]
        kernel_idx = self.select_from_list(
            kernel_options,
            "Select kernel configuration method:",
            default=0
        )
        self.kernel_config = "genkernel" if kernel_idx == 0 else "manual"
        
        # Make options
        import multiprocessing
        cpu_count = multiprocessing.cpu_count()
        make_opts = self.ask_question(
            f"Enter MAKEOPTS (parallel jobs)",
            f"-j{cpu_count}"
        )
        self.make_opts = make_opts
        
        # Additional packages
        self.print_warning("\nEnter additional packages to install (space-separated)")
        self.print_warning("Example: app-editors/vim net-misc/dhcpcd sys-process/cronie")
        packages_str = self.ask_question("Additional packages", "")
        
        self.additional_packages = packages_str.split() if packages_str else []
        
        self.print_success("Profile configuration completed")

    def show_summary(self):
        """Display installation summary"""
        self.print_header("Installation Summary")
        
        print(f"{Colors.BOLD}Disk Configuration:{Colors.ENDC}")
        print(f"  Device: {self.disk_config.device}")
        print(f"  Filesystem: {self.disk_config.filesystem.value}")
        print(f"  Encryption: {self.disk_config.encryption.value}")
        
        print(f"\n{Colors.BOLD}System Configuration:{Colors.ENDC}")
        print(f"  Hostname: {self.system_config.hostname}")
        print(f"  Timezone: {self.system_config.timezone}")
        print(f"  Locale: {self.system_config.locale}")
        
        print(f"\n{Colors.BOLD}Users:{Colors.ENDC}")
        print(f"  Root: configured")
        for user in self.users:
            print(f"  {user.username}: {user.shell}")
        
        print(f"\n{Colors.BOLD}Boot Configuration:{Colors.ENDC}")
        print(f"  Bootloader: {self.bootloader.value}")
        print(f"  Init System: {self.init_system.value}")
        
        print(f"\n{Colors.BOLD}Installation Profile:{Colors.ENDC}")
        print(f"  Profile: {self.profile.value}")
        print(f"  Kernel: {self.kernel_config}")
        print(f"  Make Options: {self.make_opts}")
        
        if self.additional_packages:
            print(f"\n{Colors.BOLD}Additional Packages:{Colors.ENDC}")
            for pkg in self.additional_packages:
                print(f"  - {pkg}")
        
        print()

    def build_config(self) -> InstallConfig:
        """Build the final installation configuration"""
        return InstallConfig(
            disk_config=self.disk_config,
            system_config=self.system_config,
            root_password=self.root_password,
            users=self.users,
            bootloader=self.bootloader,
            init_system=self.init_system,
            profile=self.profile,
            additional_packages=self.additional_packages,
            kernel_config=self.kernel_config,
            make_opts=self.make_opts
        )

    def run(self):
        """Run the guided installer"""
        self.clear_screen()
        self.print_header("Gentoo Linux Guided Installer")
        
        print(f"{Colors.WARNING}This installer will guide you through the Gentoo installation process.{Colors.ENDC}")
        print(f"{Colors.WARNING}Make sure you have booted from a Gentoo Live ISO.{Colors.ENDC}\n")
        
        if not self.ask_yes_no("Continue with installation?", default=True):
            print("Installation cancelled.")
            sys.exit(0)
        
        # Run configuration steps
        self.configure_disks()
        self.configure_system()
        self.configure_users()
        self.configure_boot()
        self.configure_profile()
        
        # Show summary and confirm
        self.clear_screen()
        self.show_summary()
        
        self.print_warning("\nTHIS WILL DESTROY ALL DATA ON THE SELECTED DISK!")
        if not self.ask_yes_no("Proceed with installation?", default=False):
            print("Installation cancelled.")
            sys.exit(0)
        
        # Build configuration
        config = self.build_config()
        
        # Save configuration
        import json
        from dataclasses import asdict
        
        config_file = "/tmp/gentooinstall_config.json"
        with open(config_file, 'w') as f:
            json.dump(asdict(config), f, indent=2, default=str)
        
        self.print_success(f"Configuration saved to {config_file}")
        
        # Start installation
        self.print_section("Starting Installation")
        
        try:
            installer = GentooInstaller(config)
            installer.perform_installation()
            
            self.clear_screen()
            self.print_header("Installation Complete!")
            print(f"\n{Colors.OKGREEN}{Colors.BOLD}Gentoo Linux has been successfully installed!{Colors.ENDC}\n")
            print("Next steps:")
            print("  1. Remove the installation media")
            print("  2. Reboot: reboot")
            print("  3. Log in with your configured credentials")
            print("\nFor more information, visit: https://wiki.gentoo.org/\n")
            
        except Exception as e:
            self.print_error(f"Installation failed: {e}")
            print(f"\nCheck the log file: /var/log/gentooinstall/install.log")
            sys.exit(1)


def main():
    """Main entry point for guided installer"""
    if os.geteuid() != 0:
        print(f"{Colors.FAIL}This installer must be run as root!{Colors.ENDC}")
        sys.exit(1)
    
    installer = GuidedInstaller()
    installer.run()


if __name__ == "__main__":
    main()
