#!/usr/bin/env python3
"""
Gentoo MAKEOPTS Detector and Configurator
Detects system specifications and recommends optimal MAKEOPTS values
"""

import os
import subprocess
import sys
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

def get_cpu_threads():
    """Get the number of CPU threads using nproc."""
    try:
        result = subprocess.run(['nproc'], capture_output=True, text=True, check=True)
        threads = int(result.stdout.strip())
        return threads
    except (subprocess.CalledProcessError, ValueError, FileNotFoundError):
        # Fallback: try to read from /proc/cpuinfo
        try:
            with open('/proc/cpuinfo', 'r') as f:
                threads = len([line for line in f if line.startswith('processor')])
            return threads if threads > 0 else 1
        except:
            return 1

def get_ram_gb():
    """Get total RAM in GB."""
    try:
        # Try reading from /proc/meminfo
        with open('/proc/meminfo', 'r') as f:
            for line in f:
                if line.startswith('MemTotal:'):
                    mem_kb = int(line.split()[1])
                    mem_gb = mem_kb / (1024 * 1024)  # Convert KB to GB
                    return mem_gb
    except:
        pass
    
    # Fallback: try using free command
    try:
        result = subprocess.run(['free', '-g'], capture_output=True, text=True, check=True)
        for line in result.stdout.splitlines():
            if line.startswith('Mem:'):
                mem_gb = int(line.split()[1])
                return mem_gb
    except:
        pass
    
    return None

def calculate_recommended_makeopts():
    """Calculate recommended MAKEOPTS values based on system specs."""
    print_header("GENTOO MAKEOPTS DETECTOR")
    
    print_info("Detecting system specifications...")
    
    # Get CPU threads
    threads = get_cpu_threads()
    print_info(f"CPU Threads detected: {threads}")
    
    # Get RAM
    ram_gb = get_ram_gb()
    if ram_gb:
        print_info(f"Total RAM detected: {ram_gb:.2f} GB")
    else:
        print_warning("Could not detect RAM, using CPU threads only")
        ram_gb = None
    
    print_separator()
    
    # Calculate recommended values
    # MAKEOPTS_J: min(RAM/2GB, threads) or same as threads (Portage default)
    if ram_gb:
        recommended_j = min(int(ram_gb / 2), threads)
    else:
        recommended_j = threads
    
    # MAKEOPTS_L: slightly above threads (Portage default is slightly above nproc)
    recommended_l = threads + 1
    
    print_info("Recommended MAKEOPTS values:")
    print(f"   {Colors.BOLD}MAKEOPTS_J (jobs):{Colors.RESET} {recommended_j}")
    print(f"   {Colors.BOLD}MAKEOPTS_L (load-average):{Colors.RESET} {recommended_l}")
    print()
    
    if ram_gb:
        print_info("Calculation details:")
        print(f"   - RAM/2GB = {ram_gb:.2f}/2 = {ram_gb/2:.2f}")
        print(f"   - min({ram_gb/2:.2f}, {threads}) = {recommended_j}")
        print(f"   - Load average = {threads} + 1 = {recommended_l}")
    else:
        print_info("Calculation details:")
        print(f"   - Using Portage default: jobs = threads = {recommended_j}")
        print(f"   - Load average = {threads} + 1 = {recommended_l}")
    
    print_separator()
    
    return recommended_j, recommended_l

def main():
    """Main function to detect and configure MAKEOPTS."""
    ensure_config()
    
    # Calculate recommended values
    recommended_j, recommended_l = calculate_recommended_makeopts()
    
    # Get current values
    current_j = cfg_get("MAKEOPTS_J")
    current_l = cfg_get("MAKEOPTS_L")
    
    if current_j is not None or current_l is not None:
        print_info("Current MAKEOPTS values in config:")
        print(f"   MAKEOPTS_J: {current_j if current_j is not None else 'Not set'}")
        print(f"   MAKEOPTS_L: {current_l if current_l is not None else 'Not set'}")
        print_separator()
    
    # Ask user what they want to do
    print_info("What would you like to do?")
    print("   1. Set recommended values automatically in config.jsonc")
    print("   2. Just display recommended values (don't modify config)")
    print()
    
    while True:
        try:
            choice = input(f"{Colors.CYAN}Enter your choice (1 or 2): {Colors.RESET}").strip()
            
            if choice == "1":
                print_separator()
                print_info("Setting recommended MAKEOPTS values in config.jsonc...")
                cfg_set("MAKEOPTS_J", recommended_j)
                cfg_set("MAKEOPTS_L", recommended_l)
                print_success(f"MAKEOPTS_J set to: {recommended_j}")
                print_success(f"MAKEOPTS_L set to: {recommended_l}")
                print_separator()
                print_success("Configuration updated successfully!")
                break
            elif choice == "2":
                print_separator()
                print_info("Recommended values (not saved to config):")
                print(f"   MAKEOPTS_J = {recommended_j}")
                print(f"   MAKEOPTS_L = {recommended_l}")
                print_separator()
                print_info("You can manually set these in config.jsonc if needed.")
                break
            else:
                print_error("Invalid choice. Please enter 1 or 2.")
        except KeyboardInterrupt:
            print("\n")
            print_warning("Operation cancelled by user.")
            sys.exit(0)
        except EOFError:
            print("\n")
            print_warning("Operation cancelled.")
            sys.exit(0)

if __name__ == "__main__":
    main()

