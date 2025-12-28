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

def cfg_set(key, value):
    data = _load()
    data[key] = value
    _save(data)

def detect_and_set_locale():
    result = subprocess.run(
        ["eselect", "locale", "list"],
        capture_output=True,
        text=True,
        check=True
    )

    for line in result.stdout.splitlines():
        if "en_US.utf8" in line:
            match = re.search(r"\[(\d+)\]", line)
            if match:
                cfg_set("LOCALE", int(match.group(1)))
                return

    raise RuntimeError("en_US.utf8 not found in eselect locale list")
