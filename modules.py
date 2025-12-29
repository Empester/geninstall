import json
import re
import subprocess
import os
import requests
import time
from urllib.parse import urlparse

# Try to import statistics, fallback to manual calculation
try:
    import statistics
    HAS_STATISTICS = True
except ImportError:
    HAS_STATISTICS = False

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
                        print(f"\033[92m✓ LOCALE set to en_US.utf8 (number {number})\033[0m")
                        return number
            
            # If not found, try to find any en_US locale
            for line in output.splitlines():
                if "en_US" in line.lower():
                    match = re.search(r"\[(\d+)\]", line)
                    if match:
                        number = int(match.group(1))
                        cfg_set("LOCALE", number)
                        print(f"\033[92m✓ LOCALE set to en_US variant (number {number})\033[0m")
                        return number
            
            # If still not found, use default value 0 and let the user set it manually
            print(f"\033[93m⚠ WARNING: en_US.utf8 not found in eselect locale list, using default\033[0m")
            return 0
        
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            # If eselect doesn't exist or fails, just use the config value
            print(f"\033[93m⚠ WARNING: Could not run eselect locale list: {e}\033[0m")
            print(f"\033[96mℹ Using LOCALE from config or defaulting to 0\033[0m")
            # If auto-detect failed, return 0 as fallback
            return 0
    
    print(f"\033[96mℹ LOCALE already set to {current_locale}, leaving as-is\033[0m")
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

