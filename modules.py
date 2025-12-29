import json
import re
import subprocess
import os

CONFIG_FILE = "config.jsonc"

def _load():
    with open(CONFIG_FILE, encoding="utf-8") as f:
        lines = f.readlines()

    clean_lines = []
    for line in lines:
        # Remove // comments only if they are not inside quotes
        if '//' in line:
            parts = line.split('//')
            in_string = False
            clean_line = ''
            for i, c in enumerate(line):
                if c == '"':
                    in_string = not in_string
                if line[i:i+2] == '//' and not in_string:
                    break  # stop at comment outside string
                clean_line += c
            clean_lines.append(clean_line.rstrip() + '\n')
        else:
            clean_lines.append(line)

    content = ''.join(clean_lines)
    return json.loads(content)



def _save(data):
    """Save configuration to file."""
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=2)

def cfg_get(key, default=None):
    """Get a value from the config."""
    data = _load()
    return data.get(key, default)

def cfg_set(key, value):
    """Set a value in the config."""
    data = _load()
    data[key] = value
    _save(data)

def detect_and_set_locale():
    """Detect and set the locale from eselect."""
    current_locale = cfg_get("LOCALE")
    
    # If LOCALE is 1, try to auto-detect (1 is the "auto-detect" flag)
    # If LOCALE is 0 or any other number, use that number directly
    if current_locale == 1:
        try:
            # Run eselect locale list and capture output
            result = subprocess.run(
                ["eselect", "locale", "list"],
                capture_output=True,
                text=True,
                check=True
            )
            output = result.stdout
            
            # Search for en_US.utf8 or en_US.UTF-8 in the output (case insensitive)
            for line in output.splitlines():
                if "en_US.utf8" in line.lower() or "en_US.UTF-8" in line:
                    match = re.search(r"\[(\d+)\]", line)
                    if match:
                        number = int(match.group(1))
                        cfg_set("LOCALE", number)
                        print(f"LOCALE set to en_US.utf8 (number {number})")
                        return number
            
            # If not found, try to find any en_US locale
            for line in output.splitlines():
                if "en_US" in line.lower():
                    match = re.search(r"\[(\d+)\]", line)
                    if match:
                        number = int(match.group(1))
                        cfg_set("LOCALE", number)
                        print(f"LOCALE set to en_US variant (number {number})")
                        return number
            
            # If still not found, use default value 0 and let the user set it manually
            print("WARNING: en_US.utf8 not found in eselect locale list, using default")
            return 0
        
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            # If eselect doesn't exist or fails, just use the config value
            print(f"WARNING: Could not run eselect locale list: {e}")
            print("Using LOCALE from config or defaulting to 0")
            # If auto-detect failed, return 0 as fallback
            return 0
    
    print(f"LOCALE already set to {current_locale}, leaving as-is")
    return current_locale

# Optional: Add a function to get all config at once
def cfg_get_all():

    return _load()

# Optional: Add a function to validate config
def cfg_validate():

    required_keys = [
        "USERNAME", "HOSTNAME", "ROOTPT", "EFIPT", "SWAPPT",
        "MAKEOPTS_J", "MAKEOPTS_L", "INIT", "URL", "PROFILE",
        "ZONEINFO", "LOCALE", "ROOT_PASSWORD", "USER_PASSWORD"
    ]
    
    data = _load()
    missing = [key for key in required_keys if key not in data]
    
    if missing:
        raise ValueError(f"Missing required config keys: {missing}")
    
    return True

def apply_password(username, password):
    if not password:
        raise RuntimeError(f"Password for {username} is empty")

    os.system(f'echo "{username}:{password}" | chpasswd')

def ensure_config():
    if not os.path.exists(CONFIG_FILE):
        content = "// Gentoo install configuration file\n"
        content += json.dumps(DEFAULT_CONFIG, indent=2)
        with open(CONFIG_FILE, "w") as f:
            f.write(content)
        print(f"{CONFIG_FILE} created with default values.")
    else:
        print(f"{CONFIG_FILE} already exists.")

DEFAULT_CONFIG = {
    "ROOTPT": "/dev/",
    "EFIPT": "/dev/",
    "SWAPPT": "sda5",
    "URL": "https://your-profile-url",
    "PROFILE": 0,
    "HOSTNAME": "gentoo-pc",
    "USERNAME": "user",
    "ZONEINFO": "Europe/Bucharest",
    "LOCALE": 0,
    "ROOT_PASSWORD": "",
    "USER_PASSWORD": ""
}
