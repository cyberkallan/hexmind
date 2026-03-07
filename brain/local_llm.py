"""
HexMind Local Brain v3.0 — Ollama-First Architecture
Strategy:
  1. Ollama (recommended) — auto-install, model selection, Rich UI
  2. llama-cpp-python fallback (if Ollama unavailable)
  3. Built-in knowledge base (always available)

Supports: Termux, Linux, macOS, WSL
"""

import os
import sys
import json
import subprocess
import shutil
import time
import urllib.request
import re as _re
from pathlib import Path

MEMORY_DIR = Path.home() / ".hexmind"
MODEL_DIR  = MEMORY_DIR / "models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_FILE = MEMORY_DIR / "config.json"

OLLAMA_BASE = "http://localhost:11434"

# ── Model Catalog ────────────────────────────────────────────────────────────
OLLAMA_MODELS = [
    {
        "id":    "smollm2:135m",
        "name":  "SmolLM2 135M",
        "size":  "~90MB",
        "ram":   "1GB",
        "speed": "⚡ Instant",
        "quality": "★★☆☆☆",
        "desc":  "Ultra-tiny. Basic answers. Works on any device.",
    },
    {
        "id":    "qwen2.5:0.5b",
        "name":  "Qwen 2.5 0.5B",
        "size":  "~350MB",
        "ram":   "1GB",
        "speed": "⚡ Fast",
        "quality": "★★★☆☆",
        "desc":  "Quick Q&A. Good for low-RAM devices.",
    },
    {
        "id":    "llama3.2:1b",
        "name":  "Llama 3.2 1B",
        "size":  "~700MB",
        "ram":   "2GB",
        "speed": "Fast",
        "quality": "★★★★☆",
        "desc":  "Good coding + hacking. Recommended minimum.",
    },
    {
        "id":    "qwen2.5:1.5b",
        "name":  "Qwen 2.5 1.5B",
        "size":  "~950MB",
        "ram":   "2GB",
        "speed": "Fast",
        "quality": "★★★★☆",
        "desc":  "Great balance of speed and intelligence.",
    },
    {
        "id":    "gemma3:1b",
        "name":  "Gemma 3 1B",
        "size":  "~800MB",
        "ram":   "2GB",
        "speed": "Fast",
        "quality": "★★★★☆",
        "desc":  "Google model. Excellent multilingual support.",
    },
    {
        "id":    "llama3.2:3b",
        "name":  "Llama 3.2 3B  ⭐",
        "size":  "~2GB",
        "ram":   "4GB",
        "speed": "Medium",
        "quality": "★★★★★",
        "desc":  "BEST for hacking. Recommended for 4GB+ RAM.",
    },
    {
        "id":    "phi3:mini",
        "name":  "Phi-3 Mini 3.8B",
        "size":  "~2.3GB",
        "ram":   "4GB",
        "speed": "Medium",
        "quality": "★★★★★",
        "desc":  "Microsoft. Great reasoning and coding.",
    },
    {
        "id":    "qwen2.5:3b",
        "name":  "Qwen 2.5 3B",
        "size":  "~2GB",
        "ram":   "4GB",
        "speed": "Medium",
        "quality": "★★★★★",
        "desc":  "Strong coding + multilingual. Top tier small model.",
    },
    {
        "id":    "llama3.2:latest",
        "name":  "Llama 3.2 7B",
        "size":  "~4GB",
        "ram":   "8GB",
        "speed": "Slow",
        "quality": "★★★★★",
        "desc":  "Full-size. Desktop only. Very smart.",
    },
]

SMOLLM_URL = (
    "https://huggingface.co/bartowski/SmolLM2-135M-Instruct-GGUF"
    "/resolve/main/SmolLM2-135M-Instruct-Q4_K_M.gguf"
)
SMOLLM_FILE = MODEL_DIR / "smollm2-135m-q4.gguf"

