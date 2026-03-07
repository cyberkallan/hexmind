import os
import sys
import shutil
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm

console = Console()
CONFIG_DIR = Path.home() / ".hexmind"
SHELL_DIR = CONFIG_DIR / "shell"

ZSHRC = Path.home() / ".zshrc"
BASHRC = Path.home() / ".bashrc"

THEMES = {
    "1": {"name": "Cyberpunk", "color": "13", "zsh": r"[%{\e[38;5;13m%}{alias}%{\e[0m%}]-[%{\e[38;5;14m%}%~%{\e[0m%}] ❯ ", "bash": r"\[\e[38;5;13m\]{alias}\[\e[0m\]-\[\e[38;5;14m\]\w\[\e[0m\] ❯ "},
    "2": {"name": "Matrix Green", "color": "46", "zsh": r"[%{\e[38;5;46m%}{alias}%{\e[0m%}]-[%{\e[38;5;40m%}%~%{\e[0m%}] ❯ ", "bash": r"\[\e[38;5;46m\]{alias}\[\e[0m\]-\[\e[38;5;40m\]\w\[\e[0m\] ❯ "},
    "3": {"name": "Kali Red", "color": "196", "zsh": r"┌──([%{\e[38;5;196m%}{alias}㉿hexmind%{\e[0m%}])-[%{\e[38;5;255m%}%~%{\e[0m%}]\n└─$ ", "bash": r"┌──(\[\e[38;5;196m\]{alias}㉿hexmind\[\e[0m\])-\[\e[38;5;255m\]\w\[\e[0m\]\n└─$ "},
    "4": {"name": "Stealth", "color": "0", "zsh": r"~ ", "bash": r"~ "},
}

ZSH_HOOK = """# HexMind Zsh Companion Hook
export HEXMIND_ALIAS="{alias}"

hexmind_ask() {
    python3 "$HOME/hexmind/hexmind.py" --ask "$*"
}

command_not_found_handler() {
    echo -e "\\e[38;5;{color}m[HexMind]⚡\\e[0m Oops! Analyzing '\\e[1m$1\\e[0m'..."
    python3 "$HOME/hexmind/hexmind.py" --analyze-error "$*"
    return 127
}

hexmind_autocomplete() {
    local current_line=$BUFFER
    echo -e "\\n\\e[38;5;{color}m[HexMind]🧠\\e[0m Let me help..."
    local suggestion=$(python3 "$HOME/hexmind/hexmind.py" --assist "$current_line")
    BUFFER="$current_line $suggestion"
    CURSOR=${#BUFFER}
    zle reset-prompt
}
zle -N hexmind_autocomplete
bindkey '^H' hexmind_autocomplete

PROMPT="{zsh_prompt}"
"""

BASH_HOOK = """# HexMind Bash Companion Hook
export HEXMIND_ALIAS="{alias}"

hexmind_ask() {
    python3 "$HOME/hexmind/hexmind.py" --ask "$*"
}

command_not_found_handle() {
    echo -e "\\e[38;5;{color}m[HexMind]⚡\\e[0m Oops! Analyzing '\\e[1m$1\\e[0m'..."
    python3 "$HOME/hexmind/hexmind.py" --analyze-error "$*"
    return 127
}

PS1="{bash_prompt}"
"""

