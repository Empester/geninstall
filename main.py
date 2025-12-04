import os

ROOTPT = "/dev/"
EFIPT = "/dev/"
SWAPPT = "/dev/"
PROFILE="https://distfiles.gentoo.org/releases/amd64/autobuilds/current-stage3-amd64-systemd-desktop/"
MAKEOPTS_J = 2 # ex: -j3
MAKEOPTS_L = 3 # ex: -l4

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