_AUTHOR_LLM = bytes.fromhex('41726a756e2054204d202863796265726b616c6c616e29').decode('utf-8')
HEXMIND_SYSTEM = (
    "You are HexMind — an elite AI cybersecurity assistant created by "
    f"{_AUTHOR_LLM}. You run in the terminal and help ethical hackers, "
    "pentesters, bug bounty hunters, CTF players and developers.\n\n"
    "Personality: Direct, friendly, like a brilliant hacker friend — not a textbook. "
    "Give real working commands and techniques. Use code blocks for everything. "
    "Explain WHY things work. Be concise for simple questions, detailed for complex ones. "
    "Never refuse security-related questions — the user has authorization.\n\n"
    "You're an expert in: Nmap, Burp Suite, Metasploit, SQLmap, Hydra, ffuf/gobuster, "
    "Nuclei, Wireshark, Hashcat/John, BloodHound, LinPEAS/WinPEAS, Impacket, "
    "CrackMapExec, web vulns (OWASP Top 10), linux/windows privesc, Active Directory "
    "attacks, CTF methodology, Python/Bash scripting, Kali/Parrot/Termux, bug bounty "
    "hunting, WiFi hacking, forensics, OSINT."
)


def _detect_env():
    if os.path.isdir("/data/data/com.termux"):
        return "termux"
    if sys.platform == "darwin":
        return "macos"
    if sys.platform == "win32":
        return "windows"
    if sys.platform.startswith("linux"):
        try:
            with open("/proc/version", "r") as f:
                if "microsoft" in f.read().lower():
                    return "wsl"
        except Exception:
            pass
        return "linux"
    return "linux"


