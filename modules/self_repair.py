import os
import sys
import traceback
from pathlib import Path
from rich.panel import Panel

class RepairAgent:
    def __init__(self, engine, console):
        self.engine = engine
        self.console = console

    def analyze_and_fix(self, error_msg: str, tb_str: str, file_path: str = None):
        """Analyzes a traceback and attempts to patch the file."""
        self.console.print(f"\n[bold red]🔧 HexMind Self-Repair initiated...[/bold red]")
        self.console.print(f"  [dim]Analyzing error: {error_msg}[/dim]")

        # If file_path is not provided, try to extract it from the traceback
        if not file_path:
            file_path = self._extract_file_from_tb(tb_str)

        if not file_path or not os.path.exists(file_path):
            self.console.print("  [yellow]⚠ Could not identify source file for repair.[/yellow]")
            return False

        # Read the source code
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()
        except Exception as e:
            self.console.print(f"  [red]Failed to read source file: {e}[/red]")
            return False

        # Build prompt for the AI
        prompt = f"""You are the HexMind Self-Repair Engine.
An error has occurred in the application. Your task is to provide a FIX.

FILE: {file_path}
ERROR: {error_msg}
TRACEBACK:
{tb_str}

SOURCE CODE:
{source_code}

INSTRUCTIONS:
1. Analyze why the error happened.
2. Provide a REPLACEMENT BLOCK for the buggy part of the code.
3. Your response MUST contain a code block in 'diff' or 'python' format that shows exactly what to change.
4. If you use Python, provide ONLY the replacement for the specific function or lines that were broken.

DO NOT output conversational text after the fix. Just the explanation and the code.
"""

        self.console.print("  [cyan]🧠 Querying AI for a solution...[/cyan]")
        try:
            # Use the engine's chat capability (could be local or cloud)
            # We bypass the complex chat loop and go straight to the LLM
            if hasattr(self.engine, 'offline_brain') and self.engine.offline_brain.is_offline():
                 # Use local LLM if active
                 response = self.engine.offline_brain.respond(prompt)
            else:
                 # Use cloud LLM
                 response = self.engine.chat(prompt)
            
            if not response:
                self.console.print("  [red]AI failed to provide a fix.[/red]")
                return False

            self.console.print("\n[bold green]✅ Fix proposed by AI:[/bold green]")
            self.console.print(Panel(response, border_style="green"))

            # Extract the fix and apply it
            return self._apply_proposed_fix(file_path, source_code, response)

        except Exception as e:
            self.console.print(f"  [red]Repair loop failed: {e}[/red]")
            return False

    def _extract_file_from_tb(self, tb_str: str):
        # Very simple regex to find the last file in the traceback that belongs to our project
        import re
        matches = re.findall(r'File "(.*?)", line \d+', tb_str)
        if matches:
            # Filter for files in the current working directory or hexmind subdirs
            cwd = os.getcwd().lower()
            for m in reversed(matches):
                if cwd in m.lower():
                    return m
        return None

    def _apply_proposed_fix(self, file_path, original_source, ai_response):
        """Extracts code blocks from AI response and attempts to patch the file."""
        import re
        # Find code blocks
        blocks = re.findall(r'```(?:python|diff)?\n(.*?)```', ai_response, re.DOTALL)
        if not blocks:
            self.console.print("  [yellow]⚠ No code blocks found in AI fix suggestion.[/yellow]")
            return False

        # Currently, we just try to find the best block to replace.
        # This is a bit risky for autonomous use, so we'll show it to the user.
        from rich.prompt import Confirm
        if not Confirm.ask("  [bold yellow]Apply this patch automatically?[/bold yellow]", default=False):
            return False

        # Attempt to apply the fix
        # In a real "Musk level" system, we'd use fuzzy matching or AST-based replacement.
        # For now, we'll try to find the function name or a unique substring.
        # A safer version would be to let the AGENT (me) do the final application,
        # but the request is for HexMind to be self-evolving.
        
        # Simplified 'Musk' version: Write a backup and overwrite if confirmed
        try:
            backup_path = file_path + ".bak"
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(original_source)
            
            # This is where the magic happens - actually modifying itself.
            # We'll use the first block as the fix.
            # LOGIC: If the block contains the WHOLE file, overwrite. 
            # If it's a snippet, we need smarter replacement.
            fix = blocks[0]
            
            # Heuristic: if it's > 50% of original size, it might be the whole file
            if len(fix) > len(original_source) * 0.7:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(fix)
                self.console.print(f"  [bold green]Applied full file patch to {os.path.basename(file_path)}[/bold green]")
                return True
            else:
                self.console.print("  [yellow]⚠ Snippet patch detected. Automated partial replacement is experimental.[/yellow]")
                # We'll just append it for now to show it worked, but real repair needs better logic
                # (In a real implementation, we'd use re.sub or AST)
                return False
                
        except Exception as e:
            self.console.print(f"  [red]Failed to apply patch: {e}[/red]")
            return False

def handle_exception(engine, console, e, tb_str):
    """Entry point for the repair agent."""
    agent = RepairAgent(engine, console)
    agent.analyze_and_fix(str(e), tb_str)
