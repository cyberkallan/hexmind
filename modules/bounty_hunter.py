"""
HexMind Autonomous Bug Bounty Hunter Daemon
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
A 24/7 background worker that continuously monitors a target domain,
discovers subdomains, checks for live web servers, and runs passive
vulnerability scans.
"""

import os
import time
import threading
import subprocess
import json
from pathlib import Path
from datetime import datetime

class BountyHunterDaemon:
    def __init__(self, engine, target_domain: str, interval_hours: float = 12):
        self.engine = engine
        self.target = target_domain
        self.interval = interval_hours * 3600
        self._running = False
        self._thread = None
        
        self.workspace_dir = Path.home() / ".hexmind" / "workspaces" / target_domain.replace("*.", "")
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        self.subs_file = self.workspace_dir / "subdomains.txt"
        self.live_file = self.workspace_dir / "live_hosts.txt"
        self.vuln_file = self.workspace_dir / "vulnerabilities.json"

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        
        if self.engine and self.engine.emit_callback:
            self.engine.emit_callback(f"\r\n\x1b[35m[Bounty Hunter] Started 24/7 monitoring on {self.target}\x1b[0m\r\n")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
            
    def _run_cmd(self, cmd: str) -> str:
        """Run a shell command safely."""
        try:
            return subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.DEVNULL)
        except Exception:
            return ""

    def _loop(self):
        while self._running:
            try:
                self._run_recon_cycle()
            except Exception as e:
                pass
            time.sleep(self.interval)

    def _run_recon_cycle(self):
        """Execute one full cycle of reconnaissance."""
        if self.engine and self.engine.emit_callback:
            self.engine.emit_callback(f"\r\n\x1b[36m[Bounty Hunter] Initiating recon cycle on {self.target}...\x1b[0m\r\n")

        # 1. Subdomain Enumeration
        new_subs = set()
        # Simulated or real subfinder. For safety/portability, we'll try API or tool.
        # Try crt.sh API (it's free and requires no tools)
        import urllib.request
        try:
            url = f"https://crt.sh/?q=%.{self.target.replace('*.', '')}&output=json"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=15) as response:
                data = json.loads(response.read().decode('utf-8'))
                for entry in data:
                    name = entry.get('name_value', '')
                    if '\n' in name:
                        new_subs.update(name.split('\n'))
                    else:
                        new_subs.add(name)
        except Exception:
            pass

        # Load old subs
        old_subs = set()
        if self.subs_file.exists():
            old_subs = set(self.subs_file.read_text().splitlines())
            
        # Find differences
        discovered = new_subs - old_subs
        if discovered:
            self.subs_file.write_text("\n".join(sorted(new_subs)))
            if self.engine and self.engine.emit_callback:
                self.engine.emit_callback(f"\x1b[32m[Bounty Hunter] Discovered {len(discovered)} NEW subdomains!\x1b[0m\r\n")
                
            # Alert the conversational AI buffer
            alert_msg = f"Bounty Hunter just found {len(discovered)} new subdomains for {self.target}."
            if hasattr(self.engine, 'memory'):
                self.engine.memory.save_memory(f"bounty_target_{self.target}", alert_msg)

        # 2. Port Scanning / Live Host Checking
        # (This would use httpx or nmap in a real environment. We simulate checking the new ones via requests)
        live_hosts = []
        if discovered:
            import requests
            for sub in list(discovered)[:10]:  # Limit to 10 for performance in background
                if not self._running: break
                sub = sub.strip()
                if sub.startswith("*"): continue
                try:
                    res = requests.get(f"http://{sub}", timeout=3, allow_redirects=False)
                    live_hosts.append(sub)
                except requests.exceptions.RequestException:
                    pass
                    
            if live_hosts:
                try:
                    with open(self.live_file, "a") as f:
                        for h in live_hosts: f.write(f"{h}\n")
                except: pass
                if self.engine and self.engine.emit_callback:
                    self.engine.emit_callback(f"\x1b[32m[Bounty Hunter] Verified {len(live_hosts)} new hosts are LIVE.\x1b[0m\r\n")

        # 3. Passive Vulnerability Scan
        # Here we would normally run `nuclei`. We will simulate a quick scan by analyzing HTTP headers of live hosts.
        vulns_found = []
        if live_hosts:
            for host in live_hosts:
                try:
                    res = requests.get(f"http://{host}", timeout=3)
                    if "X-Powered-By" in res.headers:
                        vulns_found.append({"host": host, "vuln": f"Information Disclosure: {res.headers['X-Powered-By']}"})
                    if ".git" in res.text or "Index of /.git" in res.text:
                        vulns_found.append({"host": host, "vuln": "CRITICAL: Exposed .git directory detected!"})
                except Exception:
                    pass
                    
        if vulns_found:
            # Load existing
            existing_vulns = []
            if self.vuln_file.exists():
                try: existing_vulns = json.loads(self.vuln_file.read_text())
                except: pass
            
            existing_vulns.extend(vulns_found)
            self.vuln_file.write_text(json.dumps(existing_vulns, indent=2))
            
            if self.engine and self.engine.emit_callback:
                self.engine.emit_callback(f"\r\n\x1b[31;1m[Bounty Hunter ALERT] Found {len(vulns_found)} potential vulnerabilities!\x1b[0m\r\n")

        if self.engine and self.engine.emit_callback:
            self.engine.emit_callback(f"\x1b[36m[Bounty Hunter] Cycle complete. Sleeping for {self.interval/3600} hours.\x1b[0m\r\n")

# Global tracking
_active_hunters = {}

def start_bounty_hunter(engine, target: str):
    if target in _active_hunters:
        return f"Bounty Hunter is already actively monitoring {target}."
    
    hunter = BountyHunterDaemon(engine, target)
    hunter.start()
    _active_hunters[target] = hunter
    return f"🚀 **Started Autonomous Bug Bounty Hunter**\n\nTarget: `{target}`\nMonitoring Interval: 12 Hours\nWorkspace: `{hunter.workspace_dir}`\n\nHexMind is now continuously scanning this target in the background."

def stop_bounty_hunter(target: str):
    if target in _active_hunters:
        _active_hunters[target].stop()
        del _active_hunters[target]
        return f"Stopped monitoring {target}."
    return f"No active hunter found for {target}."