class ThemeManager:
    def __init__(self):
        SHELL_DIR.mkdir(parents=True, exist_ok=True)

    def menu(self):
        console.print(Panel(
            "[bold cyan]HexMind Terminal Theme & Companion[/bold cyan]\n\n"
            "This installs HexMind directly into your native terminal (Zsh/Bash).\n"
            "• [green]Auto-Corrections:[/green] Typo a command? HexMind catches it and suggests a fix.\n"
            "• [green]Ctrl+H Hotkey:[/green] Press Ctrl+H to autocomplete your terminal line with AI.\n"
            "• [green]Seamless CLI:[/green] Ask questions anywhere instantly.",
            title="[bold green] Install Theme [/bold green]",
            border_style="green", padding=(1,2)
        ))
        
        choice = Prompt.ask("\n  [yellow]Select Action[/yellow] (1. Install Theme | 2. Uninstall Theme | 3. Cancel)", choices=["1", "2", "3"], default="1")
        if choice == "1":
            self.install()
        elif choice == "2":
            self.uninstall()

    def install(self):
        console.print("\n  [bold cyan]1. Personalization[/bold cyan]")
        alias = Prompt.ask("  [bold]Hacker Alias[/bold]", default="Neo")
        age   = Prompt.ask("  [bold]Age[/bold] (optional)", default="24")
        
        console.print("\n  [bold yellow]2. Theme Selection[/bold yellow]")
        for k, v in THEMES.items():
            console.print(f"    [cyan]{k}.[/cyan] {v['name']}")
        
        t_choice = Prompt.ask("  [yellow]Theme choice[/yellow]", choices=["1","2","3","4"], default="1")
        selected = THEMES[t_choice]
        
        # Save profile
        import json
        config_path = CONFIG_DIR / "config.json"
        if config_path.exists():
            with open(config_path, "r") as f:
                conf = json.load(f)
            conf.setdefault("user", {})
            conf["user"]["name"] = alias
            conf["user"]["age"] = age
            with open(config_path, "w") as f:
                json.dump(conf, f, indent=4)
                
        # Write hooks - Using .replace() safely instead of .format() to avoid clashing with Bash/Zsh native curly braces
        zsh_content = ZSH_HOOK.replace("{alias}", alias)\
                              .replace("{color}", selected["color"])\
                              .replace("{zsh_prompt}", selected["zsh"].replace("{alias}", alias))
                              
        bash_content = BASH_HOOK.replace("{alias}", alias)\
                                .replace("{color}", selected["color"])\
                                .replace("{bash_prompt}", selected["bash"].replace("{alias}", alias))
        
        zsh_file = SHELL_DIR / "hexmind-hook.zsh"
        bash_file = SHELL_DIR / "hexmind-hook.bash"
        zsh_file.write_text(zsh_content, encoding="utf-8")
        bash_file.write_text(bash_content, encoding="utf-8")
        
        console.print("\n  [bold cyan]3. Injecting Hooks[/bold cyan]")
        
        # Inject ZSH
        if ZSHRC.exists():
            content = ZSHRC.read_text(encoding="utf-8")
            if "hexmind-hook" not in content:
                with open(ZSHRC, "a", encoding="utf-8") as f:
                    f.write(f"\n# Added by HexMind\nsource {zsh_file}\n")
                console.print("  [+] Patched ~/.zshrc")
            else:
                console.print("  [~] ~/.zshrc already patched")
        
        # Inject Bash
        if BASHRC.exists():
            content = BASHRC.read_text(encoding="utf-8")
            if "hexmind-hook" not in content:
                with open(BASHRC, "a", encoding="utf-8") as f:
                    f.write(f"\n# Added by HexMind\nsource {bash_file}\n")
                console.print("  [+] Patched ~/.bashrc")
            else:
                console.print("  [~] ~/.bashrc already patched")
                
        console.print("\n  [bold green]Installation Complete![/bold green] 🎉")
        console.print("  [dim]Type the `exit` command to close HexMind, then restart your terminal to see changes.[/dim]\n")

    def uninstall(self):
        console.print("\n  [bold red]Removing HexMind Shell Hooks...[/bold red]")
        
        for rc_file in [ZSHRC, BASHRC]:
            if rc_file.exists():
                lines = rc_file.read_text(encoding="utf-8").splitlines()
                new_lines = []
                skip = False
                changed = False
                for line in lines:
                    if line == "# Added by HexMind":
                        skip = True
                        changed = True
                        continue
                    if skip and "hexmind-hook" in line:
                        skip = False
                        continue
                    new_lines.append(line)
                
                if changed:
                    rc_file.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
                    console.print(f"  [-] Cleaned {rc_file.name}")
                    
        shutil.rmtree(SHELL_DIR, ignore_errors=True)
        console.print("  [-] Cleared shell hook scripts")
        console.print("  [bold green]Uninstall Complete.[/bold green] Restart your terminal.\n")