# Gentoo mirror list - comprehensive list from https://www.gentoo.org/downloads/mirrors/
# Includes country, protocol, IPv4/IPv6 support, and full URL
GENTOO_MIRRORS = [
    # North America - Canada
    {"url": "https://gentoo.mirrors.tera-byte.com/", "name": "Tera-byte Dot Com Inc", "country": "CA", "protocol": "https", "ipv6": False},
    {"url": "http://gentoo.mirrors.tera-byte.com/", "name": "Tera-byte Dot Com Inc", "country": "CA", "protocol": "http", "ipv6": False},
    {"url": "https://mirror.csclub.uwaterloo.ca/gentoo-distfiles/", "name": "University of Waterloo", "country": "CA", "protocol": "https", "ipv6": True},
    {"url": "http://mirror.csclub.uwaterloo.ca/gentoo-distfiles/", "name": "University of Waterloo", "country": "CA", "protocol": "http", "ipv6": True},
    {"url": "https://mirror.reenigne.net/gentoo/", "name": "Reenigne", "country": "CA", "protocol": "https", "ipv6": True},
    {"url": "http://mirror.reenigne.net/gentoo/", "name": "Reenigne", "country": "CA", "protocol": "http", "ipv6": True},
    {"url": "https://gentoo.mirrors.ovh.net/gentoo-distfiles/", "name": "OVHcloud", "country": "CA", "protocol": "https", "ipv6": False},
    {"url": "http://gentoo.mirrors.ovh.net/gentoo-distfiles/", "name": "OVHcloud", "country": "CA", "protocol": "http", "ipv6": False},
    {"url": "https://stygian.failzero.net/mirror/gentoo", "name": "FailZero / Genesis Hosting", "country": "CA", "protocol": "https", "ipv6": True},
    {"url": "https://ca.mirrors.cicku.me/gentoo/", "name": "CICKU", "country": "CA", "protocol": "https", "ipv6": True},
    {"url": "http://ca.mirrors.cicku.me/gentoo/", "name": "CICKU", "country": "CA", "protocol": "http", "ipv6": True},
    {"url": "https://elara.ca.ext.planetunix.net/pub/gentoo/", "name": "PlanetUnix Networks", "country": "CA", "protocol": "https", "ipv6": True},
    {"url": "http://elara.ca.ext.planetunix.net/pub/gentoo/", "name": "PlanetUnix Networks", "country": "CA", "protocol": "http", "ipv6": True},
    
    # North America - United States
    {"url": "https://gentoo.osuosl.org/", "name": "OSU Open Source Lab", "country": "US", "protocol": "https", "ipv6": True},
    {"url": "http://gentoo.osuosl.org/", "name": "OSU Open Source Lab", "country": "US", "protocol": "http", "ipv6": True},
    {"url": "https://mirror.leaseweb.com/gentoo/", "name": "LeaseWeb", "country": "US", "protocol": "https", "ipv6": True},
    {"url": "http://mirror.leaseweb.com/gentoo/", "name": "LeaseWeb", "country": "US", "protocol": "http", "ipv6": True},
    {"url": "http://www.gtlib.gatech.edu/pub/gentoo", "name": "Georgia Tech", "country": "US", "protocol": "http", "ipv6": False},
    {"url": "http://gentoo-mirror.flux.utah.edu/", "name": "University of Utah", "country": "US", "protocol": "http", "ipv6": False},
    {"url": "https://mirrors.mit.edu/gentoo-distfiles/", "name": "Massachusetts Institute of Technology", "country": "US", "protocol": "https", "ipv6": False},
    {"url": "http://mirrors.mit.edu/gentoo-distfiles/", "name": "Massachusetts Institute of Technology", "country": "US", "protocol": "http", "ipv6": False},
    {"url": "https://mirrors.rit.edu/gentoo/", "name": "Rochester Institute of Technology", "country": "US", "protocol": "https", "ipv6": True},
    {"url": "http://mirrors.rit.edu/gentoo/", "name": "Rochester Institute of Technology", "country": "US", "protocol": "http", "ipv6": True},
    {"url": "https://mirror.rackspace.com/gentoo/", "name": "Rackspace Technology", "country": "US", "protocol": "https", "ipv6": False},
    {"url": "https://mirror.clarkson.edu/gentoo/", "name": "Clarkson University", "country": "US", "protocol": "https", "ipv6": True},
    {"url": "https://mirror.servaxnet.com/gentoo/", "name": "ServaxNet", "country": "US", "protocol": "https", "ipv6": True},
    
    # South America
    {"url": "https://mirror.ufscar.br/gentoo/", "name": "Universidade Federal de São Carlos", "country": "BR", "protocol": "https", "ipv6": True},
    {"url": "https://mirror.unesp.br/gentoo/", "name": "Universidade Estadual Paulista", "country": "BR", "protocol": "https", "ipv6": True},
    {"url": "https://mirror.ufro.cl/gentoo/", "name": "Universidad de La Frontera", "country": "CL", "protocol": "https", "ipv6": True},
    
    # Europe - Austria
    {"url": "https://mirror.easyname.at/gentoo/", "name": "Easyname", "country": "AT", "protocol": "https", "ipv6": True},
    {"url": "https://mirror.23media.com/gentoo/", "name": "23media", "country": "AT", "protocol": "https", "ipv6": True},
    
    # Europe - Belgium
    {"url": "https://ftp.belnet.be/mirror/gentoo/", "name": "BELNET", "country": "BE", "protocol": "https", "ipv6": True},
    
    # Europe - Bulgaria
    {"url": "https://mirror.telepoint.bg/gentoo/", "name": "Telepoint", "country": "BG", "protocol": "https", "ipv6": True},
    
    # Europe - Switzerland
    {"url": "https://mirror.init7.net/gentoo/", "name": "Init7", "country": "CH", "protocol": "https", "ipv6": True},
    {"url": "https://mirror.cyberbits.eu/gentoo/", "name": "Cyberbits", "country": "CH", "protocol": "https", "ipv6": True},
    
    # Europe - Czech Republic
    {"url": "https://mirror.dkm.cz/gentoo/", "name": "DKM", "country": "CZ", "protocol": "https", "ipv6": True},
    {"url": "https://mirror.karneval.cz/pub/linux/gentoo/", "name": "Karneval", "country": "CZ", "protocol": "https", "ipv6": True},
    
    # Europe - Denmark
    {"url": "https://mirror.one.com/gentoo/", "name": "One.com", "country": "DK", "protocol": "https", "ipv6": True},
    
    # Europe - France
    {"url": "https://mirror.ibcp.fr/pub/gentoo/", "name": "IBCP", "country": "FR", "protocol": "https", "ipv6": True},
    {"url": "https://mirror.ovh.net/gentoo-distfiles/", "name": "OVH", "country": "FR", "protocol": "https", "ipv6": True},
    {"url": "https://mirror.crexio.com/gentoo/", "name": "Crexio", "country": "FR", "protocol": "https", "ipv6": True},
    
    # Europe - Germany
    {"url": "https://ftp.fau.de/gentoo", "name": "FAU", "country": "DE", "protocol": "https", "ipv6": True},
    {"url": "https://ftp.agdsn.de/gentoo", "name": "AGDSN", "country": "DE", "protocol": "https", "ipv6": True},
    {"url": "https://ftp-stud.hs-esslingen.de/pub/Mirrors/gentoo/", "name": "Esslingen", "country": "DE", "protocol": "https", "ipv6": True},
    {"url": "https://mirror.netcologne.de/gentoo/", "name": "NetCologne", "country": "DE", "protocol": "https", "ipv6": True},
    {"url": "https://ftp.halifax.rwth-aachen.de/gentoo/", "name": "RWTH Aachen", "country": "DE", "protocol": "https", "ipv6": True},
    {"url": "https://ftp.gwdg.de/pub/linux/gentoo/", "name": "GWDG", "country": "DE", "protocol": "https", "ipv6": True},
    {"url": "https://ftp.tu-ilmenau.de/mirror/gentoo/", "name": "TU Ilmenau", "country": "DE", "protocol": "https", "ipv6": True},
    {"url": "https://ftp.uni-hannover.de/gentoo/", "name": "Uni Hannover", "country": "DE", "protocol": "https", "ipv6": True},
    {"url": "https://ftp.uni-stuttgart.de/gentoo-distfiles/", "name": "Uni Stuttgart", "country": "DE", "protocol": "https", "ipv6": True},
    {"url": "https://ftp.spline.inf.fu-berlin.de/mirrors/gentoo/", "name": "FU Berlin", "country": "DE", "protocol": "https", "ipv6": True},
    {"url": "https://mirror.netzwerge.de/gentoo/", "name": "Netzwerge", "country": "DE", "protocol": "https", "ipv6": True},
    {"url": "https://mirror.dogado.de/gentoo/", "name": "Dogado", "country": "DE", "protocol": "https", "ipv6": True},
    {"url": "https://mirror.23media.de/gentoo/", "name": "23media", "country": "DE", "protocol": "https", "ipv6": True},
    
    # Europe - Greece
    {"url": "https://ftp.cc.uoc.gr/mirrors/gentoo/", "name": "University of Crete", "country": "GR", "protocol": "https", "ipv6": True},
    {"url": "https://ftp.ntua.gr/pub/linux/gentoo/", "name": "NTUA", "country": "GR", "protocol": "https", "ipv6": True},
    
    # Europe - Hungary
    {"url": "https://mirror.kif.hu/gentoo/", "name": "KIF", "country": "HU", "protocol": "https", "ipv6": True},
    
    # Europe - Ireland
    {"url": "https://ftp.heanet.ie/mirrors/gentoo/", "name": "HEAnet", "country": "IE", "protocol": "https", "ipv6": True},
    
    # Europe - Italy
    {"url": "https://mirror.garr.it/mirrors/gentoo/", "name": "GARR", "country": "IT", "protocol": "https", "ipv6": True},
    
    # Europe - Luxembourg
    {"url": "https://mirror.one.com/gentoo/", "name": "One.com", "country": "LU", "protocol": "https", "ipv6": True},
    
    # Europe - Netherlands
    {"url": "https://ftp.nluug.nl/os/Linux/distr/gentoo/", "name": "NLUUG", "country": "NL", "protocol": "https", "ipv6": True},
    
    # Europe - Portugal
    {"url": "https://mirrors.ua.pt/gentoo/", "name": "University of Aveiro", "country": "PT", "protocol": "https", "ipv6": True},
    
    # Europe - Romania
    {"url": "https://mirrors.ua.pt/gentoo/", "name": "University of Aveiro", "country": "RO", "protocol": "https", "ipv6": True},
    
    # Europe - Sweden
    {"url": "https://ftp.lysator.liu.se/pub/gentoo/", "name": "Lysator", "country": "SE", "protocol": "https", "ipv6": True},
    
    # Europe - Spain
    {"url": "https://ftp.rediris.es/mirror/gentoo/", "name": "RedIRIS", "country": "ES", "protocol": "https", "ipv6": True},
    {"url": "https://mirror.ua.es/gentoo/", "name": "University of Alicante", "country": "ES", "protocol": "https", "ipv6": True},
    
    # Europe - Turkey
    {"url": "https://mirror.veriteknik.net.tr/gentoo/", "name": "VeriTeknik", "country": "TR", "protocol": "https", "ipv6": True},
    
    # Europe - United Kingdom
    {"url": "https://mirror.bytemark.co.uk/gentoo/", "name": "Bytemark", "country": "UK", "protocol": "https", "ipv6": True},
    
    # Australia and Oceania
    {"url": "https://mirror.aarnet.edu.au/pub/gentoo/", "name": "AARNet", "country": "AU", "protocol": "https", "ipv6": True},
    
    # Asia - China
    {"url": "https://mirrors.ustc.edu.cn/gentoo/", "name": "USTC", "country": "CN", "protocol": "https", "ipv6": True},
    {"url": "https://mirrors.tuna.tsinghua.edu.cn/gentoo/", "name": "TUNA", "country": "CN", "protocol": "https", "ipv6": True},
    {"url": "https://mirrors.aliyun.com/gentoo/", "name": "Aliyun", "country": "CN", "protocol": "https", "ipv6": True},
    {"url": "https://mirrors.163.com/gentoo/", "name": "163", "country": "CN", "protocol": "https", "ipv6": True},
    {"url": "https://mirrors.dgut.edu.cn/gentoo/", "name": "DGUT", "country": "CN", "protocol": "https", "ipv6": True},
    {"url": "https://mirrors.hit.edu.cn/gentoo/", "name": "HIT", "country": "CN", "protocol": "https", "ipv6": True},
    {"url": "https://mirrors.nju.edu.cn/gentoo/", "name": "NJU", "country": "CN", "protocol": "https", "ipv6": True},
    {"url": "https://mirror.lzu.edu.cn/gentoo", "name": "Lanzhou University", "country": "CN", "protocol": "https", "ipv6": True},
    
    # Asia - Hong Kong
    {"url": "http://gentoo.aditsu.net:8000/", "name": "aditsu.net", "country": "HK", "protocol": "http", "ipv6": False},
    
    # Asia - India
    {"url": "https://mirrors.nxtgen.com/gentoo-mirror/gentoo-source/", "name": "NxtGen", "country": "IN", "protocol": "https", "ipv6": True},
    
    # Asia - Japan
    {"url": "http://ftp.iij.ad.jp/pub/linux/gentoo/", "name": "Internet Initiative Japan", "country": "JP", "protocol": "http", "ipv6": True},
    {"url": "https://ftp.jaist.ac.jp/pub/Linux/Gentoo/", "name": "JAIST", "country": "JP", "protocol": "https", "ipv6": True},
    {"url": "https://ftp.riken.jp/Linux/gentoo/", "name": "RIKEN", "country": "JP", "protocol": "https", "ipv6": True},
    {"url": "https://repo.jing.rocks/gentoo", "name": "Jing Luo", "country": "JP", "protocol": "https", "ipv6": True},
    
    # Asia - Kazakhstan
    {"url": "https://mirror.ps.kz/gentoo/pub", "name": "PS Internet Company LLC", "country": "KZ", "protocol": "https", "ipv6": True},
    
    # Asia - Korea
    {"url": "http://ftp.kaist.ac.kr/pub/gentoo/", "name": "KAIST", "country": "KR", "protocol": "http", "ipv6": True},
    {"url": "https://ftp.lanet.kr/pub/gentoo/", "name": "lanet.kr", "country": "KR", "protocol": "https", "ipv6": True},
    
    # Asia - Belarus
    {"url": "http://ftp.byfly.by/pub/gentoo-distfiles/", "name": "ftp.byfly.by", "country": "BY", "protocol": "http", "ipv6": False},
    
    # Asia - Russia
    {"url": "https://mirror.yandex.ru/gentoo-distfiles/", "name": "Yandex.ru", "country": "RU", "protocol": "https", "ipv6": True},
    {"url": "http://mirror.yandex.ru/gentoo-distfiles/", "name": "Yandex.ru", "country": "RU", "protocol": "http", "ipv6": True},
    {"url": "https://gentoo-mirror.alexxy.name/", "name": "Alexxy.name", "country": "RU", "protocol": "https", "ipv6": True},
    {"url": "http://gentoo-mirror.alexxy.name/", "name": "Alexxy.name", "country": "RU", "protocol": "http", "ipv6": True},
    {"url": "http://mirror.mephi.ru/gentoo-distfiles/", "name": "National Research Nuclear University - MEPhI", "country": "RU", "protocol": "http", "ipv6": False},
    {"url": "https://ru.mirrors.cicku.me/gentoo/", "name": "CICKU", "country": "RU", "protocol": "https", "ipv6": True},
    {"url": "http://ru.mirrors.cicku.me/gentoo/", "name": "CICKU", "country": "RU", "protocol": "http", "ipv6": True},
    
    # Asia - Singapore
    {"url": "https://mirror.freedif.org/gentoo", "name": "Freedif", "country": "SG", "protocol": "https", "ipv6": True},
    {"url": "http://mirror.freedif.org/gentoo", "name": "Freedif", "country": "SG", "protocol": "http", "ipv6": True},
    
    # Asia - Taiwan
    {"url": "http://ftp.twaren.net/Linux/Gentoo/", "name": "National Center for High-Performance Computing", "country": "TW", "protocol": "http", "ipv6": False},
    
    # Middle East - Israel
    {"url": "https://mirror.isoc.org.il/pub/gentoo/", "name": "Hamakor FOSS Society", "country": "IL", "protocol": "https", "ipv6": True},
    
    # Middle East - Saudi Arabia
    {"url": "https://sa.mirrors.cicku.me/gentoo/", "name": "CICKU", "country": "SA", "protocol": "https", "ipv6": True},
    {"url": "http://sa.mirrors.cicku.me/gentoo/", "name": "CICKU", "country": "SA", "protocol": "http", "ipv6": True},
    
    # Africa - South Africa
    {"url": "https://gentoo.dimensiondata.com/", "name": "Dimension Data", "country": "ZA", "protocol": "https", "ipv6": True},
    {"url": "https://gentoo.uls.co.za/", "name": "Ultimate Linux Solutions", "country": "ZA", "protocol": "https", "ipv6": True},
    {"url": "https://za.mirrors.cicku.me/gentoo/", "name": "CICKU", "country": "ZA", "protocol": "https", "ipv6": True},
    {"url": "http://za.mirrors.cicku.me/gentoo/", "name": "CICKU", "country": "ZA", "protocol": "http", "ipv6": True},
    {"url": "https://mirror.ufs.ac.za/gentoo/", "name": "University of the Free State", "country": "ZA", "protocol": "https", "ipv6": True},
    {"url": "http://mirror.ufs.ac.za/gentoo/", "name": "University of the Free State", "country": "ZA", "protocol": "http", "ipv6": True},
]

