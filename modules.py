import json
import re
import subprocess

CONFIG_FILE = "config.jsonc"

def _load():
    with open(CONFIG_FILE, "r") as f:
        content = re.sub(r"//.*", "", f.read())
    return json.loads(content)

def _save(data):
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
    current_locale = cfg_get("LOCALE")
    
    if current_locale == 1:
        # Run eselect locale list and capture output
        output = os.popen("eselect locale list").read()
        
        for line in output.splitlines():
            if "en_US.utf8" in line:
                match = re.search(r"\[(\d+)\]", line)
                if match:
                    number = int(match.group(1))
                    cfg_set("LOCALE", number)
                    print(f"LOCALE set to en_US.utf8 (number {number})")
                    return number
        
        raise RuntimeError("en_US.utf8 not found in eselect locale list")
    
    print(f"LOCALE already set to {current_locale}, leaving as-is")
    return current_locale