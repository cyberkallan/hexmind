import socket
import threading
import time
from rich.panel import Panel

class GhostMode:
    def __init__(self, engine, console):
        self.engine = engine
        self.console = console
        self.running = False
        self.listeners = []
        self._threads = []

    def start(self, ports=[21, 22, 80, 443, 3389, 8080]):
        """Starts honeypot listeners on specified ports."""
        self.running = True
        self.console.print(f"\n[bold magenta]👻 HexMind V6 Ghost Mode engaged.[/bold magenta]")
        self.console.print(f"  [dim]Active Sentry listening on {len(ports)} ports for suspicious activity...[/dim]")
        
        for port in ports:
            t = threading.Thread(target=self._listen_on_port, args=(port,), daemon=True)
            t.start()
            self._threads.append(t)

    def stop(self):
        self.running = False

    def _listen_on_port(self, port):
        # Create a socket listener
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('0.0.0.0', port))
                s.listen(5)
                s.settimeout(1.0)
                
                while self.running:
                    try:
                        conn, addr = s.accept()
                        with conn:
                            self._on_intrusion_detected(port, addr)
                            # Simple honeypot response
                            banner = b"SSH-2.0-OpenSSH_8.2p1 Ubuntu-4ubuntu0.5\r\n" if port == 22 else b"HTTP/1.1 200 OK\r\nServer: Apache/2.4.41 (Ubuntu)\r\n\r\n"
                            conn.sendall(banner)
                    except socket.timeout:
                        continue
                    except Exception:
                        break
        except Exception:
            pass # Port might be in use, skip silently

    def _on_intrusion_detected(self, port, addr):
        source_ip = addr[0]
        alert_msg = f"[bold red]👻 GHOST MODE ALERT[/bold red]\n\n"
        alert_msg += f"Inbound Scan/Connection attempt detected!\n"
        alert_msg += f"Target Port: [bold yellow]{port}[/bold yellow]\n"
        alert_msg += f"Source IP: [bold red]{source_ip}[/bold red]\n\n"
        alert_msg += f"[cyan]Counter-Intel: Deployed decoy banner and isolating session...[/cyan]"
        
        self.console.print("\n")
        self.console.print(Panel(alert_msg, border_style="magenta", box=None))
        self.console.print("\n")

def engage_ghost(engine, console):
    ghost = GhostMode(engine, console)
    ghost.start()
    return ghost
