import os
import sys
import requests
import re
from modules import *

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
print("Latest stage3:", PROFILE)

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
    if os.geteuid() != 0:
        print("This script must be run as root.")
        sys.exit(1)

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
    os.system("mkdir -p /mnt/gentoo")
    print("Made parent directory: [/mnt/gentoo]")
    
    # Check if mount succeeds - explicitly specify ext4 filesystem type
    mount_result = os.system(f"mount -t ext4 {ROOTPT} /mnt/gentoo")
    if mount_result != 0:
        print(f"ERROR: Failed to mount {ROOTPT} to /mnt/gentoo")
        print("Make sure the partition is formatted with mkfs.ext4 first")
        sys.exit(1)
    
    # Verify mount was successful by checking if the mount point is actually mounted
    if not os.path.ismount("/mnt/gentoo"):
        print(f"ERROR: {ROOTPT} is not mounted at /mnt/gentoo")
        sys.exit(1)
    
    print(f"Mounted [{ROOTPT}] to [/mnt/gentoo]")
    print("Latest stage3 profile:", PROFILE)
    os.system(f"wget -P /mnt/gentoo {BASE_URL}/{PROFILE}")
    print(f"Finished links utility")
    os.system(f"cd /mnt/gentoo && tar xpvf stage3-*.tar.xz --xattrs-include='*.*' --numeric-owner")
    print("Checking the content of the tarball.... finished")
    # Fix: Use relative path after cd, or absolute path to mounted partition
    # Ensure portage directory exists before writing
    os.system("mkdir -p /mnt/gentoo/etc/portage")
    os.system(f"cd /mnt/gentoo && echo 'MAKEOPTS=\"-j{MAKEOPTS_J} -l{MAKEOPTS_L}\"' >> etc/portage/make.conf")
    print("MAKEOPTS set up.")
    os.system("cp --dereference /etc/resolv.conf /mnt/gentoo/etc/")
    print("Successfully copied [etc/resolv.conf] to [/mnt/gentoo/etc]")
    # Fix: Changed 'move' to 'mv'
    os.system("mv in_chroot.py /mnt/gentoo/ && mv modules.py /mnt/gentoo/ && arch-chroot /mnt/gentoo python in_chroot.py")
    # print("Chroot successful!")


    # # Move the file from current dir into /mnt/gentoo/root
    # os.system("mv in_chroot.py /mnt/gentoo/root/")
    # os.system("mv modules.py /mnt/gentoo/root/")
    # # os.system("mv config.jsonc /mnt/gentoo/root/")

    # # Run inside chroot
    # os.system("arch-chroot /mnt/gentoo python /root/in_chroot.py")

    print("Chroot successful!")

require_root()

# Check if partition is formatted, if not, format it
if not is_partition_formatted(ROOTPT):
    print(f"Partition {ROOTPT} is not formatted as ext4.")
    print("Formatting partitions...")
    partition()
else:
    print(f"Partition {ROOTPT} is already formatted as ext4.")

MOUNT()

