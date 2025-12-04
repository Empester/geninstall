import os
import requests
import re

ROOTPT = "/dev/"
EFIPT = "/dev/"
SWAPPT = "/dev/"
URL = "https://gentoo.osuosl.org/releases/amd64/autobuilds/current-stage3-amd64-desktop-systemd/latest-stage3-amd64-desktop-systemd.txt"
MAKEOPTS_J = 2 # ex: -j3
MAKEOPTS_L = 3 # ex: -l4

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


# os.system('pwd')
def mkfs():
    os.system(f"mkfs.ext4 {ROOTPT}")
    os.system(f"mkfs.fat -F32 {EFIPT}")
    os.system(f"mkswap {SWAPPT}")
    os.system(f"swapon {SWAPPT}")

def partition():
    answer = input(f"""
    \t Your root partition is {ROOTPT}
    \t Your EFI partition is {EFIPT}
    \t Your SWAP partition is {SWAPPT}
    If correct, insert Y or N

    """)
    if answer.upper() == "Y":
        mkfs()

partition()

def MOUNT():
    os.system("mkdir -p /mnt/gentoo")
    os.system(f"mount {ROOTPT} /mnt/gentoo")
    print("Latest stage3 profile:", PROFILE)
    os.system(f"cd /mnt/gentoo && wget {PROFILE}")
    os.system(f"cd /mnt/gentoo && tar xpvf stage3-*.tar.xz --xattrs-include='*.*' --numeric-owner")
    os.system(f"""cd /mnt/gentoo/ && echo ''MAKEOPTS="-j{MAKEOPTS_J} -l{MAKEOPTS_L}"' >> /etc/portage/make.conf""")
    os.system("cd /mnt/gentoo && cp --dereference /etc/resolv.conf /mnt/gentoo/etc/")
    os.system("cd /mnt/gentoo && arch-chroot /mnt/gentoo /usr/bin/python3 /root/in-chroot.py")




def require_root():
    if os.geteuid() != 0:
        print("This script must be run as root.")
        sys.exit(1)
require_root()
