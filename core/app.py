import os
import sys
import time
import json
import threading
import random
import re
import subprocess
import queue
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.markdown import Markdown
from rich.align import Align
from rich.table import Table
from rich.columns import Columns
from rich.rule import Rule
from rich.markup import escape
from rich import box
from prompt_toolkit import prompt as ptk_prompt
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.styles import Style as PtkStyle

from core.providers import ProviderManager
from core.config import ConfigManager
from core.chat import ChatEngine
from brain.skills import SkillsManager
from brain.memory import UserMemory
from brain.skills_lib import SkillsLibrary

console = Console()

CONFIG_DIR  = Path.home() / ".hexmind"
CONFIG_FILE = CONFIG_DIR / "config.json"

# ── BANNER ────────────────────────────────────────────────────────────────────
BANNER_LINES = [
    "  ██╗  ██╗███████╗██╗  ██╗███╗   ███╗██╗███╗   ██╗██████╗ ",
    "  ██║  ██║██╔════╝╚██╗██╔╝████╗ ████║██║████╗  ██║██╔══██╗",
    "  ███████║█████╗   ╚███╔╝ ██╔████╔██║██║██╔██╗ ██║██║  ██║",
    "  ██╔══██║██╔══╝   ██╔██╗ ██║╚██╔╝██║██║██║╚██╗██║██║  ██║",
    "  ██║  ██║███████╗██╔╝ ██╗██║ ╚═╝ ██║██║██║ ╚████║██████╔╝",
    "  ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝╚═╝╚═╝  ╚═══╝╚═════╝",
]

TIPS = [
    "💡 Type 'brain' to setup local AI (Ollama + 9 models to choose from)",
    "💡 Try: 'show me the directory' — HexMind runs commands for you",
    "💡 Use '!nmap -sV target' to run shell commands inline",
    "💡 Type 'mode' to switch between Hacker/Dev/OSINT/Tutor mode",
    "💡 OpenRouter has 300+ free models — get key at openrouter.ai/keys",
    "💡 Type 'tools' for built-in port scanner, DNS, hash tools and more",
    "💡 Type 'system' for restart, reset, and system controls",
    "💡 HexMind automatically frames your security queries for better AI answers",
    "💡 Type 'help' to see all commands",
]

SPINNER_FRAMES = ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]
THINKING_WORDS = ["Thinking", "Reasoning", "Processing", "Analyzing"]
SEARCH_WORDS   = ["Searching", "Looking up", "Scanning", "Researching"]
RUN_WORDS      = ["Running", "Executing", "Computing", "Processing"]


def clear():
    os.system("clear" if os.name != "nt" else "cls")


def spinner_anim(stop_event, label="Thinking"):
    frames = SPINNER_FRAMES
    i = 0
    labels = THINKING_WORDS if label == "Thinking" else (RUN_WORDS if label == "Running" else SEARCH_WORDS)
    while not stop_event.is_set():
        lbl = labels[i % len(labels)]
        f   = frames[i % len(frames)]
        sys.stdout.write(f"\r  \033[96m{f}\033[0m \033[93m{lbl}...\033[0m        ")
        sys.stdout.flush()
        time.sleep(0.08)
        i += 1
    sys.stdout.write("\r" + " " * 60 + "\r")
    sys.stdout.flush()


def show_banner():
    console.print()
    for i, line in enumerate(BANNER_LINES):
        colors = ["bold bright_cyan", "bold cyan", "bold cyan", "bold cyan", "bold cyan", "bold blue"]
        console.print(line, style=colors[i])
    console.print()
    _A = bytes.fromhex('62792041726a756e2054204d').decode('utf-8')
    _G = bytes.fromhex('6769746875622e636f6d2f63796265726b616c6c616e').decode('utf-8')
    console.print(Align.center(Text("  AI-Powered Hacker Terminal Assistant  v2.5", style="bold white")))
    console.print(Align.center(Text(f"  {_A}  ·  {_G}", style="dim cyan")))
    console.print(Align.center(Text(f"  {random.choice(TIPS)}", style="italic dim green")))
    console.print()


def status_bar(provider_name: str, model_name: str, mode: str, offline: bool, local_ai: bool):
    """Render the status line under the chat header."""
    if offline and local_ai:
        src = "[bold yellow]🧠 Local AI[/bold yellow]"
    elif offline:
        src = "[bold red]⚡ Offline Brain[/bold red]"
    else:
        src = f"[bold green]☁ {provider_name}[/bold green]"

    model_tag = f"[dim]({model_name})[/dim]" if model_name else ""
    mode_tag  = f"[cyan]{mode}[/cyan]"
    console.print(f"  {src} {model_tag}  ·  {mode_tag}  ·  [dim]help · brain · tools · mode · settings · !cmd[/dim]")
    console.print(Rule(style="dim blue"))