def check_mirror_reachable(mirror_url, timeout=5):
    """Check if a mirror URL is reachable and online."""
    try:
        # Ensure URL ends with /
        if not mirror_url.endswith('/'):
            mirror_url = mirror_url + '/'
        
        # Try to fetch a small file or HEAD request
        response = requests.head(mirror_url, timeout=timeout, allow_redirects=True)
        if response.status_code < 400:
            return True
    except requests.exceptions.RequestException:
        pass
    
    # Fallback: try GET with a small timeout
    try:
        response = requests.get(mirror_url, timeout=timeout, allow_redirects=True, stream=True)
        if response.status_code < 400:
            return True
    except requests.exceptions.RequestException:
        pass
    
    return False

def test_mirror_latency(mirror_url, test_cycles=3):
    """Test mirror latency and return average latency, jitter, and success rate."""
    latencies = []
    failures = 0
    
    for cycle in range(test_cycles):
        try:
            start_time = time.time()
            response = requests.head(mirror_url, timeout=5, allow_redirects=True)
            end_time = time.time()
            
            if response.status_code < 400:
                latency = (end_time - start_time) * 1000  # Convert to milliseconds
                latencies.append(latency)
            else:
                failures += 1
        except requests.exceptions.RequestException:
            failures += 1
        
        # Small delay between cycles
        if cycle < test_cycles - 1:
            time.sleep(0.5)
    
    if len(latencies) == 0:
        return None
    
    # Calculate average latency
    avg_latency = sum(latencies) / len(latencies)
    
    # Calculate jitter (standard deviation)
    if len(latencies) > 1:
        if HAS_STATISTICS:
            jitter = statistics.stdev(latencies)
        else:
            # Manual calculation of standard deviation
            mean = avg_latency
            variance = sum((x - mean) ** 2 for x in latencies) / (len(latencies) - 1)
            jitter = variance ** 0.5
    else:
        jitter = 0
    
    success_rate = len(latencies) / (len(latencies) + failures)
    
    return {
        "avg_latency": avg_latency,
        "jitter": jitter,
        "success_rate": success_rate,
        "latencies": latencies
    }

