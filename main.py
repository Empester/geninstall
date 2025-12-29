import os
import sys
import requests
import re
from modules import *

# Color codes for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_success(msg):
    print(f"{Colors.GREEN}✓ {msg}{Colors.RESET}")

def print_error(msg):
    print(f"{Colors.RED}✗ ERROR: {msg}{Colors.RESET}")

def print_warning(msg):
    print(f"{Colors.YELLOW}⚠ WARNING: {msg}{Colors.RESET}")

def print_info(msg):
    print(f"{Colors.CYAN}ℹ {msg}{Colors.RESET}")

def print_header(msg):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{msg}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.RESET}\n")

def print_separator():
    print(f"{Colors.CYAN}{'-'*70}{Colors.RESET}")

ensure_config()

ROOTPT = cfg_get("ROOTPT")
EFIPT = cfg_get("EFIPT")
SWAPPT = cfg_get("SWAPPT")
URL = "https://gentoo.osuosl.org/releases/amd64/autobuilds/current-stage3-amd64-systemd/latest-stage3-amd64-systemd.txt"
MAKEOPTS_J = cfg_get("MAKEOPTS_J")
MAKEOPTS_L = cfg_get("MAKEOPTS_L")
# INIT = cfg_get("INIT").lower()

resp = requests.get(URL)
resp.raise_for_status()

lines = [line.strip() for line in resp.text.splitlines() if line.strip()]

# Filter only lines that start with 'stage3-amd64'
stage3_lines = [line for line in lines if line.startswith("stage3-amd64")]

if not stage3_lines:
    raise ValueError("No stage3 filename found in the text file.")

# Take the first word of the last stage3 line
filename = stage3_lines[-1].split()[0]

# Store in PROFILE
PROFILE = filename

import requests
import re
import os

# Get latest stage3
URL = "https://gentoo.osuosl.org/releases/amd64/autobuilds/current-stage3-amd64-desktop-systemd/latest-stage3-amd64-desktop-systemd.txt"
resp = requests.get(URL)
resp.raise_for_status()
lines = [line.strip() for line in resp.text.splitlines() if line.strip()]
stage3_lines = [line for line in lines if line.startswith("stage3-amd64")]
PROFILE = stage3_lines[-1].split()[0]
print_header("GENTOO INSTALLATION SCRIPT")
print_info(f"Detected latest stage3 tarball: {PROFILE}")
print_separator()

# Download
BASE_URL = "https://gentoo.osuosl.org/releases/amd64/autobuilds/current-stage3-amd64-desktop-systemd/"


# def partition():
#     skip = cfg_get("SKIP", "").lower()
#     if skip in ("y", "yes"):
#         mkfs()
#     else:
#         answer = input(f"""
# Your root partition is {ROOTPT}
# Your EFI partition is {EFIPT}
# Your SWAP partition is {SWAPPT}
# If correct, insert Y or N: """).strip().upper()
#         if answer == "Y":
#             mkfs()
#         else:
#             print("Aborting partitioning. Please check your config.")

# partition()
def mkfs():
    os.system(f"mkfs.ext4 {ROOTPT}")
    os.system(f"mkfs.fat -F32 {EFIPT}")
    os.system(f"mkswap {SWAPPT}")
    os.system(f"swapon {SWAPPT}")

def partition():
    skip = cfg_get("SKIP", "").lower()
    if skip in ("y", "yes"):
        mkfs()
    else:
        answer = input(f"""
Your root partition is {ROOTPT}
Your EFI partition is {EFIPT}
Your SWAP partition is {SWAPPT}
If correct, insert Y or N: """).strip().upper()
        if answer == "Y":
            mkfs()
        else:
            print("Aborting partitioning. Please check your config.")


def require_root():
    print_info("Checking for root privileges...")
    if os.geteuid() != 0:
        print_error("This script must be run as root. Please run with sudo or as root user.")
        sys.exit(1)
    print_success("Root privileges confirmed")
    print_separator()

def is_partition_formatted(device):
    """Check if a partition is formatted as ext4"""
    # Use blkid to check filesystem type
    result = os.system(f"blkid -s TYPE -o value {device} > /dev/null 2>&1")
    if result == 0:
        # Get the filesystem type
        fs_type = os.popen(f"blkid -s TYPE -o value {device}").read().strip()
        return fs_type == "ext4"
    return False

