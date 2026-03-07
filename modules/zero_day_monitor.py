import threading
import time
import requests
import xml.etree.ElementTree as ET
from datetime import datetime

class ZeroDaySentinel:
    def __init__(self, engine, console, interval_minutes=15):
        self.engine = engine
        self.console = console
        self.interval = interval_minutes * 60
        self.seen_cves = set()
        self.running = False
        self._thread = None

    def start(self):
        self.running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        # self.console.print("  [dim]🛡️ Zero-Day Sentinel is watching for new exploits...[/dim]")

    def stop(self):
        self.running = False

    def _monitor_loop(self):
        while self.running:
            self._check_feeds()
            time.sleep(self.interval)

    def _check_feeds(self):
        # We use a mix of RSS feeds that are public and easy to parse
        feeds = [
            "https://nvd.nist.gov/feeds/xml/cve/misc/nvd-rss.xml",
            "https://github.com/advisories/feed"
        ]
        
        # Get active technologies from current workspace to match against
        # For V5, we would scrape this from the 'viz_engine' or recon files
        tech_keywords = ["nginx", "apache", "smb", "wordpress", "php", "javascript", "linux"]
        
        for url in feeds:
            try:
                r = requests.get(url, timeout=10)
                if r.status_code == 200:
                    root = ET.fromstring(r.content)
                    for item in root.findall(".//item"):
                        title = item.find("title").text
                        link = item.find("link").text
                        
                        if title not in self.seen_cves:
                            self.seen_cves.add(title)
                            
                            # Check for matches with our tech stack
                            for tech in tech_keywords:
                                if tech.lower() in title.lower():
                                    self._trigger_alert(title, link, tech)
            except Exception:
                pass

    def _trigger_alert(self, title, link, tech):
        from rich.panel import Panel
        alert_msg = f"[bold red]🚨 CRITICAL ZERO-DAY ALERT[/bold red]\n\n"
        alert_msg += f"Exploit found for target tech: [bold yellow]{tech.upper()}[/bold yellow]\n"
        alert_msg += f"Vulnerability: {title}\n"
        alert_msg += f"Source: {link}\n\n"
        alert_msg += "[cyan]Action: Do you want to try the PoC payload? (Type 'exploit now')[/cyan]"
        
        self.console.print("\n")
        self.console.print(Panel(alert_msg, border_style="red", box=None))
        self.console.print("\n")

def start_sentinel(engine, console):
    sentinel = ZeroDaySentinel(engine, console)
    sentinel.start()
    return sentinel