class HexMind:
    def __init__(self):
        self.cfg_mgr     = ConfigManager(CONFIG_DIR, CONFIG_FILE)
        self.config      = self.cfg_mgr.load()
        self.prov_mgr    = ProviderManager()
        self.engine      = None
        self.user        = {}
        self.history     = InMemoryHistory()
        self.cmd_queue   = queue.Queue()
        self.session_log = []
        self._last_activity = time.time()
        self.voice_commander = None
        self._start_heartbeat()
        self._start_queue_watcher()

    def _start_queue_watcher(self):
        def watch():
            while True:
                try:
                    cmd = self.cmd_queue.get()
                    if cmd:
                        self._handle_command(cmd, source="WEB")
                except:
                    pass
                time.sleep(0.5)
        threading.Thread(target=watch, daemon=True).start()

    # ── Run ───────────────────────────────────────────────────────────────────
    def run(self):
        clear()
        show_banner()

        if not self.config.get("setup_done"):
            self._first_time_setup()
        else:
            self._welcome_back()
            self._init_engine()

        # Start Telegram Bot if token exists
        token = self.config.get("telegram_token")
        if token and self.engine:
            try:
                from modules.telegram_bot import start_telegram_daemon
                start_telegram_daemon(self.engine, token, None)
            except Exception as e:
                console.print(f"  [red]Failed to start Telegram Bot: {e}[/red]\n")

        # Start V8 Knowledge Ingestor
        try:
            from modules.knowledge_ingestor import start_ingestor
            start_ingestor(console)
        except Exception:
            pass

        self._chat_loop()

    # ── Welcome back ──────────────────────────────────────────────────────────
    def _welcome_back(self):
        self.user = self.config.get("user", {})
        name = self.user.get("name", "Hacker")
        prov = self.config.get("provider", {})
        greets = [
            f"[bold cyan]Welcome back, {name}![/bold cyan] Ready to hack? 🔥",
            f"[bold cyan]{name}[/bold cyan] online. HexMind loaded. Let's go.",
            f"Hey [bold cyan]{name}[/bold cyan]! AI core ready. What are we doing today?",
            f"Back again, [bold cyan]{name}[/bold cyan]? Good. Let's get to work 💻",
        ]
        console.print(Panel(
            random.choice(greets),
            border_style="cyan", title="[bold green] HexMind [/bold green]",
            padding=(0, 2)
        ))
        console.print()

    # ── First time setup ──────────────────────────────────────────────────────
    def _first_time_setup(self):
        console.print(Panel(
            "[bold cyan]Welcome to HexMind v2.0![/bold cyan]\n\n"
            "Your AI-powered terminal hacking companion.\n"
            "Quick setup — takes about 60 seconds.",
            title="[bold green] First Time Setup [/bold green]",
            border_style="green", padding=(1, 2)
        ))
        console.print()
        time.sleep(0.3)

        from rich.prompt import Prompt

        name = Prompt.ask("  [bold cyan]Your name[/bold cyan]").strip() or "Hacker"
        console.print(f"  [green]Nice to meet you, {name}![/green]\n")

        skill_opts = [
            ("1","Ethical Hacking & Pentesting"),("2","Bug Bounty Hunting"),
            ("3","CTF Player"),("4","Developer / Coder"),
            ("5","Cybersecurity Student"),("6","OSINT & Recon"),
            ("7","Network Security"),("8","Just Exploring"),
        ]
        t = Table(show_header=False, box=box.SIMPLE, show_edge=False)
        t.add_column("", style="bold cyan", width=4)
        t.add_column("", style="white")
        for n, s in skill_opts: t.add_row(f"[{n}]", s)
        console.print("  [bold white]Primary focus:[/bold white]"); console.print(t)
        sc = Prompt.ask("  [cyan]Number[/cyan]", default="1")
        skill = dict(skill_opts).get(sc.strip(), "Ethical Hacking & Pentesting")

        os_opts = [
            ("1","Kali Linux"),("2","Parrot OS"),("3","Ubuntu/Debian"),
            ("4","Termux (Android)"),("5","macOS"),("6","WSL / Windows"),("7","Other"),
        ]
        o = Table(show_header=False, box=box.SIMPLE, show_edge=False)
        o.add_column("", style="bold cyan", width=4)
        o.add_column("", style="white")
        for n, s in os_opts: o.add_row(f"[{n}]", s)
        console.print("\n  [bold white]Your main platform:[/bold white]"); console.print(o)
        oc  = Prompt.ask("  [cyan]Number[/cyan]", default="1")
        uos = dict(os_opts).get(oc.strip(), "Kali Linux")

        exp = Prompt.ask(
            "\n  [bold cyan]Experience level?[/bold cyan] [dim](beginner/intermediate/advanced)[/dim]",
            default="intermediate"
        ).lower().strip()
        if exp not in ("beginner","intermediate","advanced"):
            exp = "intermediate"

        from rich.prompt import Confirm
        auto_learn = Confirm.ask(
            "\n  [bold cyan]Enable Background Auto Self-Learning?[/bold cyan]\n"
            "  [dim]HexMind will periodically research advanced infosec concepts in the background to grow its intelligence.[/dim]",
            default=True
        )

        self.user = {"name": name, "skill": skill, "os": uos, "experience": exp, "auto_learn": auto_learn}
        console.print(f"\n  [green]Profile saved![/green]\n")

        self._setup_provider_menu()

        self.config.update({"setup_done": True, "user": self.user, "mode": "Hacker Mode"})
        self.cfg_mgr.save(self.config)

        console.print(f"\n  [bold green]All set, {name}! Let's hack. 🔥[/bold green]\n")
        time.sleep(0.4)
        self._init_engine()

    # ── Provider setup ────────────────────────────────────────────────────────
    def _setup_provider_menu(self):
        from rich.prompt import Prompt
        while True:
            rows = [
                ("1","OpenRouter",        "Free options",  "300+ models · recommended · free key at openrouter.ai/keys"),
                ("2","Anthropic (Claude)","Paid",          "Claude 3.5 Sonnet · very smart"),
                ("3","Google Gemini",     "Free tier",     "gemini-1.5-flash · free"),
                ("4","OpenAI (GPT)",      "Paid",          "GPT-4o, GPT-4o Mini"),
                ("5","DeepSeek",          "Free / cheap",  "deepseek-chat, deepseek-coder"),
                ("6","Telegram Bot",      "Integration",   "Setup Telegram bot for remote access"),
                ("7","Hard Reset",        "Danger",        "Uninstall HexMind & wipe all data"),
                ("8","Back",              "Chat",          "Return to main chat"),
            ]
            t = Table(title="[bold cyan]HexMind Settings[/bold cyan]",
                      box=box.ROUNDED, border_style="cyan")
            t.add_column("#",  style="bold cyan", width=4)
            t.add_column("Setting", style="bold white")
            t.add_column("Category", style="yellow")
            t.add_column("Notes",    style="dim white")
            for r in rows: t.add_row(*r)
            console.print(t)
            choice = Prompt.ask("\n  [bold cyan]Pick setting (1-8)[/bold cyan]", default="8").strip()
            
            if choice == "8":
                break
            elif choice in ["1", "2", "3", "4", "5"]:
                data = self.prov_mgr.setup_provider(choice, console)
                if data:
                    self.config["provider"] = data
                    self.cfg_mgr.save(self.config)
            elif choice == "6":
                from rich.prompt import Prompt as RP
                token = RP.ask("  [cyan]Enter Telegram Bot Token (or press Enter to disable)[/cyan]").strip()
                self.config["telegram_token"] = token if token else None
                self.cfg_mgr.save(self.config)
                if token:
                    console.print("  [green]Telegram Bot Token saved. Restart HexMind to apply.[/green]\n")
                    time.sleep(1)
                else:
                    console.print("  [yellow]Telegram Bot disabled.[/yellow]\n")
                    time.sleep(1)
            elif choice == "7":
                from rich.prompt import Confirm
                if Confirm.ask("\n  [bold red]WARNING: This will completely wipe all your configs, memory, and downloaded local models from ~/.hexmind. Are you sure?[/bold red]"):
                    import shutil
                    from pathlib import Path
                    mdir = Path.home() / ".hexmind"
                    if mdir.exists():
                        shutil.rmtree(mdir, ignore_errors=True)
                    console.print("\n  [green]HexMind successfully uninstalled/hard reset.[/green]")
                    sys.exit(0)
            
            console.print("[dim]Press Enter to continue...[/dim]")
            input()
            clear()
            show_banner()

    def _init_engine(self):
        provider = self.config.get("provider", {})
        self.user = self.config.get("user", self.user)
        mode      = self.config.get("mode", "Hacker Mode")
        self.engine = ChatEngine(provider, self.user)
        self.engine.set_mode(mode)

    def _print_status_bar(self):
        prov = self.config.get("provider", {})
        mode = self.config.get("mode", "Hacker Mode")
        offline = self.engine and self.engine.is_offline()
        local_ai = offline and self.engine and self.engine.offline_brain.local_llm_ready()
        
        provider_name = prov.get("name", "?")
        
        if local_ai:
            model_name = self.engine.offline_brain.get_local_llm().model_name()
        elif offline:
            model_name = "Ruleset"
        else:
            model_name = prov.get("model_name", "Auto")
            
        status_bar(provider_name, model_name, mode, offline, local_ai)
        console.print()

    # ── Chat loop ─────────────────────────────────────────────────────────────
    def _chat_loop(self):
        prov = self.config.get("provider", {})
        mode = self.config.get("mode", "Hacker Mode")

        console.print()
        self._print_status_bar()

        # Start Self-Learning Daemon if enabled
        if self.user.get("auto_learn", False):
            try:
                from modules.self_learning import start_daemon
                start_daemon(self.engine, console)
            except Exception:
                pass

        # Start V5 Zero-Day Sentinel if enabled
        try:
            from modules.zero_day_monitor import start_sentinel
            self.sentinel = start_sentinel(self.engine, console)
        except Exception:
            pass

        pt_style = PtkStyle.from_dict({
            "":       "#00e5ff",
            "prompt": "bold #00ff88",
        })

        while True:
            self._last_activity = time.time()
            # Build prompt string showing offline status
            offline    = self.engine and self.engine.is_offline()
            local_ai   = offline and self.engine and self.engine.offline_brain.local_llm_ready()
            mode_now   = self.config.get("mode","Hacker Mode")

            if local_ai:
                prompt_str = "  🧠 You ❯ "
            elif offline:
                prompt_str = "  ⚡ You ❯ "
            else:
                prompt_str = "  You ❯ "

            try:
                user_input = ptk_prompt(
                    prompt_str,
                    history       = self.history,
                    auto_suggest  = AutoSuggestFromHistory(),
                    style         = pt_style
                ).strip()
                self._last_activity = time.time()
            except (KeyboardInterrupt, EOFError):
                self._exit()
                break

            if not user_input:
                continue

            self._handle_command(user_input, source="TERM")

    def _handle_command(self, user_input, source="TERM"):
        cmd = user_input.lower().strip()
        
        def out(msg, style=None):
            if source == "TERM":
                if style: console.print(f"  {msg}", style=style)
                else: console.print(f"  {msg}")
            try:
                from core.web_portal import HEXMIND_STATE
                HEXMIND_STATE["logs"].append(str(msg).replace("[","").replace("]",""))
            except:
                pass

        if cmd in ("exit","quit","q","bye") and source == "TERM":
            self._exit()
            return

        if cmd == "help":
            self._show_help()
        elif cmd == "clear":
            if source == "TERM": clear(); show_banner()
            self._print_status_bar()
        elif cmd == "about":
            self._show_about()
        elif cmd == "settings":
            if source == "TERM":
                self._setup_provider_menu()
                self._init_engine()
                clear(); show_banner()
                self._print_status_bar()
            else:
                out("Settings menu only available via terminal.")
        elif cmd in ("skills", "skill"):
            self.skills_lib.show_menu(console if source=="TERM" else None)
        elif cmd in ("memory", "stats", "learn"):
            self._show_memory()
        elif cmd == "brain":
            if source == "TERM":
                self._setup_local_brain()
                clear(); show_banner()
                self._print_status_bar()
            else:
                out("Brain setup only available via terminal.")
        elif cmd == "tools":
            try:
                from modules.tools import ToolsMenu
                ToolsMenu(console if source=="TERM" else None).run()
            except ImportError:
                out("Tools module not found.", "red")
        elif cmd == "save":
            self._save_session()
        elif cmd == "history":
            self._show_history()
        elif cmd == "mode":
            self._switch_mode()
        elif cmd == "profile":
            self._show_profile()
        elif cmd == "status":
            self._show_status()
        elif cmd == "system":
            self._system_controls()
        elif cmd in ("diagnostics", "diag"):
            self._show_diagnostics()
        elif cmd == "theme":
            try:
                from modules.theme_manager import ThemeManager
                ThemeManager().menu()
            except ImportError:
                out("Theme manager module not found.", "red")
        elif cmd in ("portal", "dashboard"):
            try:
                from core.web_portal import start_command_center
                start_command_center(self, port=8888, console=console)
            except Exception as e:
                out(f"Command Center error: {e}", "red")
        elif cmd == "agent":
            if self.engine.mode == "Agent Mode":
                self.engine.set_mode("Hacker Mode")
                out("Agent Mode deactivated. Returning to Hacker Mode.", "yellow")
            else:
                self.engine.set_mode("Agent Mode")
                out("Agent Mode ACTIVATED. (ReAct Framework Online).", "bold green")
            self._print_status_bar()
        elif user_input.lower().startswith("persona "):
            p_name = user_input[8:].strip()
            try:
                from modules.knowledge_ingestor import get_persona_prompt
                p_text = get_persona_prompt(p_name)
                if p_text:
                    # Instruct the engine to adopt the persona contextually
                    self.engine.history.append({"role": "system", "content": f"ADOPT PERSONA: {p_name.upper()}\n{p_text}"})
                    out(f"Successfully assumed persona: {p_name}", "bold green")
                else:
                    out(f"Persona '{p_name}' not found. Ensure f/awesome-chatgpt-prompts is loaded.", "yellow")
            except Exception as e:
                out(f"Persona error: {e}", "red")
        elif cmd == "osint":
            try:
                from modules.bio_osint import run_profile
                run_profile(self.engine, console if source=="TERM" else None)
            except ImportError:
                out("Bio-OSINT module not found.", "red")
        elif cmd == "voice":
            if self.voice_commander and self.voice_commander.running:
                self.voice_commander.stop()
            else:
                try:
                    from modules.voice_command import start_voice
                    self.voice_commander = start_voice(self.engine, console if source=="TERM" else None)
                except ImportError:
                    out("Voice Control module not found.", "red")
        elif cmd == "autopwn":
            try:
                from modules.autopwn import run_msf
                run_msf(self.engine, console if source=="TERM" else None)
            except ImportError:
                out("Auto-Pwn module not found.", "red")
        elif cmd == "mutate":
            try:
                from modules.waf_mutator import run_mutator
                run_mutator(self.engine, console if source=="TERM" else None)
            except ImportError:
                out("Mutator module not found.", "red")
        elif cmd == "re":
            try:
                from modules.re_assistant import run_re
                run_re(self.engine, console if source=="TERM" else None)
            except ImportError:
                out("RE Assistant module not found.", "red")
        elif cmd == "optimize":
            try:
                from modules.self_optimizer import run_optimization
                run_optimization(self, console if source=="TERM" else None)
            except ImportError:
                out("Self-Optimizer module not found.", "red")
        elif cmd == "ghost":
            try:
                from modules.ghost_mode import engage_ghost
                self.ghost_mode = engage_ghost(self.engine, console if source=="TERM" else None)
            except ImportError:
                out("Ghost Mode module not found.", "red")
        elif cmd == "verify":
            try:
                from modules.symbolic_engine import run_symbolic
                run_symbolic(self.engine, console if source=="TERM" else None)
            except ImportError:
                out("Neuro-Symbolic module not found.", "red")
        elif cmd.startswith("target"):
            parts = cmd.split(maxsplit=1)
            if len(parts) > 1:
                from modules.workspace import set_target
                target_path = set_target(parts[1].strip())
                out(f"✓ Workspace '{parts[1].strip()}' initialized at {target_path}", "bold green")
            else:
                out("Usage: target <domain|name>", "red")
        elif cmd == "untarget":
            from modules.workspace import clear_workspace
            clear_workspace()
            out("Workspace cleared.", "green")
        elif cmd.startswith("start-recon"):
            parts = cmd.split(maxsplit=1)
            if len(parts) > 1:
                try:
                    from modules.chains import execute_recon_chain
                    execute_recon_chain(parts[1].strip(), self.engine, console if source=="TERM" else None)
                except ImportError:
                    out("Chains module not found.", "red")
            else:
                out("Usage: start-recon <domain>", "red")
        elif cmd.startswith("see"):
            parts = cmd.split(maxsplit=1)
            if len(parts) > 1:
                try:
                    from modules.vision import analyze_image
                    out(f"👁️ HexMind Vision is analyzing {parts[1].strip()}...", "dim cyan")
                    res = analyze_image(parts[1].strip(), self.config.get("provider", {}))
                    out("\n👁️ Terminal Vision Analysis:", "bold magenta")
                    out(res)
                except ImportError:
                    out("Vision module not found.", "red")
            else:
                out("Usage: see <image.png|jpg>", "red")
        elif cmd.startswith("crawl"):
            parts = cmd.split(maxsplit=1)
            if len(parts) > 1:
                try:
                    from modules.crawler import generate_exploit_payloads
                    generate_exploit_payloads(parts[1].strip(), self.engine, console if source=="TERM" else None)
                except ImportError:
                    out("Crawler module not found.", "red")
            else:
                out("Usage: crawl <http://target.com>", "red")
        elif cmd.startswith("watch"):
            parts = cmd.split(maxsplit=1)
            if len(parts) > 1:
                try:
                    from modules.log_tailer import start_sentinel
                    start_sentinel(parts[1].strip(), self.engine, console if source=="TERM" else None)
                except ImportError:
                    out("Log Tailer module not found.", "red")
            else:
                out("Usage: watch <path/to/log>", "red")
        elif cmd == "unwatch":
            try:
                from modules.log_tailer import stop_sentinel
                stop_sentinel(console if source=="TERM" else None)
            except ImportError:
                pass
        elif cmd.startswith("agent"):
            parts = cmd.split(maxsplit=1)
            if len(parts) > 1:
                try:
                    from modules.agent_brain import run_agent
                    run_agent(parts[1].strip(), self.engine, console if source=="TERM" else None)
                except ImportError:
                    out("Agent module not found.", "red")
            else:
                out("Usage: agent <your complex objective>", "red")
        elif cmd.startswith("!"):
            self._run_shell(cmd[1:].strip())
        else:
            intent_keywords = ["switch model", "change model", "change ai", "switch ai"]
            if any(kw in cmd for kw in intent_keywords) and source == "TERM":
                from rich.prompt import Confirm
                if Confirm.ask("\n  [bold cyan]Do you want to change the current AI provider/model?[/bold cyan]", default=True):
                    self._setup_provider_menu()
                    self._init_engine()
                    clear(); show_banner()
                    self._print_status_bar()
                    return
            
            # For AI chat, we want to capture the response for the web too
            if source == "TERM":
                self._ask(user_input)
            else:
                res = self.engine.chat(user_input)
                out(res)

    # ── AI Diagnostics ────────────────────────────────────────────────────────
    def _show_diagnostics(self):
        latency = getattr(self.engine, "last_latency", 0.0)
        tps     = getattr(self.engine, "last_tokens_sec", 0.0)
        
        offline  = self.engine and self.engine.is_offline()
        local_ai = offline and (self.engine and self.engine.offline_brain.local_llm_ready())
        
        if local_ai:
            backend = self.engine.offline_brain.get_local_llm().backend_name()
            model   = self.engine.offline_brain.get_local_llm().model_name()
            ping_str = "[dim]N/A (Offline)[/dim]"
            if backend == "ollama":
                ram = "2GB - 8GB"
            else:
                ram = "300MB"
        elif offline:
            backend = "Offline Knowledge Base"
            model   = "HexMind Ruleset"
            ping_str = "[dim]N/A (Offline)[/dim]"
            ram = "[dim]< 50MB[/dim]"
        else:
            backend = self.config.get("provider", {}).get("name", "Cloud API")
            model   = self.config.get("provider", {}).get("model_name", "Auto")
            ping_str = f"{latency*1000:.1f} ms" if latency > 0 else "N/A"
            ram = "[dim]Cloud Hosted[/dim]"
            
        t = Table(title="[bold cyan]HexMind AI Diagnostics[/bold cyan]", box=box.ROUNDED, border_style="cyan")
        t.add_column("Metric", style="bold yellow")
        t.add_column("Value", style="white")
        
        t.add_row("Active Engine", f"{backend}")
        t.add_row("Model", f"{model}")
        t.add_row("Response Latency", f"{latency:.2f} seconds")
        t.add_row("Token Speed", f"{tps:.1f} tokens/sec")
        if not local_ai and not offline:
            t.add_row("API Ping", ping_str)
        if local_ai:
            t.add_row("Est. RAM Footprint", ram)
            
        console.print()
        console.print(t)
        console.print("  [dim]Speeds are calculated from your last interaction.[/dim]\n")

    # ── Ask AI ────────────────────────────────────────────────────────────────
    def _ask(self, user_input: str):
        if not self.engine:
            console.print("  [red]No AI engine. Type 'settings'.[/red]\n"); return

        self.session_log.append({
            "role":"user","content":user_input,
            "time":datetime.now().strftime("%H:%M:%S")
        })

        # Determine animation label
        cmd, _ = self.engine.offline_brain.detect_agent_command(user_input)
        if cmd:
            anim = "Running"
        elif any(w in user_input.lower() for w in ["search","find","lookup","who is","what is"]):
            anim = "Searching"
        else:
            anim = "Thinking"

        stop_ev = threading.Event()
        t = threading.Thread(target=spinner_anim, args=(stop_ev, anim), daemon=True)
        t.start()

        try:
            response = self.engine.chat(user_input)
        except Exception as e:
            stop_ev.set(); t.join()
            err = str(e)
            console.print(f"\n  [bold red]⚠ Error:[/bold red] {escape(err)}")
            
            # V4 SELF-REPAIR TRIGGER
            try:
                import traceback
                from modules.self_repair import handle_exception
                handle_exception(self, console, e, traceback.format_exc())
            except Exception as repair_err:
                console.print(f"  [dim red]Self-repair module failed: {repair_err}[/dim red]")

            if "404" in err or "model" in err.lower():
                console.print("  [yellow]→ Type 'settings' → pick OpenRouter → select Auto Router (option 1)[/yellow]")
            elif "401" in err or "key" in err.lower():
                console.print("  [yellow]→ Type 'settings' and re-enter your API key[/yellow]")
            console.print()
            return

        stop_ev.set(); t.join()

        self.session_log.append({
            "role":"assistant","content":response,
            "time":datetime.now().strftime("%H:%M:%S")
        })

        offline  = self.engine.is_offline()
        local_ai = offline and self.engine.offline_brain.local_llm_ready()
        username = getattr(self, "user", {}).get("name", "Hacker")

        console.print()
        if local_ai:
            console.print(f"[bold yellow]HexMind 🧠 Local AI[/bold yellow] • [dim]for {username}[/dim]\n")
        elif offline:
            console.print(f"[bold red]HexMind ⚡ Offline AI[/bold red] • [dim]for {username}[/dim]\n")
        else:
            console.print(f"[bold cyan]HexMind ☁️ Cloud AI[/bold cyan] • [dim]for {username}[/dim]\n")

        console.print(Markdown(response, code_theme="monokai"))
        console.print("\n" + "─"*60 + "\n")

        # Auto-detect executable commands in AI response and offer to run
        self._offer_command_execution(response)

    # ── Local brain setup ─────────────────────────────────────────────────────
    def _show_memory(self):
        if not self.engine:
            console.print("  [dim]No session yet.[/dim]\n"); return
        stats = self.engine.memory.get_stats()
        tbl = Table(title="[bold cyan]HexMind Memory & Learning[/bold cyan]",
                    box=box.ROUNDED, border_style="cyan")
        tbl.add_column("Metric", style="bold cyan")
        tbl.add_column("Value",  style="white")
        tbl.add_row("Total Sessions",    str(stats["sessions"]))
        tbl.add_row("Total Messages",    str(stats["messages"]))
        tbl.add_row("First Seen",        stats["first_seen"][:10] if stats["first_seen"] != "?" else "?")
        tbl.add_row("Last Seen",         stats["last_seen"][:10] if stats["last_seen"] != "?" else "?")
        if stats["top_topics"]:
            topics_str = ", ".join(f"{tp}({cnt})" for tp, cnt in stats["top_topics"])
            tbl.add_row("Top Interests",  topics_str)
        if stats["tools_used"]:
            tools_str = ", ".join(f"{k}({v})" for k, v in sorted(stats["tools_used"].items(), key=lambda x: -x[1])[:5])
            tbl.add_row("Tools Used",     tools_str)
        if stats["commands_run"]:
            cmds_str = ", ".join(f"{k}({v})" for k, v in sorted(stats["commands_run"].items(), key=lambda x: -x[1])[:5])
            tbl.add_row("Agent Commands", cmds_str)
        console.print(tbl)
        installed = self.skills_lib.list_installed()
        if installed:
            console.print(f"  [dim]Installed skills: {', '.join(installed)}[/dim]")
        console.print()

    def _setup_local_brain(self):
        from rich.prompt import Prompt, Confirm
        while True:
            console.print(Panel(
                "[bold cyan]HexMind Local AI Brain[/bold cyan]\n\n"
                "Runs 100% offline on CPU. Works on Kali, Ubuntu, Termux, macOS, Windows.",
                title="[bold green] Local Brain Control Menu [/bold green]",
                border_style="green", padding=(1,2)
            ))
            
            is_ready = False
            active_model = "None"
            if getattr(self, "engine", None):
                llm = self.engine.offline_brain.get_local_llm()
                if llm.is_ready():
                    is_ready = True
                    active_model = llm.model_name()
                
            status_color = "green" if (self.engine and self.engine.offline_brain.is_offline() and is_ready) else "red"
            status_text = "ON" if (self.engine and self.engine.offline_brain.is_offline() and is_ready) else "OFF"
            
            menu = [
                ("1", "Toggle Local Brain", f"Currently: [{status_color}]{status_text}[/{status_color}]"),
                ("2", "Active Model",       f"{active_model}"),
                ("3", "Install/Change Model", "Download or switch to a new model"),
                ("4", "Uninstall Model",    "Remove a downloaded model to free space"),
                ("5", "Back",               "Return to chat")
            ]
            t = Table(box=box.ROUNDED, border_style="cyan")
            t.add_column("#", style="bold cyan", width=3)
            t.add_column("Action", style="bold white")
            t.add_column("Status", style="dim white")
            for m in menu: t.add_row(*m)
            console.print(t)
            
            choice = Prompt.ask("  [cyan]Select (1-5)[/cyan]", default="5").strip()
            
            if choice == "1":
                if not self.engine:
                    console.print("  [red]No engine running. Type 'settings' first.[/red]\n")
                else:
                    current = self.engine.offline_brain.is_offline()
                    if not current and not is_ready:
                        ok = self.engine.offline_brain.get_local_llm().setup(cp=lambda s: console.print(s) if not isinstance(s, str) else console.print(f"  {s}"))
                        if ok:
                            self.engine.offline_brain.set_offline(True)
                            console.print("  [green]Local Brain is now ON[/green]\n")
                        else:
                            console.print("  [red]Failed to start Local Brain.[/red]\n")
                    else:
                        self.engine.offline_brain.set_offline(not current)
                        console.print(f"  [green]Local Brain is now {'ON' if not current else 'OFF'}[/green]\n")
                
            elif choice == "2":
                console.print(f"  [dim]Active model is: {active_model}[/dim]\n")
                time.sleep(1)
                
            elif choice == "3":
                if self.engine:
                    ok = self.engine.offline_brain.get_local_llm().setup(force=True, cp=lambda s: console.print(s) if not isinstance(s, str) else console.print(f"  {s}"))
                    if ok:
                        self.engine.offline_brain.set_offline(True)
                
            elif choice == "4":
                if self.engine:
                    llm = self.engine.offline_brain.get_local_llm()
                    models = llm.list_models()
                    if not models:
                        console.print("  [yellow]No downloaded models found or Ollama is not running.[/yellow]\n")
                    else:
                        mt = Table(title="[bold cyan]Downloaded Models[/bold cyan]", box=box.ROUNDED, border_style="cyan")
                        mt.add_column("#", style="bold cyan")
                        mt.add_column("Model Name", style="white")
                        mt.add_column("Size", style="yellow")
                        for i, m in enumerate(models, 1):
                            mt.add_row(str(i), m["name"], m["size"])
                        console.print(mt)
                        
                        rm_choice = Prompt.ask("  [cyan]Enter # to uninstall (or 'c' to cancel)[/cyan]", default="c").strip()
                        if rm_choice.lower() != 'c':
                            try:
                                idx = int(rm_choice) - 1
                                if 0 <= idx < len(models):
                                    model_to_rm = models[idx]["name"]
                                    if Confirm.ask(f"  [red]Are you sure you want to delete {model_to_rm}?[/red]", default=False):
                                        console.print(f"  [dim]Uninstalling {model_to_rm}...[/dim]")
                                        if llm.remove_model(model_to_rm):
                                            console.print(f"  [green]Successfully removed {model_to_rm}.[/green]\n")
                                            if active_model == model_to_rm:
                                                llm._ollama_model = None
                                                llm._ready = False
                                        else:
                                            console.print(f"  [red]Failed to remove {model_to_rm}.[/red]\n")
                            except ValueError:
                                pass
                
            elif choice == "5":
                console.print("  [dim]Returning to chat...[/dim]")
                break
            
            console.print("[dim]Press Enter to continue...[/dim]")
            input()
            clear()
            show_banner()

    # ── Shell command ─────────────────────────────────────────────────────────
    def _run_shell(self, cmd: str):
        if not cmd:
            console.print("  [dim]Usage: !<command>  e.g. !nmap -sV 192.168.1.1[/dim]\n"); return
            
        from brain.offline import translate_command
        cmd = translate_command(cmd)
        
        console.print(f"\n  [bold yellow]$ {escape(cmd)}[/bold yellow]\n")
        os.system(cmd)
        console.print()

    # ── Mode switch ───────────────────────────────────────────────────────────
    def _switch_mode(self):
        from rich.prompt import Prompt
        modes = [
            ("1","Hacker Mode",       "Offensive security, exploits, CTF mindset"),
            ("2","Developer Mode",    "Code, debugging, secure development"),
            ("3","OSINT Mode",        "Reconnaissance and intelligence gathering"),
            ("4","Tutor Mode",        "Step-by-step teaching, patient and thorough"),
            ("5","General Assistant", "General AI with security expertise"),
        ]
        t = Table(title="[bold cyan]Select Mode[/bold cyan]", box=box.ROUNDED, border_style="cyan")
        t.add_column("#", style="bold cyan", width=4)
        t.add_column("Mode", style="bold white")
        t.add_column("Focus", style="dim white")
        for m in modes: t.add_row(*m)
        console.print(t)
        c    = Prompt.ask("  [cyan]Select (1-5)[/cyan]", default="1")
        sel  = {m[0]:m[1] for m in modes}.get(c,"Hacker Mode")
        if self.engine: self.engine.set_mode(sel)
        self.config["mode"] = sel
        self.cfg_mgr.save(self.config)
        console.print(f"\n  [bold green]Mode → {sel}[/bold green]\n")

    # ── Help ──────────────────────────────────────────────────────────────────
    def _show_help(self):
        cmds = [
            ("help",       "Show this menu"),
            ("tools",      "Built-in tools (port scanner, DNS, hash, encode/decode, etc.)"),
            ("brain",      "Setup local AI brain (Ollama + 9 models, 100% offline)"),
            ("diagnostics","Check AI response speed, memory footprint, and token stream rate"),
            ("target <dev>", "Create a structured Pentest Workspace (recon/, scans/)"),
            ("untarget",   "Clear the active Pentest Workspace"),
            ("start-recon", "Run an autonomous tool chain (subfinder->httpx->nmap->AI)"),
            ("see <img.png>", "Analyze a screenshot/image for vulnerabilities and attack surfaces"),
            ("crawl <url>", "Scrape a target for interactive forms and automatically generate exploit payloads (SQLi/XSS)"),
            ("watch <log>", "Run background Log Sentinel AI to alert on intrusions (SQLi/Bruteforce)"),
            ("agent <goal>", "Launch True Autonomous ReAct AI (Think > Act > Observe loop) to accomplish complex OS tasks"),
            ("skills",     "Install/manage skill packs (web-top10, privesc, CTF, payloads...)"),
            ("theme",      "Install HexMind AI Terminal Theme & Companion hooks"),
            ("memory",     "Show what HexMind has learned about you + session stats"),
            ("mode",       "Switch AI mode (Hacker / Dev / OSINT / Tutor)"),
            ("settings",   "Change AI provider / API key"),
            ("system",     "System controls (restart, reset, reonboard, clear memory...)"),
            ("profile",    "View your profile and settings"),
            ("status",     "Show current AI mode and connection status"),
            ("history",    "View this session's chat history"),
            ("save",       "Save session to ~/.hexmind/sessions/"),
            ("clear",      "Clear terminal"),
            ("about",      "About HexMind"),
            ("!<command>", "Run shell command directly (e.g. !nmap -sV 10.0.0.1)"),
            ("exit",       "Exit HexMind"),
        ]
        t = Table(title="[bold cyan]HexMind Commands[/bold cyan]", box=box.ROUNDED, border_style="cyan")
        t.add_column("Command",     style="bold cyan",  no_wrap=True)
        t.add_column("Description", style="white")
        for c in cmds: t.add_row(*c)
        console.print(t)
        console.print(
            "  [dim]Agent mode: just describe what you want — 'scan 192.168.1.1', 'show the directory', etc.[/dim]\n"
        )

    # ── Status ────────────────────────────────────────────────────────────────
    def _show_status(self):
        prov     = self.config.get("provider", {})
        offline  = self.engine and self.engine.is_offline()
        local_ai = offline and self.engine and self.engine.offline_brain.local_llm_ready()

        llm_name = "N/A"
        if self.engine and self.engine.offline_brain:
            llm = self.engine.offline_brain.get_local_llm()
            if llm and llm.is_ready():
                llm_name = f"{llm.backend_name()} ({llm.model_name()})"

        if local_ai:
            src_str = f"[bold yellow]🧠 Local AI Brain ({llm_name})[/bold yellow]"
        elif offline:
            src_str = "[bold red]⚡ Offline Knowledge Base[/bold red]"
        else:
            src_str = f"[bold green]☁ Cloud AI ({prov.get('name','?')})[/bold green]"

        console.print(Panel(
            f"[bold]Source:[/bold]  {src_str}\n"
            f"[bold]Model:[/bold]   {prov.get('model_name', prov.get('model','N/A'))}\n"
            f"[bold]Mode:[/bold]    [cyan]{self.config.get('mode','Hacker Mode')}[/cyan]\n"
            f"[bold]Local AI:[/bold] {llm_name}\n"
            f"[bold]User:[/bold]    {self.user.get('name','?')} · {self.user.get('os','?')} · {self.user.get('experience','?')}",
            title="[bold cyan] Status [/bold cyan]", border_style="cyan", padding=(0,2)
        ))
        console.print()

    # ── Profile ───────────────────────────────────────────────────────────────
    def _show_profile(self):
        u = self.user; p = self.config.get("provider",{})
        t = Table(title="[bold cyan]Your Profile[/bold cyan]", box=box.ROUNDED, border_style="cyan")
        t.add_column("Field", style="bold cyan"); t.add_column("Value", style="white")
        rows = [
            ("Name", u.get("name","N/A")),("Focus", u.get("skill","N/A")),
            ("Platform", u.get("os","N/A")),("Experience", u.get("experience","N/A")),
            ("Provider", p.get("name","N/A")),("Model", p.get("model_name", p.get("model","N/A"))),
            ("Mode", self.config.get("mode","Hacker Mode")),
        ]
        for r in rows: t.add_row(*r)
        console.print(t); console.print()

    # ── History ───────────────────────────────────────────────────────────────
    def _show_history(self):
        if not self.session_log:
            console.print("  [dim]No history this session.[/dim]\n"); return
        console.print()
        for e in self.session_log:
            color = "cyan" if e["role"]=="user" else "green"
            label = "You" if e["role"]=="user" else "HexMind"
            prev  = e["content"][:100] + ("…" if len(e["content"])>100 else "")
            console.print(f"  [dim]{e.get('time','')}[/dim]  [bold {color}]{label}[/bold {color}]: {prev}")
        console.print()

    # ── Save ──────────────────────────────────────────────────────────────────
    def _save_session(self):
        if not self.session_log:
            console.print("  [dim]Nothing to save yet.[/dim]\n"); return
        d = CONFIG_DIR / "sessions"; d.mkdir(parents=True, exist_ok=True)
        f = d / f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        f.write_text(json.dumps(self.session_log, indent=2))
        console.print(f"  [bold green]Saved:[/bold green] {f}\n")

    # ── About ─────────────────────────────────────────────────────────────────
    def _show_about(self):
        _A2 = bytes.fromhex('41726a756e2054204d').decode('utf-8')
        _G2 = bytes.fromhex('6769746875622e636f6d2f63796265726b616c6c616e').decode('utf-8')
        console.print(Panel(
            "[bold cyan]HexMind v2.5[/bold cyan] — AI-Powered Hacker Terminal Assistant\n\n"
            f"[dim]Author  :[/dim]  {_A2}\n"
            f"[dim]GitHub  :[/dim]  {_G2}\n\n"
            "[bold white]Features:[/bold white]\n"
            "  • Cloud AI — OpenRouter (free), Anthropic, Gemini, OpenAI, DeepSeek\n"
            "  • Local AI — Ollama (9 models, 90MB to 4GB), runs offline on CPU\n"
            "  • Agent mode — understands natural language, auto-executes commands\n"
            "  • Smart prompts — anti-refusal engineering for security queries\n"
            "  • Knowledge base — 20+ cybersecurity topics, instant offline fallback\n"
            "  • Built-in tools — port scanner, DNS, hash, encoder, IP info\n"
            "  • Multi-mode — Hacker / Developer / OSINT / Tutor\n"
            "  • System controls — restart, reset, reonboard, memory management\n\n"
            "[dim]Built for hackers, pentesters, CTF players and devs.[/dim]",
            title="[bold green] About [/bold green]", border_style="green", padding=(1,2)
        ))
        console.print()

    # ── Memory stats ──────────────────────────────────────────────────────────
    def _show_memory_stats(self):
        if not self.engine:
            console.print("  [dim]No session started yet.[/dim]\n"); return
        stats = self.engine.memory.get_stats()
        tbl = Table(title="[bold cyan]HexMind Memory & Learning[/bold cyan]", box=box.ROUNDED, border_style="cyan")
        tbl.add_column("Metric", style="bold cyan"); tbl.add_column("Value", style="white")
        tbl.add_row("Total sessions",   str(stats["sessions"]))
        tbl.add_row("Total messages",   str(stats["messages"]))
        tbl.add_row("First seen",       stats["first_seen"][:10] if stats["first_seen"] != "?" else "?")
        if stats["top_topics"]:
            topics_str = ", ".join(f"{tp}({cnt})" for tp, cnt in stats["top_topics"])
            tbl.add_row("Top interests", topics_str)
        if stats["tools_used"]:
            tools_str = ", ".join(f"{k}({v})" for k, v in sorted(stats["tools_used"].items(), key=lambda x: -x[1])[:5])
            tbl.add_row("Tools used",    tools_str)
        if stats["commands_run"]:
            cmds_str = ", ".join(f"{k}({v})" for k, v in sorted(stats["commands_run"].items(), key=lambda x: -x[1])[:5])
            tbl.add_row("Agent commands run", cmds_str)
        console.print(tbl)
        console.print("  [dim]HexMind learns from every conversation to improve responses over time.[/dim]\n")

    # ── Exit ──────────────────────────────────────────────────────────────────
    def _exit(self):
        name = self.user.get("name","Hacker")
        console.print(f"\n  [bold cyan]Stay safe out there, {name}. See you next time! 👋[/bold cyan]\n")
        sys.exit(0)

    # ── System Controls ───────────────────────────────────────────────────────
    def _system_controls(self):
        from rich.prompt import Prompt
        
        auto_learn_state = "[green]ON[/green]" if self.user.get("auto_learn", False) else "[red]OFF[/red]"
        
        controls = [
            ("1", "Restart Session",     "Clear chat history, keep settings"),
            ("2", "Reonboard",           "Re-run first-time setup (name, skill, etc.)"),
            ("3", "Reset Everything",    "Delete ALL config, memory, skills"),
            ("4", "Clear Memory",        "Wipe learned data, keep config"),
            ("5", "Clear Skills",        "Remove all installed skill packs"),
            ("6", "Change Brain Model",  "Re-select Ollama model for local AI"),
            ("7", "Export Config",       "Show current config as JSON"),
            ("8", "Toggle Auto-Learn",   f"Background intelligence gathering is {auto_learn_state}"),
            ("9", "Back",               "Return to chat"),
        ]
        t = Table(title="[bold cyan]System Controls[/bold cyan]", box=box.ROUNDED, border_style="cyan")
        t.add_column("#", style="bold cyan", width=3)
        t.add_column("Action", style="bold white")
        t.add_column("Info", style="dim white")
        for c in controls: t.add_row(*c)
        console.print(t)

        choice = Prompt.ask("  [cyan]Select (1-8)[/cyan]", default="8").strip()

        if choice == "1":
            # Restart session
            self.session_log.clear()
            if self.engine:
                self.engine.history.clear()
            console.print("  [green]Session restarted. Chat history cleared.[/green]\n")
            clear(); show_banner()

        elif choice == "2":
            # Reonboard
            console.print("  [cyan]Re-running first-time setup...[/cyan]\n")
            self._first_time_setup()
            self._init_engine()
            console.print("  [green]Setup complete![/green]\n")

        elif choice == "3":
            # Full reset
            from rich.prompt import Confirm
            if Confirm.ask("  [red]Delete ALL HexMind data?[/red]", default=False):
                import shutil
                data_dir = Path.home() / ".hexmind"
                if data_dir.exists():
                    shutil.rmtree(data_dir)
                console.print("  [green]Everything reset. Restarting...[/green]\n")
                time.sleep(1)
                os.execv(sys.executable, [sys.executable] + sys.argv)
            else:
                console.print("  [dim]Cancelled.[/dim]\n")

        elif choice == "4":
            # Clear memory
            mem_dir = Path.home() / ".hexmind" / "memory"
            if mem_dir.exists():
                import shutil
                shutil.rmtree(mem_dir)
                mem_dir.mkdir(parents=True, exist_ok=True)
            console.print("  [green]Memory cleared.[/green]\n")

        elif choice == "5":
            # Clear skills
            skills_dir = Path.home() / ".hexmind" / "skills"
            if skills_dir.exists():
                import shutil
                shutil.rmtree(skills_dir)
                skills_dir.mkdir(parents=True, exist_ok=True)
            console.print("  [green]All skill packs removed.[/green]\n")

        elif choice == "6":
            # Change brain model
            if self.engine:
                llm = self.engine.offline_brain.get_local_llm()
                llm._ready = False
                llm.setup(console_print=lambda s: console.print(f"  {s}"))
            else:
                console.print("  [dim]Start a session first (type 'settings').[/dim]\n")

        elif choice == "8":
            # Toggle Auto-Learn
            current_state = self.user.get("auto_learn", False)
            new_state = not current_state
            self.user["auto_learn"] = new_state
            self.config["user"] = self.user
            self.cfg_mgr.save(self.config)
            
            try:
                if new_state:
                    from modules.self_learning import start_daemon
                    start_daemon(self.engine, console)
                    console.print("  [bold green]✓ Background Auto-Learning ENABLED[/bold green]")
                    console.print("  [dim]HexMind will now passively research infosec concepts.[/dim]\n")
                else:
                    from modules.self_learning import stop_daemon
                    stop_daemon()
                    console.print("  [bold red]⨯ Background Auto-Learning DISABLED[/bold red]\n")
            except Exception as e:
                console.print(f"  [red]Failed to toggle daemon: {e}[/red]\n")

        elif choice == "7":
            # Export config
            console.print(Panel(
                json.dumps(self.config, indent=2, default=str),
                title="[bold cyan]Config[/bold cyan]",
                border_style="cyan"
            ))
            console.print()

    # ── Auto-execute commands from AI response ────────────────────────────────
    def _offer_command_execution(self, response: str):
        """Detect code blocks in AI response and offer to run them."""
        # Find strictly tagged bash/sh/shell/console code blocks to avoid parsing natural text or bullets.
        pattern = r'```(?:bash|sh|shell|console|linux|ubuntu|debian|centos)\n(.*?)```'
        blocks = re.findall(pattern, response, re.IGNORECASE | re.DOTALL)
        
        # If no strictly tagged bash blocks are found, try fallback ONLY if there's a highly confident single code block
        if not blocks:
            # If there's exactly one generic block, and it contains bash-like tokens (not lists/markdown)
            generic_blocks = re.findall(r'```(?:\w+)?\n(.*?)```', response, re.DOTALL)
            if generic_blocks:
                for b in generic_blocks:
                    # Ignore blocks that look like python or markdown descriptions
                    if "import " in b or "def " in b or "1. " in b or "**" in b:
                        continue
                    if any(cmd in b for cmd in ["sudo ", "apt ", "pkg ", "cd ", "nmap ", "curl ", "wget ", "chmod ", "ls ", "python3 ", "pip ", "git "]):
                        blocks.append(b)
                        
        if not blocks:
            return

        # Extract individual commands from code blocks
        cmds = []
        for block in blocks:
            for line in block.strip().split('\n'):
                line = line.strip()
                # Remove common bash prefix symbols
                if line.startswith('$ '):
                    line = line[2:].strip()
                elif line.startswith('# ') and not line.startswith('#!/'):
                    continue # Skip comments
                    
                # Skip pure empty lines, markdown artifacts, and output lines
                if line and len(line) < 300 and not line.startswith(('  ', '\t', '->', '=>', '|', '•', '*', '1.', '2.', '3.')):
                    cmds.append(line)

        if not cmds or len(cmds) > 5:
            return

        # Show extracted commands
        from rich.markup import escape # Added this import for escape function
        console.print(Panel(
            "\n".join(f"[cyan]{i}.[/cyan] {escape(c)}" for i, c in enumerate(cmds[:5], 1)),
            title="[bold yellow]⚡ Agent Task Execution[/bold yellow]",
            border_style="yellow", padding=(0,2)
        ))

        try:
            from rich.prompt import Prompt
            console.print("  [dim]HexMind can run these commands for you automatically.[/dim]")
            choice = Prompt.ask(
                "  [yellow]▶ Execute task? (number/[bold]all[/bold]/[bold]s[/bold]kip)[/yellow]",
                default="s"
            ).strip().lower()

            if choice in ["skip", "s", "no", "n", ""]:
                return
            elif choice == "all" or choice == "a":
                for c in cmds[:5]:
                    self._run_shell(c)
            else:
                try:
                    idx = int(choice) - 1
                    if 0 <= idx < len(cmds):
                        self._run_shell(cmds[idx])
                except ValueError:
                    pass
        except (KeyboardInterrupt, EOFError):
            pass

    # ── Heartbeat — idle tips ─────────────────────────────────────────────────
    def _start_heartbeat(self):
        """Background thread that shows tips when user is idle."""
        self._last_activity = time.time()

        def heartbeat_loop():
            tips_shown = 0
            idle_tips = [
                "💡 [dim]Tip: Type 'skills' to install security cheatsheets[/dim]",
                "🧠 [dim]Tip: Set up local brain with 'brain' for offline AI[/dim]",
                "⚙️  [dim]Tip: Use 'mode' to switch to OSINT/Tutor/Dev mode[/dim]",
                "🚀 [dim]Tip: Just describe what you want — 'scan my network', 'crack this hash'[/dim]",
                "🔍 [dim]Tip: Use '!command' to run any shell command inline[/dim]",
                "💾 [dim]Tip: 'save' saves this entire session to disk[/dim]",
            ]
            while True:
                time.sleep(5)
                idle = time.time() - self._last_activity
                if idle > 45 and tips_shown < 3:
                    console.print(f"\n  {idle_tips[tips_shown % len(idle_tips)]}")
                    tips_shown += 1
                    self._last_activity = time.time()

        t = threading.Thread(target=heartbeat_loop, daemon=True)
        t.start()