def MOUNT():
    print_header("MOUNTING ROOT PARTITION")
    print_info("Creating mount point directory: /mnt/gentoo")
    os.system("mkdir -p /mnt/gentoo")
    print_success("Mount point directory created: /mnt/gentoo")
    
    print_info(f"Mounting {ROOTPT} to /mnt/gentoo as ext4 filesystem (read-write)...")
    # Check if mount succeeds - explicitly specify ext4 filesystem type with read-write
    mount_result = os.system(f"mount -t ext4 -o rw {ROOTPT} /mnt/gentoo")
    if mount_result != 0:
        print_error(f"Failed to mount {ROOTPT} to /mnt/gentoo")
        print_error("Make sure the partition is formatted with mkfs.ext4 first")
        sys.exit(1)
    
    # Verify it's mounted read-write
    print_info("Verifying mount status and read-write permissions...")
    mount_info = os.popen(f"mount | grep {ROOTPT}").read()
    if "ro," in mount_info or ",ro" in mount_info:
        print_warning(f"{ROOTPT} is mounted read-only, attempting to remount as read-write...")
        remount_result = os.system(f"mount -o remount,rw {ROOTPT} /mnt/gentoo")
        if remount_result != 0:
            print_error(f"Failed to remount {ROOTPT} as read-write")
            print_error("The filesystem may have errors. Run: fsck -y {ROOTPT}")
            sys.exit(1)
        print_success("Successfully remounted as read-write")
    
    # Verify mount was successful by checking if the mount point is actually mounted
    if not os.path.ismount("/mnt/gentoo"):
        print_error(f"{ROOTPT} is not mounted at /mnt/gentoo")
        sys.exit(1)
    
    print_success(f"Successfully mounted {ROOTPT} to /mnt/gentoo")
    print_separator()
    
    print_header("STAGE3 DOWNLOAD AND EXTRACTION")
    print_info(f"Target stage3 tarball: {PROFILE}")
    
    # Check available disk space before downloading
    import shutil
    print_info("Checking available disk space...")
    stat = shutil.disk_usage("/mnt/gentoo")
    free_gb = stat.free / (1024**3)
    total_gb = stat.total / (1024**3)
    used_gb = stat.used / (1024**3)
    print_info(f"Total space: {total_gb:.2f} GB | Used: {used_gb:.2f} GB | Free: {free_gb:.2f} GB")
    if free_gb < 5:
        print_warning("Less than 5GB free space available! This may cause issues during installation.")
    else:
        print_success(f"Sufficient disk space available ({free_gb:.2f} GB)")
    print_separator()
    
    print_info(f"Downloading stage3 tarball from: {BASE_URL}{PROFILE}")
    print_info("This may take several minutes depending on your internet connection...")
    os.system(f"wget -P /mnt/gentoo {BASE_URL}/{PROFILE}")
    print_success("Stage3 tarball downloaded successfully")
    print_separator()
    
    # Extract with error checking
    print_info("Extracting stage3 tarball...")
    print_info("This process extracts the Gentoo base system and may take a few minutes...")
    tar_result = os.system(f"cd /mnt/gentoo && tar xpvf stage3-*.tar.xz --xattrs-include='*.*' --numeric-owner 2>&1")
    if tar_result != 0:
        print_error("Failed to extract stage3 tarball. This may indicate disk space issues.")
        print_error("Check available space and filesystem errors.")
        sys.exit(1)
    print_success("Stage3 tarball extracted successfully")
    print_separator()
    
    print_header("CONFIGURING PORTAGE")
    print_info("Creating /etc/portage directory structure...")
    os.system("mkdir -p /mnt/gentoo/etc/portage")
    print_success("Portage directory structure created")
    
    print_info(f"Configuring MAKEOPTS: -j{MAKEOPTS_J} -l{MAKEOPTS_L}")
    os.system(f"cd /mnt/gentoo && echo 'MAKEOPTS=\"-j{MAKEOPTS_J} -l{MAKEOPTS_L}\"' >> etc/portage/make.conf")
    print_success("MAKEOPTS configured in /etc/portage/make.conf")
    print_separator()
    
    print_header("PREPARING CHROOT ENVIRONMENT")
    print_info("Copying resolv.conf for network configuration in chroot...")
    os.system("cp --dereference /etc/resolv.conf /mnt/gentoo/etc/")
    print_success("Successfully copied /etc/resolv.conf to /mnt/gentoo/etc/")
    
    print_info("Copying installation scripts to chroot environment...")
    os.system("cp in_chroot.py /mnt/gentoo/ && cp modules.py /mnt/gentoo/ && cp config.jsonc /mnt/gentoo/")
    print_success("Copied in_chroot.py, modules.py, and config.jsonc to /mnt/gentoo/")
    print_separator()
    
    print_header("ENTERING CHROOT ENVIRONMENT")
    print_info("Starting chroot environment and running installation script...")
    print_info("All subsequent operations will run inside the chrooted Gentoo system")
    print_separator()
    os.system("arch-chroot /mnt/gentoo python in_chroot.py")
    
    print_separator()
    print_success("Chroot session completed successfully!")
    print_separator()

require_root()

# Check if partition is formatted, if not, format it
print_header("PARTITION FORMATTING CHECK")
print_info(f"Checking filesystem type on {ROOTPT}...")
if not is_partition_formatted(ROOTPT):
    print_warning(f"Partition {ROOTPT} is not formatted as ext4")
    print_info("Initiating partition formatting process...")
    partition()
    print_success("Partitions formatted successfully")
else:
    print_success(f"Partition {ROOTPT} is already formatted as ext4")
print_separator()

MOUNT()

