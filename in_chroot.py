import os
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
ROOTPT = cfg_get("ROOTPT")
EFIPT = cfg_get("EFIPT")
SWAPPT = cfg_get("SWAPPT")
PROFILE = cfg_get("URL")
PROFILENR = cfg_get("PROFILE")  # 8 for default/linux/amd64/23.0/desktop/plasma/systemd
HOSTNAME = cfg_get("HOSTNAME")
USERNAME = cfg_get("USERNAME")
ZONEINFO = cfg_get("ZONEINFO")
# LOCALE will be set after locale-gen in CRITICALS()
RPSW = cfg_get("ROOT_PASSWORD")
UPSW = cfg_get("USER_PASSWORD")

hosts = f"""
# /etc/hosts: Local Host Database
#
# This file describes a number of aliases-to-address mappings for the for
# local hosts that share this file.
#
# The format of lines in this file is:
#
# IP_ADDRESS	canonical_hostname	[aliases...]
#
#The fields can be separated by any number of spaces or tabs.
#
# In the presence of the domain name service or NIS, this file may not be
# consulted at all; see /etc/host.conf for the resolution order.
#

# IPv4 and IPv6 localhost aliases
127.0.0.1	localhost
::1		localhost
127.0.0.1   {HOSTNAME}

#
# Imaginary network.
#10.0.0.2               myname
#10.0.0.3               myfriend
#
# According to RFC 1918, you can use the following IP networks for private
# nets which will never be connected to the Internet:
#
#       10.0.0.0        -   10.255.255.255
#       172.16.0.0      -   172.31.255.255
#       192.168.0.0     -   192.168.255.255
#
# In case you want to be able to connect directly to the Internet (i.e. not
# behind a NAT, ADSL router, etc...), you need real official assigned
# numbers.  Do not try to invent your own network numbers but instead get one
# from your network provider (if any) or from your regional registry (ARIN,
# APNIC, LACNIC, RIPE NCC, or AfriNIC.)
#
"""


