#!/usr/bin/env python3

import os
import sys
import time
import subprocess


def detect_environment():
    """Auto-detect runtime environment.
    Returns one of: 'termux', 'wsl', 'linux', 'macos', 'windows'
    """
    if os.path.isdir("/data/data/com.termux"):
        return "termux"
    if sys.platform == "darwin":
        return "macos"
    if sys.platform == "win32":
        return "windows"
    # Check for WSL (Windows Subsystem for Linux)
    if sys.platform.startswith("linux"):
        try:
            with open("/proc/version", "r") as f:
                if "microsoft" in f.read().lower():
                    return "wsl"
        except Exception:
            pass
        return "linux"
    return "linux"


ENV = detect_environment()


def is_termux():
    return ENV == "termux"


def check_and_install_deps():
    env = ENV

    core_packages = [
        ("requests",      "requests"),
        ("rich",          "rich"),
        ("prompt_toolkit","prompt-toolkit"),
    ]

    provider_packages_standard = [
        ("anthropic",          "anthropic"),
        ("openai",             "openai"),
        ("google.generativeai","google-generativeai"),
    ]

    provider_packages_termux = [
        ("anthropic",          "anthropic", "anthropic==0.18.1"),
        ("openai",             "openai",    "openai==0.28.1"),
        ("google.generativeai","google-generativeai", "google-generativeai"),
    ]

    missing_core = []
    for module, pkg in core_packages:
        try:
            __import__(module)
        except ImportError:
            missing_core.append(pkg)

    missing_providers = []
    if env == "termux":
        for module, pkg, fallback in provider_packages_termux:
            try:
                __import__(module)
            except ImportError:
                missing_providers.append((pkg, fallback))
    else:
        for module, pkg in provider_packages_standard:
            try:
                __import__(module)
            except ImportError:
                missing_providers.append((pkg, pkg))

    if not missing_core and not missing_providers:
        return

    print("\033[96m\n  [*] Installing required packages...\033[0m")

    def install(package):
        if env == "termux":
            cmds = [
                [sys.executable, "-m", "pip", "install", package, "--quiet"],
            ]
        elif env == "windows":
            cmds = [
                [sys.executable, "-m", "pip", "install", package, "--quiet"],
            ]
        else:
            # Linux / macOS / WSL — try --break-system-packages first (for externally managed envs)
            cmds = [
                [sys.executable, "-m", "pip", "install", package, "--quiet", "--break-system-packages"],
                [sys.executable, "-m", "pip", "install", package, "--quiet"],
            ]
        for cmd in cmds:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                return True
        return False

    for pkg in missing_core:
        print(f"\033[93m  --> Installing {pkg}...\033[0m")
        ok = install(pkg)
        if not ok:
            print(f"\033[91m  [!] Failed to install {pkg}. Run manually: pip install {pkg}\033[0m")

    for pkg_latest, pkg_fallback in missing_providers:
        print(f"\033[93m  --> Installing {pkg_latest}...\033[0m")
        ok = install(pkg_latest)
        if not ok and pkg_fallback != pkg_latest:
            print(f"\033[93m  --> Trying fallback {pkg_fallback}...\033[0m")
            ok = install(pkg_fallback)
        if not ok:
            print(f"\033[93m  [~] {pkg_latest} unavailable — that AI provider won't work. Others still fine.\033[0m")

    print("\033[92m  [+] Setup complete.\033[0m\n")
    time.sleep(0.5)


check_and_install_deps()

from core.app import HexMind
import argparse

def run_cli():
    parser = argparse.ArgumentParser(description="HexMind AI Hacking Companion")
    parser.add_argument("--analyze-error", type=str, help="Analyze a failed shell command")
    parser.add_argument("--assist", type=str, help="Autocomplete a shell command")
    parser.add_argument("--ask", type=str, help="Ask a question directly from the CLI")
    args, unknown = parser.parse_known_args()
    
    if args.analyze_error or args.assist or args.ask:
        app = HexMind()
        app._init_engine()
        
        if args.analyze_error:
            prompt = f"I just typed this command and it failed / wasn't found: `{args.analyze_error}`. What is the correct command? Reply ONLY with the corrected command in a single line, nothing else."
            print(f"  \033[90m...\033[0m")
            try:
                ans = app.engine.chat(prompt).strip()
                ans = ans.replace("```bash","").replace("```sh","").replace("```shell","").replace("```","").strip()
                ans = ans.split("\n")[0] # ensure single line
                print(f"  \033[92mDid you mean:\033[0m \033[1m{ans}\033[0m")
            except Exception as e:
                print(f"  \033[91mHexMind Error:\033[0m {e}")
                
        elif args.assist:
            prompt = f"I am typing a terminal command and got stuck. Here is what I have so far: `{args.assist}`. Complete it. Reply ONLY with the missing end part of the command. Do not repeat what I already typed. No explanations."
            try:
                ans = app.engine.chat(prompt).strip()
                ans = ans.replace("```bash","").replace("```sh","").replace("```shell","").replace("```","").strip()
                ans = ans.split("\n")[0]
                print(ans, end="")
            except:
                pass
                
        elif args.ask:
            from rich.console import Console
            from rich.markdown import Markdown
            c = Console()
            c.print(f"\n  [bold cyan]HexMind 🧠[/bold cyan] [dim]Thinking...[/dim]")
            try:
                ans = app.engine.chat(args.ask)
                c.print()
                c.print(Markdown(ans, code_theme="monokai"))
                c.print()
            except Exception as e:
                c.print(f"  [red]Error:[/red] {e}")
                
        sys.exit(0)
        
    app = HexMind()
    app.run()

if __name__ == "__main__":
    run_cli()

