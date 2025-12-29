import os
from chroot_modules import *
ROOTPT = cfg_get("ROOTPT")
EFIPT = cfg_get("EFIPT")
SWAPPT = cfg_get("SWAPPT")
PROFILE = cfg_get("URL")
PROFILENR = cfg_get("PROFILE")  # 8 for default/linux/amd64/23.0/desktop/plasma/systemd
HOSTNAME = cfg_get("HOSTNAME")
USERNAME = cfg_get("USERNAME")
ZONEINFO = cfg_get("ZONEINFO")
LOCALE = detect_and_set_locale()
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
    os.system("mkdir -p boot/efi")
    os.system(f"mount /dev/{EFIPT} boot/efi")
    print("Syncing the system...")
    os.system("emerge-webrsync")
    os.system("emerge -q --oneshot app-portage/mirrorselect")
    print("Selecting mirrors...")
    os.system("mirrorselect -i -o >> /etc/portage/make.conf")
    print("Resyncing quietly...")
    os.system("emerge --sync --quiet")
    print("Selecting profile...")
    os.system(f"eselect profile set {PROFILENR}") # gives error: action unknown: 2
    print("Upgrading system...")
    os.system("emerge --verbose --update --deep --changed-use @world")
    print("Configuring zoneinfo...")
    os.system(f"ln -sf ../usr/share/zoneinfo/{ZONEINFO} /etc/localtime")
    print("Configuring locale...")
    os.system("""echo "en_US.UTF-8 UTF-8" > /etc/locale.gen""")
    os.system("locale-gen")
    print(f"Continuing with locale selected: {LOCALE}...")
    os.system(f"eselect locale set {LOCALE}")
    os.system("env-update")
    os.system("source /etc/profile")  
    os.system("""
    echo "sys-kernel/linux-firmware @BINARY-REDISTRIBUTABLE" >> /etc/portage/package.license
    """)
    os.system("""
    echo "sys-firmware/intel-microcode intel-ucode" >> /etc/portage/package.license
    """)
    os.system("emerge sys-kernel/linux-firmware")    
    os.system("emerge sys-firmware/sof-firmware")
    os.system("emerge sys-firmware/intel-microcode")
    os.system("""
    echo "sys-kernel/installkernel systemd dracut grub" >> /etc/portage/package.use/installkernel
    """)
    os.system("emerge sys-kernel/gentoo-kernel-bin")
    os.system("emerge dev-vcs/git sys-devel/make")
    os.system("git clone https://codeberg.org/coast/cfstabgen.git")
    os.system("cd cfstabgen && make && make install") 
    os.system("cfstabgen -U / > /etc/fstab")
    os.system(f"echo {HOSTNAME} > /etc/hostname")
    os.system("emerge net-misc/dhcpcd")
    os.system("systemctl enable dhcpcd")
    with open("/etc/hosts", "w") as f: 
        f.write(hosts)
    print("Replaced /etc/hosts with new hostname:", HOSTNAME)

    
    print("Setting root password...")
    apply_password("root", RPSW)
    print("Your root password has been set!")
    os.system(f"useradd -m -G users,wheel,audio,video -s /bin/bash {USERNAME}")
    print("Setting user password...")
    apply_password(USERNAME, UPSW)
    print("Your user password has been set!")

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
    def CONFIGURE_SUDOERS():
        os.system("emerge -q sudo")

        with open("/etc/sudoers", "w") as f:
            f.write(sudo_config)
    print("Replaced /etc/sudoers with custom configuration.")
    CONFIGURE_SUDOERS()
    os.system("emerge net-wireless/iw net-wireless/wpa_supplicant")
    os.system("""
    echo 'GRUB_PLATFORMS="efi-64"' >> /etc/portage/make.conf
    """)
    os.system("emerge --verbose sys-boot/grub")
    os.system(f"mount {EFIPT} /boot/efi")
    os.system("grub-install --efi-directory=/boot/efi")
    os.system("mkdir -p /boot/efi/grub")
    os.system("grub-mkconfig -o /boot/efi/grub/grub.cfg")
    os.system("mount -o remount,rw /")
    print("Installation finished. Exiting chroot...")
    print("Done! You may reboot now.")
    os.system("exit")

CRITICALS()