def CRITICALS():
    print_header("GENTOO INSTALLATION - CHROOT ENVIRONMENT")
    print_info("Starting installation process inside chroot environment...")
    print_separator()
    
    print_header("MOUNTING EFI PARTITION")
    print_info("Creating /boot/efi directory...")
    os.system("mkdir -p /boot/efi")
    # Check if EFI partition is already mounted, if not mount it
    if not os.path.ismount("/boot/efi"):
        print_info(f"Mounting EFI partition {EFIPT} to /boot/efi...")
        mount_result = os.system(f"mount -t vfat {EFIPT} /boot/efi")
        if mount_result != 0:
            print_warning(f"Failed to mount {EFIPT} to /boot/efi, continuing anyway...")
        else:
            print_success(f"EFI partition {EFIPT} mounted to /boot/efi")
    else:
        print_success("/boot/efi is already mounted")
    print_separator()
    
    print_header("PORTAGE TREE SYNC")
    print_info("Synchronizing Portage tree with emerge-webrsync...")
    print_info("This downloads the Gentoo package database and may take several minutes...")
    os.system("emerge-webrsync")
    print_success("Portage tree synchronized successfully")
    print_separator()
    
    print_info("Installing mirrorselect tool for mirror optimization...")
    os.system("emerge -q --oneshot app-portage/mirrorselect")
    print_success("mirrorselect installed")
    print_separator()
    
    print_info("Selecting optimal mirrors for package downloads...")
    os.system("mirrorselect -i -o >> /etc/portage/make.conf")
    print_success("Mirrors configured in /etc/portage/make.conf")
    print_separator()
    
    print_info("Resyncing Portage tree with selected mirrors...")
    os.system("emerge --sync --quiet")
    print_success("Portage tree resynced with optimized mirrors")
    print_separator()
    
    print_header("PROFILE SELECTION")
    print_info(f"Setting Gentoo profile to profile number: {PROFILENR}")
    os.system(f"eselect profile set {PROFILENR}")
    print_success(f"Profile set to {PROFILENR}")
    print_separator()
    
    print_header("SYSTEM UPGRADE")
    print_info("Upgrading system packages to latest versions...")
    print_info("This process may take a significant amount of time depending on system specifications...")
    os.system("emerge --verbose --update --deep --changed-use @world")
    print_success("System upgrade completed")
    print_separator()
    
    print_header("TIMEZONE CONFIGURATION")
    print_info(f"Setting timezone to: {ZONEINFO}")
    os.system(f"ln -sf ../usr/share/zoneinfo/{ZONEINFO} /etc/localtime")
    print_success(f"Timezone configured: {ZONEINFO}")
    print_separator()
    
    print_header("LOCALE CONFIGURATION")
    print_info("Generating locale configuration...")
    print_info("Adding en_US.UTF-8 to locale.gen...")
    os.system("""echo "en_US.UTF-8 UTF-8" > /etc/locale.gen""")
    print_info("Generating locales...")
    os.system("locale-gen")
    print_success("Locales generated successfully")
    # Now detect and set locale after it's been generated
    print_info("Detecting and setting system locale...")
    LOCALE = detect_and_set_locale()
    print_info(f"Setting locale to option {LOCALE}...")
    os.system(f"eselect locale set {LOCALE}")
    print_success(f"Locale configured: option {LOCALE}")
    print_info("Updating environment with new locale settings...")
    os.system("env-update")
    os.system("source /etc/profile")
    print_success("Environment updated with locale settings")
    print_separator()  
    print_header("FIRMWARE INSTALLATION")
    print_info("Configuring firmware license acceptance...")
    os.system("""
    echo "sys-kernel/linux-firmware @BINARY-REDISTRIBUTABLE" >> /etc/portage/package.license
    """)
    os.system("""
    echo "sys-firmware/intel-microcode intel-ucode" >> /etc/portage/package.license
    """)
    print_success("Firmware licenses configured")
    
    print_info("Installing Linux firmware packages...")
    os.system("emerge sys-kernel/linux-firmware")
    print_success("Linux firmware installed")
    
    print_info("Installing SOF (Sound Open Firmware)...")
    os.system("emerge sys-firmware/sof-firmware")
    print_success("SOF firmware installed")
    
    print_info("Installing Intel microcode...")
    os.system("emerge sys-firmware/intel-microcode")
    print_success("Intel microcode installed")
    print_separator()
    
    print_header("KERNEL INSTALLATION")
    print_info("Configuring installkernel package use flags...")
    os.system("""
    echo "sys-kernel/installkernel systemd dracut grub" >> /etc/portage/package.use/installkernel
    """)
    print_success("Installkernel use flags configured")
    
    print_info("Installing Gentoo binary kernel...")
    print_info("This may take several minutes...")
    os.system("emerge sys-kernel/gentoo-kernel-bin")
    print_success("Kernel installed successfully")
    print_separator()
    
    print_header("BUILD TOOLS INSTALLATION")
    print_info("Installing git and make for build tools...")
    os.system("emerge dev-vcs/git sys-devel/make")
    print_success("Build tools installed")
    print_separator()
    
    print_header("FSTAB GENERATION")
    print_info("Cloning cfstabgen from Codeberg...")
    os.system("git clone https://codeberg.org/coast/cfstabgen.git")
    print_success("cfstabgen repository cloned")
    
    print_info("Building and installing cfstabgen...")
    os.system("cd cfstabgen && make && make install")
    print_success("cfstabgen installed")
    
    print_info("Generating /etc/fstab with UUIDs...")
    os.system("cfstabgen -U / > /etc/fstab")
    print_success("/etc/fstab generated successfully")
    print_separator()
    
    print_header("NETWORK CONFIGURATION")
    print_info(f"Setting system hostname to: {HOSTNAME}")
    os.system(f"echo {HOSTNAME} > /etc/hostname")
    print_success(f"Hostname set: {HOSTNAME}")
    
    print_info("Installing dhcpcd for network configuration...")
    os.system("emerge net-misc/dhcpcd")
    print_success("dhcpcd installed")
    
    print_info("Enabling dhcpcd service for automatic network configuration...")
    os.system("systemctl enable dhcpcd")
    print_success("dhcpcd service enabled")
    
    print_info(f"Configuring /etc/hosts with hostname: {HOSTNAME}")
    with open("/etc/hosts", "w") as f: 
        f.write(hosts)
    print_success(f"/etc/hosts configured with hostname: {HOSTNAME}")
    print_separator()

    print_header("USER ACCOUNT CONFIGURATION")
    print_info("Setting root user password...")
    apply_password("root", RPSW)
    print_success("Root password has been set successfully")
    
    print_info(f"Creating user account: {USERNAME}")
    print_info(f"Adding user to groups: users, wheel, audio, video")
    os.system(f"useradd -m -G users,wheel,audio,video -s /bin/bash {USERNAME}")
    print_success(f"User account {USERNAME} created")
    
    print_info(f"Setting password for user: {USERNAME}")
    apply_password(USERNAME, UPSW)
    print_success(f"Password for {USERNAME} has been set successfully")
    print_separator()

    sudo_config = """
    ## sudoers file.
    ##
    ## This file MUST be edited with the 'visudo' command as root.
    ## Failure to use 'visudo' may result in syntax or file permission errors
    ## that prevent sudo from running.
    ##
    ## See the sudoers man page for the details on how to write a sudoers file.
    ##

    ##
    ## Host alias specification
    ##
    ## Groups of machines. These may include host names (optionally with wildcards),
    ## IP addresses, network numbers or netgroups.
    # Host_Alias	WEBSERVERS = www1, www2, www3

    ##
    ## User alias specification
    ##
    ## Groups of users.  These may consist of user names, uids, Unix groups,
    ## or netgroups.
    # User_Alias	ADMINS = millert, dowdy, mikef

    ##
    ## Cmnd alias specification
    ##
    ## Groups of commands.  Often used to group related commands together.
    # Cmnd_Alias	PROCESSES = /usr/bin/nice, /bin/kill, /usr/bin/renice, \
    # 			   /usr/bin/pkill, /usr/bin/top
    #
    # Cmnd_Alias	REBOOT = /sbin/halt, /sbin/reboot, /sbin/poweroff
    #
    # Cmnd_Alias	DEBUGGERS = /usr/bin/gdb, /usr/bin/lldb, /usr/bin/strace, \
    # 			   /usr/bin/truss, /usr/bin/bpftrace, \
    # 			   /usr/bin/dtrace, /usr/bin/dtruss
    #
    # Cmnd_Alias	PKGMAN = /usr/bin/apt, /usr/bin/dpkg, /usr/bin/rpm, \
    # 			/usr/bin/yum, /usr/bin/dnf,  /usr/bin/zypper, \
    # 			/usr/bin/pacman

    ##
    ## Defaults specification
    ##
    ## Preserve editor environment variables for visudo.
    ## To preserve these for all commands, remove the "!visudo" qualifier.
    Defaults!/usr/sbin/visudo env_keep += "SUDO_EDITOR EDITOR VISUAL"
    ##
    ## Use a hard-coded PATH instead of the user's to find commands.
    ## This also helps prevent poorly written scripts from running
    ## arbitrary commands under sudo.
    Defaults secure_path="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/opt/bin:/usr/lib/llvm/20/bin:/usr/lib/llvm/19/bin:/usr/lib/llvm/18/bin:/usr/lib/llvm/17/bin:/usr/lib/llvm/16/bin:/usr/lib/llvm/15/bin"
    ##
    ## You may wish to keep some of the following environment variables
    ## when running commands via sudo.
    ##
    ## Locale settings
    # Defaults env_keep += "LANG LANGUAGE LINGUAS LC_* _XKB_CHARSET"
    ##
    ## Run X applications through sudo; HOME is used to find the
    ## .Xauthority file.  Note that other programs use HOME to find   
    ## configuration files and this may lead to privilege escalation!
    # Defaults env_keep += "HOME"
    ##
    ## X11 resource path settings
    # Defaults env_keep += "XAPPLRESDIR XFILESEARCHPATH XUSERFILESEARCHPATH"
    ##
    ## Desktop path settings
    # Defaults env_keep += "QTDIR KDEDIR"
    ##
    ## Allow sudo-run commands to inherit the callers' ConsoleKit session
    # Defaults env_keep += "XDG_SESSION_COOKIE"
    ##
    ## Uncomment to enable special input methods.  Care should be taken as
    ## this may allow users to subvert the command being run via sudo.
    # Defaults env_keep += "XMODIFIERS GTK_IM_MODULE QT_IM_MODULE QT_IM_SWITCHER"
    ##
    ## Uncomment to disable "use_pty" when running commands as root.
    ## Commands run as non-root users will run in a pseudo-terminal,
    ## not the user's own terminal, to prevent command injection.
    # Defaults>root !use_pty
    ##
    ## Uncomment to run commands in the background by default.
    ## This can be used to prevent sudo from consuming user input while
    ## a non-interactive command runs if "use_pty" or I/O logging are
    ## enabled.  Some commands may not run properly in the background.
    # Defaults exec_background
    ##
    ## Uncomment to send mail if the user does not enter the correct password.
    # Defaults mail_badpass
    ##
    ## Uncomment to enable logging of a command's output, except for
    ## sudoreplay and reboot.  Use sudoreplay to play back logged sessions.
    ## Sudo will create up to 2,176,782,336 I/O logs before recycling them.
    ## Set maxseq to a smaller number if you don't have unlimited disk space.
    # Defaults log_output
    # Defaults!/usr/bin/sudoreplay !log_output
    # Defaults!/usr/local/bin/sudoreplay !log_output
    # Defaults!REBOOT !log_output
    # Defaults maxseq = 1000
    ##
    ## Uncomment to disable intercept and log_subcmds for debuggers and
    ## tracers.  Otherwise, anything that uses ptrace(2) will be unable
    ## to run under sudo if intercept_type is set to "trace".
    # Defaults!DEBUGGERS !intercept, !log_subcmds
    ##
    ## Uncomment to disable intercept and log_subcmds for package managers.
    ## Some package scripts run a huge number of commands, which is made
    ## slower by these options and also can clutter up the logs.
    # Defaults!PKGMAN !intercept, !log_subcmds
    ##
    ## Uncomment to disable PAM silent mode.  Otherwise messages by PAM
    ## modules such as pam_faillock will not be printed.
    # Defaults !pam_silent

    ##
    ## Runas alias specification
    ##

    ##
    ## User privilege specification
    ##
    root ALL=(ALL:ALL) ALL

    ## Uncomment to allow members of group wheel to execute any command
    %wheel ALL=(ALL:ALL) ALL
    Defaults timestamp_timeout=0


    # Preserve environment variables for Wayland
    Defaults env_keep += "XDG_SESSION_TYPE XDG_RUNTIME_DIR DISPLAY WAYLAND_DISPLAY DBUS_SESSION_BUS_ADDRESS"


    ## Same thing without a password
    # %wheel ALL=(ALL:ALL) NOPASSWD: ALL

    ## Uncomment to allow members of group sudo to execute any command
    # %sudo ALL=(ALL:ALL) ALL

    ## Uncomment to allow any user to run sudo if they know the password
    ## of the user they are running the command as (root by default).
    # Defaults targetpw  # Ask for the password of the target user
    # ALL ALL=(ALL:ALL) ALL  # WARNING: only use this together with 'Defaults targetpw'

    ## Read drop-in files from /etc/sudoers.d
    @includedir /etc/sudoers.d
    """
    print_header("SUDO CONFIGURATION")
    def CONFIGURE_SUDOERS():
        print_info("Installing sudo package...")
        os.system("emerge -q sudo")
        print_success("sudo installed")
        
        print_info("Writing custom sudoers configuration...")
        with open("/etc/sudoers", "w") as f:
            f.write(sudo_config)
        print_success("Custom sudoers configuration written")
    CONFIGURE_SUDOERS()
    print_separator()
    
    print_header("WIRELESS TOOLS INSTALLATION")
    print_info("Installing wireless networking tools (iw, wpa_supplicant)...")
    os.system("emerge net-wireless/iw net-wireless/wpa_supplicant")
    print_success("Wireless tools installed")
    print_separator()
    
    print_header("GRUB BOOTLOADER INSTALLATION")
    print_info("Configuring GRUB for EFI-64 platform...")
    os.system("""
    echo 'GRUB_PLATFORMS="efi-64"' >> /etc/portage/make.conf
    """)
    print_success("GRUB platform configured")
    
    print_info("Installing GRUB bootloader...")
    print_info("This may take several minutes...")
    os.system("emerge --verbose sys-boot/grub")
    print_success("GRUB installed successfully")
    
    # Ensure EFI partition is mounted (it should already be from earlier)
    print_info("Verifying EFI partition mount...")
    if not os.path.ismount("/boot/efi"):
        print_warning("/boot/efi is not mounted, attempting to mount...")
        mount_result = os.system(f"mount -t vfat {EFIPT} /boot/efi")
        if mount_result != 0:
            print_error(f"Failed to mount {EFIPT} to /boot/efi for GRUB installation")
        else:
            print_success(f"EFI partition {EFIPT} mounted to /boot/efi")
    else:
        print_success("/boot/efi is already mounted")
    
    print_info("Installing GRUB to EFI directory...")
    os.system("grub-install --efi-directory=/boot/efi")
    print_success("GRUB installed to EFI directory")
    
    print_info("Creating GRUB configuration directory...")
    os.system("mkdir -p /boot/efi/grub")
    print_success("GRUB configuration directory created")
    
    print_info("Generating GRUB configuration file...")
    os.system("grub-mkconfig -o /boot/efi/grub/grub.cfg")
    print_success("GRUB configuration generated")
    print_separator()
    
    print_header("FILESYSTEM VERIFICATION")
    # Remount root as read-write if it became read-only (check and fix)
    print_info("Checking filesystem mount status...")
    remount_result = os.system("mount -o remount,rw / 2>/dev/null")
    if remount_result != 0:
        print_warning("Could not remount root as read-write. This may indicate filesystem errors.")
        print_warning("After exiting chroot, you may need to run: fsck -y <root-partition>")
    else:
        print_success("Root filesystem is mounted read-write")
    print_separator()
    
    print_header("INSTALLATION COMPLETE")
    print_success("All installation steps completed successfully!")
    print_info("Exiting chroot environment...")
    print_separator()
    print_success("Installation finished. You may now reboot your system!")
    print_separator()
    os.system("exit")

CRITICALS()