def analyze_and_select_best_mirror():
    """Analyze all mirrors and select the best one based on latency, jitter, and reliability."""
    print(f"\033[1m\033[94m{'='*70}\033[0m")
    print(f"\033[1m\033[94mGENTOO MIRROR ANALYZER - Finding Best Mirror\033[0m")
    print(f"\033[1m\033[94m{'='*70}\033[0m\n")
    
    print(f"\033[96mℹ Analyzing {len(GENTOO_MIRRORS)} mirrors from official Gentoo mirror list\033[0m")
    print(f"\033[96mℹ Source: https://www.gentoo.org/downloads/mirrors/\033[0m")
    print(f"\033[96mℹ This may take a few minutes. Testing latency and reliability...\033[0m\n")
    
    results = []
    total_mirrors = len(GENTOO_MIRRORS)
    
    for idx, mirror in enumerate(GENTOO_MIRRORS, 1):
        mirror_url = mirror["url"]
        mirror_name = mirror["name"]
        mirror_country = mirror.get("country", "Unknown")
        mirror_protocol = mirror.get("protocol", "https")
        mirror_ipv6 = mirror.get("ipv6", False)
        
        print(f"\033[96mℹ [{idx}/{total_mirrors}] Testing: {mirror_name}\033[0m")
        print(f"   \033[93m📍 Location: {mirror_country}\033[0m")
        print(f"   \033[93m🔗 Protocol: {mirror_protocol.upper()}\033[0m")
        print(f"   \033[93m🌐 IPv6 Support: {'Yes' if mirror_ipv6 else 'No'}\033[0m")
        print(f"   \033[93m🔗 URL: {mirror_url}\033[0m")
        
        # Check if reachable first
        if not check_mirror_reachable(mirror_url):
            print(f"   \033[91m✗ Mirror is unreachable or offline\033[0m\n")
            continue
        
        print(f"   \033[92m✓ Mirror is online, testing latency...\033[0m")
        
        # Test latency
        test_result = test_mirror_latency(mirror_url, test_cycles=5)
        
        if test_result is None:
            print(f"   \033[91m✗ Failed to get latency data\033[0m\n")
            continue
        
        avg_latency = test_result["avg_latency"]
        jitter = test_result["jitter"]
        success_rate = test_result["success_rate"]
        
        print(f"   \033[92m✓ Average latency: {avg_latency:.2f}ms\033[0m")
        print(f"   \033[92m✓ Jitter: {jitter:.2f}ms\033[0m")
        print(f"   \033[92m✓ Success rate: {success_rate*100:.1f}%\033[0m")
        
        # Calculate score (lower is better)
        # Weight: latency 60%, jitter 20%, success_rate 20%
        score = (avg_latency * 0.6) + (jitter * 0.2) + ((1 - success_rate) * 1000 * 0.2)
        
        results.append({
            "url": mirror_url,
            "name": mirror_name,
            "country": mirror_country,
            "protocol": mirror_protocol,
            "ipv6": mirror_ipv6,
            "avg_latency": avg_latency,
            "jitter": jitter,
            "success_rate": success_rate,
            "score": score
        })
        
        print(f"   \033[93mℹ Quality score: {score:.2f}\033[0m\n")
    
    if len(results) == 0:
        print(f"\033[91m✗ ERROR: No working mirrors found!\033[0m")
        return None
    
    # Sort by score (lower is better)
    results.sort(key=lambda x: x["score"])
    best_mirror = results[0]
    
    print(f"\033[1m\033[94m{'='*70}\033[0m")
    print(f"\033[1m\033[94mMIRROR ANALYSIS COMPLETE\033[0m")
    print(f"\033[1m\033[94m{'='*70}\033[0m\n")
    
    print(f"\033[92m✓ Found {len(results)} working mirrors\033[0m\n")
    
    print(f"\033[1m\033[92m🏆 BEST MIRROR SELECTED:\033[0m")
    print(f"   Name: {best_mirror['name']}")
    print(f"   Location: {best_mirror.get('country', 'Unknown')}")
    print(f"   Protocol: {best_mirror.get('protocol', 'https').upper()}")
    print(f"   IPv6 Support: {'Yes' if best_mirror.get('ipv6', False) else 'No'}")
    print(f"   URL: {best_mirror['url']}")
    print(f"   Average Latency: {best_mirror['avg_latency']:.2f}ms")
    print(f"   Jitter: {best_mirror['jitter']:.2f}ms")
    print(f"   Success Rate: {best_mirror['success_rate']*100:.1f}%")
    print(f"   Quality Score: {best_mirror['score']:.2f}\n")
    
    if len(results) > 1:
        print(f"\033[96mℹ Top 3 mirrors:\033[0m")
        for i, result in enumerate(results[:3], 1):
            country_info = f" ({result.get('country', 'Unknown')})" if result.get('country') else ""
            print(f"   {i}. {result['name']}{country_info} - {result['avg_latency']:.2f}ms avg")
        print()
    
    return best_mirror["url"]

