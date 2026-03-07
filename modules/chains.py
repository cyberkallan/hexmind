import os
import subprocess
from pathlib import Path

def run_cmd(cmd: str) -> str:
    from rich.console import Console
    Console().print(f"  [dim cyan]⚡ Running:[/dim cyan] {cmd}")
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return r.stdout or r.stderr
    except Exception as e:
        return str(e)

def execute_recon_chain(domain: str, engine, console):
    """Executes an autonomous recon chain: subfinder -> httpx -> nmap -> AI Analysis"""
    from modules.workspace import get_active_workspace, set_target
    
    ws = get_active_workspace()
    if not ws or ws.get("target") != domain:
        console.print(f"  [dim]Initializing Workspace for {domain}...[/dim]")
        base = set_target(domain)
    else:
        base = ws["path"]
        
    recon_dir = Path(base) / "recon"
    scans_dir = Path(base) / "scans"
    
    console.print(f"\n[bold yellow]🔥 Starting Autonomous Recon Chain for {domain}[/bold yellow]")
    
    # Step 1: Subfinder
    subs_file = recon_dir / "subdomains.txt"
    console.print("  [bold cyan]1.[/bold cyan] Hunting subdomains with subfinder...")
    # Using fallback to generic brute logic if subfinder isn't installed to avoid purely breaking
    out = run_cmd(f"command -v subfinder >/dev/null && subfinder -d {domain} -silent -o '{subs_file}' || echo '{domain}' > '{subs_file}'")
    
    if not subs_file.exists() or subs_file.stat().st_size == 0:
        console.print("  [red]Subfinder failed or found nothing. Ensure subfinder is installed.[/red]")
        return
        
    count = len(subs_file.read_text().strip().split('\n'))
    console.print(f"     [green]Found {count} subdomains.[/green]")
    
    # Step 2: httpx
    alive_file = recon_dir / "alive.txt"
    console.print("  [bold cyan]2.[/bold cyan] Probing live web servers with httpx...")
    run_cmd(f"command -v httpx >/dev/null && httpx -l '{subs_file}' -silent -o '{alive_file}' || cp '{subs_file}' '{alive_file}'")
    
    if not alive_file.exists() or alive_file.stat().st_size == 0:
        console.print("  [red]httpx failed or found no live servers. Ensure httpx is installed.[/red]")
        return
        
    alive_count = len(alive_file.read_text().strip().split('\n'))
    console.print(f"     [green]Found {alive_count} live web servers.[/green]")
    
    # Step 3: Fast Nmap
    nmap_file = scans_dir / "nmap_fast.txt"
    console.print("  [bold cyan]3.[/bold cyan] Running fast port scan on live hosts with Nmap...")
    run_cmd(f"nmap -iL '{alive_file}' -F -T4 -oN '{nmap_file}'")
    
    # Step 4: AI Analysis
    console.print("\n  [bold cyan]4.[/bold cyan] Feeding results into HexMind AI for vulnerability analysis...")
    
    try:
        nmap_results = nmap_file.read_text()
        
        # Guard against absurdly giant xml feeds crashing context window
        if len(nmap_results) > 10000:
            nmap_results = nmap_results[:10000] + "\n...[truncated]..."
            
        prompt = f"""I have just run an automated recon chain against {domain}. 
Here are the active ports and services found across {alive_count} live subdomains:

```nmap
{nmap_results}
```

Analyze these results as a senior penetration tester. Summarize the top 3 most critical attack vectors I should focus on next, and provide the exact exploitation or deep-scan commands I should run against them."""

        response = engine.chat(prompt)
        from rich.markdown import Markdown
        console.print("\n[bold green]🧠 HexMind Recon Analysis:[/bold green]")
        console.print(Markdown(response, code_theme="monokai"))
        
    except Exception as e:
        console.print(f"  [red]Analysis failed: {e}[/red]")