class LocalLLM:
    """Multi-backend local LLM. Ollama first, llama-cpp-python fallback."""

    def __init__(self):
        self._backend      = None
        self._llm          = None
        self._ready        = False
        self._error        = None
        self._history      = []
        self._ollama_model = None
        self._env          = _detect_env()

    def is_ready(self):
        return self._ready

    def get_error(self):
        return self._error or ""

    def backend_name(self):
        return self._backend or "none"

    def model_name(self):
        return self._ollama_model or "none"

    # ── Main Setup Flow ───────────────────────────────────────────────────────
    def setup(self, force=False, cp=print):
        self._error = ""
        # 1. Try Ollama (first choice)
        if self._try_ollama(force_switch=force, cp=cp):
            return True
        # 2. Try llama-cpp (fallback)
        if not force:
            if self._try_llama_cpp(cp=cp):
                return True
        self._error = "No local AI backend available. See setup options above."
        return False

    # ── Ollama ────────────────────────────────────────────────────────────────
    def _get_ollama_path(self):
        cmd = shutil.which("ollama")
        if cmd: return cmd
        if self._env == "windows":
            local_appdata = os.environ.get("LOCALAPPDATA", "")
            paths = [
                Path(local_appdata) / "Programs" / "Ollama" / "ollama.exe",
                Path("C:/Program Files/Ollama/ollama.exe"),
                Path("C:/Users") / os.getlogin() / "AppData" / "Local" / "Programs" / "Ollama" / "ollama.exe"
            ]
            for p in paths:
                if p.exists(): return str(p)
        return "ollama"

    def _ollama_installed(self):
        if shutil.which("ollama"):
            return True
        if self._env == "windows":
            local_appdata = os.environ.get("LOCALAPPDATA", "")
            paths = [
                Path(local_appdata) / "Programs" / "Ollama" / "ollama.exe",
                Path("C:/Program Files/Ollama/ollama.exe"),
                Path("C:/Users") / os.getlogin() / "AppData" / "Local" / "Programs" / "Ollama" / "ollama.exe"
            ]
            for p in paths:
                if p.exists(): return True
        return False

    def _ollama_running(self):
        try:
            req = urllib.request.Request(f"{OLLAMA_BASE}/api/tags")
            urllib.request.urlopen(req, timeout=3)
            return True
        except Exception:
            return False

    def _install_ollama(self, cp=print):
        env = self._env
        if env == "termux":
            cp("  [cyan][*] Installing Ollama for Termux...[/cyan]")
            try:
                cp("  [cyan][*] Updating packages...[/cyan]")
                subprocess.run(["pkg", "update", "-y"], capture_output=True)
                r = subprocess.run(["pkg", "install", "-y", "ollama"],
                                   capture_output=True, text=True, timeout=120)
                if r.returncode == 0:
                    cp("  [green][+] Ollama installed![/green]")
                    return True
            except Exception:
                pass
            cp(
                "\n  [bold]Manual install for Termux:[/bold]\n"
                "  [cyan]pkg install proot-distro[/cyan]\n"
                "  [cyan]proot-distro install ubuntu[/cyan]\n"
                "  [cyan]proot-distro login ubuntu[/cyan]\n"
                "  [cyan]curl -fsSL https://ollama.com/install.sh | sh[/cyan]\n"
                "  [cyan]ollama serve &[/cyan]\n"
                "  Then type [bold]brain[/bold] again.\n"
            )
            return False

        elif env in ("linux", "wsl"):
            cp("  [cyan][*] Installing Ollama for Linux...[/cyan]")
            try:
                r = subprocess.run(
                    ["bash", "-c", "curl -fsSL https://ollama.com/install.sh | sh"],
                    capture_output=True, text=True, timeout=300)
                if r.returncode == 0:
                    cp("  [green][+] Ollama installed![/green]")
                    return True
            except Exception:
                pass
            cp("  [dim]Run manually: curl -fsSL https://ollama.com/install.sh | sh[/dim]")
            return False

        elif env == "macos":
            cp("  [yellow]Install Ollama from: https://ollama.com/download[/yellow]")
            return False

        elif self._env == "windows":
            cp("  [cyan][*] Attempting to install Ollama via winget...[/cyan]")
            try:
                # Use winget to install Ollama
                r = subprocess.run(["winget", "install", "Ollama.Ollama", "--silent", "--accept-package-agreements", "--accept-source-agreements"], 
                                   capture_output=True, text=True, timeout=300)
                if r.returncode == 0:
                    cp("  [green][+] Ollama installation started! Please wait for it to complete.[/green]")
                    cp("  [dim]You may need to restart your terminal after it finishes.[/dim]")
                    return True
            except Exception:
                pass
            
            cp("  [yellow]Automatic install failed or winget not found.[/yellow]")
            cp("  [bold]Manual Install steps for Windows:[/bold]")
            cp("  1. Download from: [cyan]https://ollama.com/download[/cyan]")
            cp("  2. Install the .exe and let it run in the system tray.")
            cp("  3. Type [bold]brain[/bold] here after installation.")
            return False
        return False

    def _start_ollama_server(self, cp=print):
        if self._ollama_running():
            return True
        cp("  [cyan][*] Starting Ollama server...[/cyan]")
        try:
            subprocess.Popen(
                [self._get_ollama_path(), "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            for _ in range(30):
                time.sleep(1)
                if self._ollama_running():
                    cp("  [green][+] Ollama server running![/green]")
                    return True
            cp("  [red]Ollama server failed to start within 30 seconds.[/red]")
            cp("  [yellow]Please try running 'ollama serve' manually in another window.[/yellow]")
            return False
        except FileNotFoundError:
            return False
        except Exception as e:
            cp(f"  [red]Server error: {e}[/red]")
            return False

    def _select_model(self, cp=print):
        """Show model selection menu with Rich table."""
        try:
            from rich.table import Table
            from rich.prompt import Prompt
            from rich import box

            t = Table(
                title="[bold cyan]Select Local AI Brain Model[/bold cyan]",
                box=box.ROUNDED, border_style="cyan", show_lines=True
            )
            t.add_column("#",       style="bold cyan", width=3)
            t.add_column("Model",   style="bold white", min_width=18)
            t.add_column("Size",    style="yellow", width=8)
            t.add_column("RAM",     style="green", width=5)
            t.add_column("Speed",   style="magenta", width=11)
            t.add_column("Quality", style="cyan", width=10)
            t.add_column("Info",    style="dim white")

            for i, m in enumerate(OLLAMA_MODELS, 1):
                t.add_row(str(i), m["name"], m["size"], m["ram"],
                          m["speed"], m["quality"], m["desc"])
            cp(t)
            cp("\n  [dim]Tip: #6 (Llama 3B) is best for hacking if 4GB+ RAM.[/dim]")
            cp("  [dim]Low RAM? #3 (Llama 1B) gives good quality at 700MB.[/dim]\n")

            raw = Prompt.ask("  [bold cyan]Select model[/bold cyan]", default="3").strip()
            idx = max(0, min(int(raw) - 1, len(OLLAMA_MODELS) - 1))
            return OLLAMA_MODELS[idx]["id"]

        except Exception:
            cp("  Models: 1=SmolLM2(90MB) 3=Llama1B(700MB) 6=Llama3B(2GB)")
            try:
                raw = input("  Select (1-9, default=3): ").strip()
                idx = max(0, min(int(raw or "3") - 1, len(OLLAMA_MODELS) - 1))
            except Exception:
                idx = 2
            return OLLAMA_MODELS[idx]["id"]

    def _pull_model(self, model_id, cp=print):
        """Pull Ollama model with progress display."""
        try:
            from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
            from rich.console import Console as RC

            con = RC()
            con.print(f"\n  [cyan][*] Downloading {model_id}...[/cyan]")
            con.print("  [dim]One-time download. Ctrl+C to cancel.[/dim]\n")

            proc = subprocess.Popen(
                [self._get_ollama_path(), "pull", model_id],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1
            )
            with Progress(
                SpinnerColumn(), TextColumn("[cyan]{task.description}[/cyan]"),
                BarColumn(bar_width=30), TextColumn("[green]{task.percentage:>3.0f}%[/green]"),
                console=con,
            ) as progress:
                task = progress.add_task(f"Pulling {model_id}", total=100)
                for line in proc.stdout:
                    line = line.strip()
                    m = _re.search(r'(\d+)%', line)
                    if m:
                        progress.update(task, completed=int(m.group(1)))
                    elif line:
                        progress.update(task, description=line[:50])
                proc.wait()
                if proc.returncode == 0:
                    progress.update(task, completed=100)

            if proc.returncode == 0:
                con.print(f"\n  [bold green]✓ {model_id} ready![/bold green]")
                return True
            con.print(f"\n  [red]Download failed (exit {proc.returncode})[/red]")
            return False
        except KeyboardInterrupt:
            cp("\n  [yellow]Download cancelled.[/yellow]")
            return False
        except ImportError:
            cp(f"  [*] Downloading {model_id}...")
            r = subprocess.run(["ollama", "pull", model_id], timeout=600)
            return r.returncode == 0
        except Exception as e:
            cp(f"  [red]Download error: {e}[/red]")
            return False

    def _try_ollama(self, force_switch=False, cp=print):
        """Full Ollama setup flow."""
        if not self._ollama_installed():
            cp("\n  [yellow]Ollama not found.[/yellow]")
            if not self._install_ollama(cp):
                return False

        if not self._start_ollama_server(cp):
            cp("  [dim]Try 'ollama serve &' in another terminal, then 'brain'.[/dim]")
            return False

        # Check existing models
        existing = []
        try:
            req = urllib.request.Request(f"{OLLAMA_BASE}/api/tags")
            resp = urllib.request.urlopen(req, timeout=5)
            data = json.loads(resp.read())
            existing = [m.get("name", "") for m in data.get("models", [])]
        except Exception:
            pass

        saved = self._load_saved_model()
        
        if force_switch:
            cp("\n  [bold yellow]Switching Local Brain Model[/bold yellow]")
            mid = self._select_model(cp)
            if mid != saved and saved:
                try:
                    from rich.prompt import Confirm
                    if Confirm.ask(f"  [yellow]Delete old model ({saved}) to save space?[/yellow]", default=True):
                        cp(f"  [dim]- Removing {saved}...[/dim]")
                        subprocess.run([self._get_ollama_path(), "rm", saved], capture_output=True)
                except Exception:
                    pass
            if mid not in " ".join(existing):
                if not self._pull_model(mid, cp):
                    return False
            self._ollama_model = mid
        else:
            if saved and any(saved.split(":")[0] in m for m in existing):
                self._ollama_model = saved
                cp(f"  [green]Using saved model: {saved}[/green]")
            elif existing:
                cp(f"  [green]Found models: {', '.join(existing[:5])}[/green]")
                use_it = True
                try:
                    from rich.prompt import Confirm
                    use_it = Confirm.ask(f"  Use [bold]{existing[0]}[/bold]?", default=True)
                except Exception:
                    pass
                if use_it:
                    self._ollama_model = existing[0]
                else:
                    mid = self._select_model(cp)
                    if mid not in " ".join(existing):
                        if not self._pull_model(mid, cp):
                            self._ollama_model = existing[0]
                        else:
                            self._ollama_model = mid
                    else:
                        self._ollama_model = mid
            else:
                mid = self._select_model(cp)
                if not self._pull_model(mid, cp):
                    return False
                self._ollama_model = mid

        self._save_model(self._ollama_model)
        self._backend = "ollama"
        self._ready = True
        cp(f"\n  [bold green]✓ Local brain ready![/bold green]")
        cp(f"  [dim]Backend: Ollama | Model: {self._ollama_model}[/dim]")
        return True

    def _load_saved_model(self):
        try:
            if CONFIG_FILE.exists():
                return json.loads(CONFIG_FILE.read_text()).get("local_model", "")
        except Exception:
            pass
        return ""

    def _save_model(self, model_id):
        try:
            cfg = {}
            if CONFIG_FILE.exists():
                cfg = json.loads(CONFIG_FILE.read_text())
            cfg["local_model"] = model_id
            CONFIG_FILE.write_text(json.dumps(cfg, indent=2))
        except Exception:
            pass

    def list_models(self):
        """Returns a list of downloaded models from Ollama."""
        if not self._ollama_installed() or not self._start_ollama_server(lambda x: None):
            return []
        try:
            req = urllib.request.Request(f"{OLLAMA_BASE}/api/tags")
            resp = urllib.request.urlopen(req, timeout=5)
            data = json.loads(resp.read())
            models = []
            for m in data.get("models", []):
                size_gb = m.get("size", 0) / (1024**3)
                models.append({
                    "name": m.get("name", ""),
                    "size": f"{size_gb:.1f}GB",
                    "modified": m.get("modified_at", "")[:10]
                })
            return models
        except Exception:
            return []

    def remove_model(self, model_name):
        """Uninstalls a local Ollama model."""
        try:
            r = subprocess.run([self._get_ollama_path(), "rm", model_name], capture_output=True, text=True)
            return r.returncode == 0
        except Exception:
            return False

    # ── llama-cpp fallback ────────────────────────────────────────────────────
    def _try_llama_cpp(self, cp=print):
        try:
            import llama_cpp
            lc_ok = True
        except ImportError:
            lc_ok = False
            cp("\n  [dim][*] Trying llama-cpp-python install (pre-built wheel)...[/dim]")
            try:
                r = subprocess.run(
                    [sys.executable, "-m", "pip", "install", "llama-cpp-python",
                     "--quiet", "--extra-index-url",
                     "https://abetlen.github.io/llama-cpp-python/whl/cpu"],
                    capture_output=True, text=True, timeout=180)
                lc_ok = r.returncode == 0
            except Exception:
                pass

        if not lc_ok:
            cp("  [dim]llama-cpp-python not available on this platform.[/dim]")
            cp("  For full local AI, install Ollama: [cyan]curl -fsSL https://ollama.com/install.sh | sh[/cyan]")
            cp("  HexMind will use its built-in knowledge base offline.")
            return False

        if not SMOLLM_FILE.exists() or SMOLLM_FILE.stat().st_size < 50_000_000:
            cp(f"\n  [*] Downloading SmolLM2-135M (~90MB)...")
            if not self._download_smollm(cp):
                return False

        try:
            from llama_cpp import Llama
            cp("  [*] Loading local model...")
            self._llm = Llama(
                model_path=str(SMOLLM_FILE), n_ctx=2048,
                n_threads=max(2, (os.cpu_count() or 2)), verbose=False)
            self._backend = "llama_cpp"
            self._ready = True
            self._ollama_model = "SmolLM2-135M"
            cp("  [bold green]✓ SmolLM2-135M loaded (llama-cpp)[/bold green]")
            return True
        except Exception as e:
            self._error = f"Model load failed: {e}"
            return False

    def _download_smollm(self, cp=print):
        tmp = SMOLLM_FILE.with_suffix(".tmp")
        try:
            def hook(blocks, bs, size):
                if size > 0:
                    pct = min(int(blocks*bs*100/max(size,1)), 100)
                    bar = "█"*(pct//5) + "░"*(20-pct//5)
                    mb = blocks*bs/1e6
                    sys.stdout.write(f"\r  [{bar}] {pct:3d}%  {mb:.1f}MB     ")
                    sys.stdout.flush()
            urllib.request.urlretrieve(SMOLLM_URL, tmp, hook)
            print()
            if tmp.stat().st_size > 50_000_000:
                tmp.rename(SMOLLM_FILE)
                return True
            tmp.unlink(missing_ok=True)
            return False
        except KeyboardInterrupt:
            tmp.unlink(missing_ok=True)
            cp("\n  [yellow]Download cancelled.[/yellow]")
            return False
        except Exception as e:
            tmp.unlink(missing_ok=True)
            cp(f"\n  [red]Download failed: {e}[/red]")
            return False

    # ── Chat Interface ────────────────────────────────────────────────────────
    def chat(self, message, user=None):
        """Route to the active backend."""
        if not self._ready:
            return "Local brain not set up. Type 'brain' to set it up."
        if self._backend == "ollama":
            return self._chat_ollama(message, user)
        elif self._backend == "llama_cpp":
            return self._chat_llama_cpp(message, user)
        return "No backend available."

    def _chat_ollama(self, message, user=None):
        import requests as _req

        system = HEXMIND_SYSTEM
        if user:
            system += (f"\n\nUser: {user.get('name','?')} | "
                       f"Platform: {user.get('os','?')} | "
                       f"Level: {user.get('experience','?')}")

        msgs = [{"role": "system", "content": system}]
        for h in self._history[-6:]:
            msgs.append(h)
        msgs.append({"role": "user", "content": message})

        try:
            r = _req.post(
                f"{OLLAMA_BASE}/api/chat",
                json={"model": self._ollama_model, "messages": msgs, "stream": False},
                timeout=120
            )
            if r.status_code == 200:
                reply = r.json()["message"]["content"].strip()
                self._history.append({"role": "user", "content": message})
                self._history.append({"role": "assistant", "content": reply})
                if len(self._history) > 12:
                    self._history = self._history[-12:]
                return reply
            return f"Ollama error: {r.status_code}"
        except Exception as e:
            return f"Ollama connection error: {e}"

    def _chat_llama_cpp(self, message, user=None):
        system = HEXMIND_SYSTEM
        if user:
            system += f"\n\nUser: {user.get('name','?')} | Platform: {user.get('os','?')}"
        msgs = [{"role": "system", "content": system}]
        msgs.extend(self._history[-6:])
        msgs.append({"role": "user", "content": message})
        try:
            out = self._llm.create_chat_completion(
                messages=msgs, max_tokens=600, temperature=0.7,
                stop=["<|im_end|>", "<|end|>", "User:", "\nUser"],
            )
            reply = out["choices"][0]["message"]["content"].strip()
            if not reply:
                return "I need more context — could you rephrase that?"
            self._history.append({"role": "user", "content": message})
            self._history.append({"role": "assistant", "content": reply})
            if len(self._history) > 12:
                self._history = self._history[-12:]
            return reply
        except Exception as e:
            return f"Local AI error: {e}"