def validate_and_set_mirror():
    """Validate the MIRROR config value and auto-select if invalid."""
    print(f"\033[1m\033[94m{'='*70}\033[0m")
    print(f"\033[1m\033[94mMIRROR VALIDATION AND CONFIGURATION\033[0m")
    print(f"\033[1m\033[94m{'='*70}\033[0m\n")
    
    current_mirror = cfg_get("MIRROR", "")
    
    # Check if MIRROR is blank or invalid
    if not current_mirror or current_mirror.strip() == "":
        print(f"\033[93m⚠ MIRROR value is empty or blank\033[0m")
        print(f"\033[96mℹ Triggering automatic mirror selection...\033[0m\n")
        best_mirror = analyze_and_select_best_mirror()
        if best_mirror:
            cfg_set("MIRROR", best_mirror)
            print(f"\033[92m✓ MIRROR automatically set to: {best_mirror}\033[0m\n")
            return best_mirror
        else:
            print(f"\033[91m✗ ERROR: Could not find a working mirror!\033[0m")
            return None
    
    # Check if it looks like a valid URL
    try:
        parsed = urlparse(current_mirror)
        if not parsed.scheme or not parsed.netloc:
            print(f"\033[93m⚠ MIRROR value doesn't look like a valid URL: {current_mirror}\033[0m")
            print(f"\033[96mℹ Triggering automatic mirror selection...\033[0m\n")
            best_mirror = analyze_and_select_best_mirror()
            if best_mirror:
                cfg_set("MIRROR", best_mirror)
                print(f"\033[92m✓ MIRROR automatically set to: {best_mirror}\033[0m\n")
                return best_mirror
            else:
                print(f"\033[91m✗ ERROR: Could not find a working mirror!\033[0m")
                return None
    except Exception:
        print(f"\033[93m⚠ MIRROR value appears invalid: {current_mirror}\033[0m")
        print(f"\033[96mℹ Triggering automatic mirror selection...\033[0m\n")
        best_mirror = analyze_and_select_best_mirror()
        if best_mirror:
            cfg_set("MIRROR", best_mirror)
            print(f"\033[92m✓ MIRROR automatically set to: {best_mirror}\033[0m\n")
            return best_mirror
        else:
            print(f"\033[91m✗ ERROR: Could not find a working mirror!\033[0m")
            return None
    
    # Validate that the mirror is reachable
    print(f"\033[96mℹ Validating configured mirror: {current_mirror}\033[0m")
    print(f"\033[96mℹ Checking if mirror is online and reachable...\033[0m")
    
    if check_mirror_reachable(current_mirror):
        print(f"\033[92m✓ Mirror is online and reachable!\033[0m")
        print(f"\033[92m✓ Using configured mirror: {current_mirror}\033[0m\n")
        return current_mirror
    else:
        print(f"\033[91m✗ Mirror is unreachable or offline\033[0m")
        print(f"\033[96mℹ Triggering automatic mirror selection...\033[0m\n")
        best_mirror = analyze_and_select_best_mirror()
        if best_mirror:
            cfg_set("MIRROR", best_mirror)
            print(f"\033[92m✓ MIRROR automatically set to: {best_mirror}\033[0m\n")
            return best_mirror
        else:
            print(f"\033[91m✗ ERROR: Could not find a working mirror!\033[0m")
            return None

DEFAULT_CONFIG = {

    "USERNAME": "MyNewUser",
    "HOSTNAME": "gentoo",
    "ROOTPT": "/dev/",
    "EFIPT": "/dev/",
    "SWAPPT": "/dev/",
    "SKIP":"y",
    "MAKEOPTS_J": 2,
    "MAKEOPTS_L": 3,
    "INIT": "systemd",
    "URL": "https://gentoo.osuosl.org/releases/amd64/autobuilds/current-stage3-amd64-systemd/latest-stage3-amd64-systemd.txt",
    "MIRROR":"sahur",
    "PROFILE": 2,
    "ZONEINFO": "Europe/Bucharest",
    "LOCALE": 1,
    "ROOT_PASSWORD": "",
    "USER_PASSWORD":""
    
}
