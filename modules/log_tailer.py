import time
import threading
import os
from pathlib import Path

class LogSentinel:
    def __init__(self, log_path: str, engine, console):
        self.log_path = Path(log_path).expanduser()
        self.engine = engine
        self.console = console
        self._stop_event = threading.Event()
        self._thread = None
        self.buffer = []

    def start(self):
        if not self.log_path.exists():
            self.console.print(f"  [red]Log file not found: {self.log_path}[/red]")
            return
            
        self.console.print(f"  [bold green]🛡️ HexMind Log Sentinel started on {self.log_path}[/bold green]")
        self.console.print("  [dim]Monitoring for anomalies in the background...[/dim]\n")
        
        self._thread = threading.Thread(target=self._tail, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=1.0)
            self.console.print("  [dim]Log Sentinel stopped.[/dim]\n")

    def _tail(self):
        with open(self.log_path, 'r', errors='replace') as f:
            f.seek(0, 2) # Seek to end to avoid analyzing historical logs
            while not self._stop_event.is_set():
                line = f.readline()
                if not line:
                    time.sleep(1) # Wait for new logs
                    continue
                    
                line = line.strip()
                if line:
                    self.buffer.append(line)
                    # Batch analyze every 5 lines to save API/CPU calls
                    if len(self.buffer) >= 5:
                        self._analyze_buffer()
                        
    def _analyze_buffer(self):
        logs = "\n".join(self.buffer)
        self.buffer.clear()
        
        prompt = f"""Analyze these 5 recent server log lines. Are there any critical security threats, brute force attempts, SQL injections, or anomalous behaviors?
If EVERYTHING is normal, reply STRICTLY with 'SAFE'.
If there is a legitimate attack, reply STRICTLY with a 2-sentence alert starting with 'ALERT:'.

Logs:
{logs}"""
        
        # Use offline local AI if available to prevent API spam, fallback to cloud
        res = ""
        if hasattr(self.engine, 'offline_brain') and self.engine.offline_brain.local_llm_ready():
            res = self.engine.offline_brain.respond(prompt)
        else:
            try:
                res = self.engine.chat(prompt)
            except:
                pass
            
        if res and res.strip().startswith("ALERT:"):
            from rich.panel import Panel
            self.console.print()
            self.console.print(Panel(
                f"[bold red]{res.strip()}[/bold red]",
                title="[bold red on white] 🚨 SENTINEL INTRUSION ALERT [/bold red on white]",
                border_style="red"
            ))
            
# Singleton tracker
_active_sentinel = None

def start_sentinel(log_path: str, engine, console):
    global _active_sentinel
    if _active_sentinel:
        _active_sentinel.stop()
    _active_sentinel = LogSentinel(log_path, engine, console)
    _active_sentinel.start()
    
def stop_sentinel(console):
    global _active_sentinel
    if _active_sentinel:
        _active_sentinel.stop()
        _active_sentinel = None
    else:
        console.print("  [dim]No active Sentinel to stop.[/dim]\n")
