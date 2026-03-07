import os
import subprocess
import socket
import hashlib
import base64
import urllib.parse
import re
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt
from rich import box


class ToolsMenu:
    def __init__(self, console: Console):
        self.console = console

    def run(self):
        while True:
            self.show_menu()
            choice = Prompt.ask("  [cyan]Select tool[/cyan]", default="0")
            if choice == "0":
                break
            elif choice == "1":
                self.port_scanner()
            elif choice == "2":
                self.dns_lookup()
            elif choice == "3":
                self.whois_lookup()
            elif choice == "4":
                self.hash_tool()
            elif choice == "5":
                self.encoder_decoder()
            elif choice == "6":
                self.ip_info()
            elif choice == "7":
                self.header_grabber()
            elif choice == "8":
                self.subdomain_scanner()
            elif choice == "9":
                self.wordlist_generator()
            elif choice == "10":
                self.cidr_calculator()
            else:
                self.console.print("  [red]Invalid choice.[/red]")

    def show_menu(self):
        t = Table(
            title="[bold cyan]HexMind Built-in Tools[/bold cyan]",
            box=box.ROUNDED, border_style="cyan"
        )
        t.add_column("#",    style="bold cyan", width=4)
        t.add_column("Tool", style="bold white")
        t.add_column("Description", style="dim white")
        tools = [
            ("1",  "Port Scanner",         "Quick TCP port scan on a target"),
            ("2",  "DNS Lookup",            "Resolve domain to IPs, MX, NS records"),
            ("3",  "Whois Lookup",          "Get domain/IP registration info"),
            ("4",  "Hash Tool",             "Hash text with MD5/SHA1/SHA256/SHA512"),
            ("5",  "Encoder / Decoder",     "Base64, URL encode/decode, hex"),
            ("6",  "IP Info",               "Your public IP and geolocation"),
            ("7",  "Header Grabber",        "Fetch HTTP headers from a URL"),
            ("8",  "Subdomain Scanner",     "Brute-force subdomains from a wordlist"),
            ("9",  "Wordlist Generator",    "Generate custom wordlists from keywords"),
            ("10", "CIDR Calculator",       "Calculate IP range from CIDR notation"),
            ("0",  "Back",                  "Return to chat"),
        ]
        for r in tools:
            t.add_row(*r)
        self.console.print(t)

    def port_scanner(self):
        self.console.print("\n  [bold cyan]Port Scanner[/bold cyan]")
        target = Prompt.ask("  Target (host/IP)")
        ports_input = Prompt.ask("  Port range", default="1-1024")
        timeout = float(Prompt.ask("  Timeout (seconds)", default="0.5"))

        try:
            start, end = (int(x) for x in ports_input.split("-"))
        except Exception:
            start = end = int(ports_input)

        self.console.print(f"\n  [yellow]Scanning {target} ports {start}-{end}...[/yellow]\n")
        open_ports = []

        for port in range(start, end + 1):
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(timeout)
                result = s.connect_ex((target, port))
                if result == 0:
                    try:
                        service = socket.getservbyport(port)
                    except Exception:
                        service = "unknown"
                    open_ports.append((port, service))
                    self.console.print(f"  [bold green][OPEN][/bold green] Port {port:<6} {service}")
                s.close()
            except Exception:
                pass

        if not open_ports:
            self.console.print("  [dim]No open ports found in this range.[/dim]")
        else:
            self.console.print(f"\n  [bold green]Found {len(open_ports)} open port(s).[/bold green]")
        self.console.print()

    def dns_lookup(self):
        import socket
        self.console.print("\n  [bold cyan]DNS Lookup[/bold cyan]")
        domain = Prompt.ask("  Enter domain")
        self.console.print(f"\n  [yellow]Looking up {domain}...[/yellow]\n")

        try:
            ip = socket.gethostbyname(domain)
            self.console.print(f"  [bold green]A Record:[/bold green]  {ip}")
        except Exception as e:
            self.console.print(f"  [red]A record failed: {e}[/red]")

        try:
            result = subprocess.run(["nslookup", domain], capture_output=True, text=True, timeout=10)
            if result.stdout:
                self.console.print(f"\n  [dim]{result.stdout}[/dim]")
        except Exception:
            pass

        try:
            for rtype in ["MX", "NS", "TXT"]:
                result = subprocess.run(["dig", "+short", rtype, domain], capture_output=True, text=True, timeout=10)
                if result.stdout.strip():
                    self.console.print(f"  [bold cyan]{rtype} Records:[/bold cyan]")
                    for line in result.stdout.strip().split("\n"):
                        self.console.print(f"    {line}")
        except Exception:
            pass
        self.console.print()

    def whois_lookup(self):
        self.console.print("\n  [bold cyan]Whois Lookup[/bold cyan]")
        target = Prompt.ask("  Enter domain or IP")
        self.console.print(f"\n  [yellow]Running whois for {target}...[/yellow]\n")
        try:
            result = subprocess.run(["whois", target], capture_output=True, text=True, timeout=15)
            lines = result.stdout.strip().split("\n")
            interesting = [l for l in lines if any(k in l.lower() for k in
                ["registrar","registrant","name server","creation","expiry","updated","country","email","org","status"])]
            if interesting:
                for line in interesting[:30]:
                    self.console.print(f"  {line}")
            else:
                self.console.print(result.stdout[:2000])
        except FileNotFoundError:
            self.console.print("  [red]whois not found. Install it: sudo apt install whois[/red]")
        except Exception as e:
            self.console.print(f"  [red]Error: {e}[/red]")
        self.console.print()

    def hash_tool(self):
        self.console.print("\n  [bold cyan]Hash Tool[/bold cyan]")
        text = Prompt.ask("  Enter text to hash")
        encoded = text.encode()
        t = Table(box=box.SIMPLE, show_header=True)
        t.add_column("Algorithm", style="bold cyan")
        t.add_column("Hash",      style="white")
        t.add_row("MD5",    hashlib.md5(encoded).hexdigest())
        t.add_row("SHA1",   hashlib.sha1(encoded).hexdigest())
        t.add_row("SHA256", hashlib.sha256(encoded).hexdigest())
        t.add_row("SHA512", hashlib.sha512(encoded).hexdigest())
        self.console.print(t)
        self.console.print()

    def encoder_decoder(self):
        self.console.print("\n  [bold cyan]Encoder / Decoder[/bold cyan]")
        ops = [
            ("1", "Base64 Encode"),
            ("2", "Base64 Decode"),
            ("3", "URL Encode"),
            ("4", "URL Decode"),
            ("5", "Hex Encode"),
            ("6", "Hex Decode"),
            ("7", "ROT13"),
        ]
        t = Table(show_header=False, box=box.SIMPLE, show_edge=False)
        t.add_column("Num", style="bold cyan", width=4)
        t.add_column("Op",  style="white")
        for o in ops:
            t.add_row(*o)
        self.console.print(t)

        choice = Prompt.ask("  [cyan]Select operation[/cyan]", default="1")
        text   = Prompt.ask("  Enter input text")

        result = ""
        try:
            if choice == "1":
                result = base64.b64encode(text.encode()).decode()
            elif choice == "2":
                result = base64.b64decode(text.encode()).decode(errors="replace")
            elif choice == "3":
                result = urllib.parse.quote(text)
            elif choice == "4":
                result = urllib.parse.unquote(text)
            elif choice == "5":
                result = text.encode().hex()
            elif choice == "6":
                result = bytes.fromhex(text).decode(errors="replace")
            elif choice == "7":
                result = text.translate(str.maketrans(
                    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
                    "NOPQRSTUVWXYZABCDEFGHIJKLMnopqrstuvwxyzabcdefghijklm"
                ))
        except Exception as e:
            result = f"Error: {e}"

        self.console.print(f"\n  [bold green]Result:[/bold green] {result}\n")

    def ip_info(self):
        self.console.print("\n  [bold cyan]IP Info[/bold cyan]")
        self.console.print("  [yellow]Fetching your public IP...[/yellow]")
        try:
            import requests
            r = requests.get("https://ipinfo.io/json", timeout=10)
            data = r.json()
            t = Table(box=box.SIMPLE, show_header=False)
            t.add_column("Field", style="bold cyan")
            t.add_column("Value", style="white")
            for key in ["ip","city","region","country","org","timezone"]:
                if key in data:
                    t.add_row(key.capitalize(), str(data[key]))
            self.console.print(t)
        except Exception as e:
            self.console.print(f"  [red]Error: {e}[/red]")
        self.console.print()

    def header_grabber(self):
        self.console.print("\n  [bold cyan]HTTP Header Grabber[/bold cyan]")
        url = Prompt.ask("  Enter URL (with https://)")
        self.console.print(f"\n  [yellow]Fetching headers for {url}...[/yellow]\n")
        try:
            import requests
            r = requests.head(url, timeout=10, allow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})
            t = Table(box=box.SIMPLE, show_header=True)
            t.add_column("Header", style="bold cyan")
            t.add_column("Value",  style="white")
            for k, v in r.headers.items():
                t.add_row(k, v)
            self.console.print(f"  [bold green]Status: {r.status_code}[/bold green]\n")
            self.console.print(t)
        except Exception as e:
            self.console.print(f"  [red]Error: {e}[/red]")
        self.console.print()

    def subdomain_scanner(self):
        self.console.print("\n  [bold cyan]Subdomain Scanner[/bold cyan]")
        domain = Prompt.ask("  Enter target domain (e.g. example.com)")
        self.console.print("  [dim]Using built-in mini wordlist. For full scans use gobuster/ffuf.[/dim]\n")

        wordlist = [
            "www","mail","ftp","admin","api","dev","test","staging","app","portal",
            "vpn","remote","cdn","static","assets","blog","shop","forum","support",
            "help","docs","beta","old","new","m","mobile","dashboard","panel","cpanel",
            "webmail","smtp","pop","imap","ns1","ns2","mx","cloud","git","jenkins",
            "jira","wiki","intranet","internal","corp","office","login","secure","auth"
        ]

        found = []
        self.console.print(f"  [yellow]Scanning {len(wordlist)} subdomains...[/yellow]\n")
        for sub in wordlist:
            fqdn = f"{sub}.{domain}"
            try:
                ip = socket.gethostbyname(fqdn)
                found.append((fqdn, ip))
                self.console.print(f"  [bold green][FOUND][/bold green] {fqdn:<40} {ip}")
            except Exception:
                pass

        if not found:
            self.console.print("  [dim]No subdomains resolved from the mini wordlist.[/dim]")
        else:
            self.console.print(f"\n  [bold green]Found {len(found)} subdomain(s).[/bold green]")
        self.console.print()

    def wordlist_generator(self):
        self.console.print("\n  [bold cyan]Wordlist Generator[/bold cyan]")
        self.console.print("  [dim]Generate a basic custom wordlist from keywords (for authorized testing only).[/dim]\n")
        keywords = Prompt.ask("  Enter keywords separated by commas")
        words    = [w.strip() for w in keywords.split(",") if w.strip()]
        years    = ["2022","2023","2024","2025","123","@123","!","#1","01"]
        suffixes = ["","1","12","123","!","@","#","_","2024","2025","01"]

        wordlist = set()
        for word in words:
            for s in suffixes:
                wordlist.add(word + s)
                wordlist.add(word.capitalize() + s)
                wordlist.add(word.upper() + s)
            for y in years:
                wordlist.add(word + y)
                wordlist.add(word.capitalize() + y)

        output_file = f"/tmp/hexmind_wordlist_{words[0] if words else 'custom'}.txt"
        with open(output_file, "w") as f:
            for w in sorted(wordlist):
                f.write(w + "\n")

        self.console.print(f"  [bold green]Generated {len(wordlist)} words.[/bold green]")
        self.console.print(f"  [bold cyan]Saved to:[/bold cyan] {output_file}\n")

    def cidr_calculator(self):
        self.console.print("\n  [bold cyan]CIDR Calculator[/bold cyan]")
        cidr = Prompt.ask("  Enter CIDR (e.g. 192.168.1.0/24)")
        try:
            import ipaddress
            network = ipaddress.ip_network(cidr, strict=False)
            t = Table(box=box.SIMPLE, show_header=False)
            t.add_column("Field",   style="bold cyan")
            t.add_column("Value",   style="white")
            t.add_row("Network",      str(network.network_address))
            t.add_row("Broadcast",    str(network.broadcast_address))
            t.add_row("Netmask",      str(network.netmask))
            t.add_row("Host bits",    str(network.max_prefixlen - network.prefixlen))
            t.add_row("Total hosts",  str(network.num_addresses))
            t.add_row("Usable hosts", str(max(0, network.num_addresses - 2)))
            t.add_row("First host",   str(list(network.hosts())[0]) if network.num_addresses > 2 else "N/A")
            t.add_row("Last host",    str(list(network.hosts())[-1]) if network.num_addresses > 2 else "N/A")
            self.console.print(t)
        except Exception as e:
            self.console.print(f"  [red]Error: {e}[/red]")
        self.console.print()
