import json
import re
import subprocess
import os

CONFIG_FILE = "config.jsonc"

def _load():
    """Load and parse JSONC configuration file."""
    with open(CONFIG_FILE, "r") as f:
        content = f.read()
    
    # Remove single-line comments (// ...)
    content = re.sub(r'//.*?$', '', content, flags=re.MULTILINE)
    # Remove multi-line comments (/* ... */)
    content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
    
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

def detect_and_set_locale_os():
    """Detect and set the locale from eselect."""
    current_locale = cfg_get("LOCALE")
    
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
            
            # Search for en_US.utf8 in the output
            for line in output.splitlines():
                if "en_US.utf8" in line:
                    match = re.search(r"\[(\d+)\]", line)
                    if match:
                        number = int(match.group(1))
                        cfg_set("LOCALE", number)
                        print(f"LOCALE set to en_US.utf8 (number {number})")
                        return number
            
            raise RuntimeError("en_US.utf8 not found in eselect locale list")
        
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to run eselect: {e}")
    
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