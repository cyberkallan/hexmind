import os
import sys
import json

class REAssistant:
    def __init__(self, engine, console):
        self.engine = engine
        self.console = console
        self.r2 = None

    def analyze_binary(self, file_path):
        """Analyzes a binary file using Radare2 and AI."""
        try:
            import r2pipe
        except ImportError:
            self.console.print("  [yellow]Installing r2pipe...[/yellow]")
            os.system(f"{sys.executable} -m pip install r2pipe --quiet")
            import r2pipe

        if not os.path.exists(file_path):
            self.console.print(f"  [red]File not found: {file_path}[/red]")
            return

        self.console.print(f"\n[bold green]🔬 Analyzing binary: {os.path.basename(file_path)}[/bold green]")
        
        try:
            # Open binary in headless mode
            r2 = r2pipe.open(file_path)
            r2.cmd('aa') # Analyze all
            
            # Extract basic info
            info = r2.cmdj('ij')
            functions = r2.cmdj('aflj')
            
            self.console.print(f"  [dim]Format: {info['bin']['format']} | Arch: {info['bin']['arch']} | Bits: {info['bin']['bits']}[/dim]")
            self.console.print(f"  [dim]Found {len(functions)} functions.[/dim]")

            # Pick a "main" or interesting function to decompile
            target_func = "main"
            for f in functions:
                if "main" in f['name'] or "entry" in f['name']:
                    target_func = f['name']
                    break
            
            self.console.print(f"  [cyan]🧠 Decompiling '{target_func}' for AI analysis...[/cyan]")
            disasm = r2.cmd(f'pdf @ {target_func}')
            
            prompt = f"""You are the HexMind V5 Reverse Engineering Assistant.
Analyze the following assembly disassembly of the function '{target_func}'.

DISASSEMBLY:
{disasm}

INSTRUCTIONS:
1. Explain the logical flow of this function in plain C-like pseudo-code.
2. Identify any potential vulnerabilities (Buffer Overflows, Insecure function calls like strcpy/gets, Hardcoded passwords, etc.).
3. Provide a dense summary for a security researcher.
"""

            if hasattr(self.engine, 'offline_brain') and self.engine.offline_brain.is_offline():
                response = self.engine.offline_brain.respond(prompt)
            else:
                response = self.engine.chat(prompt)

            self.console.print(f"\n[bold yellow]🛡️ Decompilation Report ({target_func}):[/bold yellow]")
            self.console.print(response)
            
            r2.quit()

        except Exception as e:
            self.console.print(f"  [red]Reverse engineering failed: {e}[/red]")

def run_re(engine, console):
    from rich.prompt import Prompt
    file_path = Prompt.ask("  [green]Enter path to binary file (.exe, .elf, .bin)[/green]").strip()
    if file_path:
        agent = REAssistant(engine, console)
        agent.analyze_binary(file_path)
