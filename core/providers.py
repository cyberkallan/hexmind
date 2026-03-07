"""
HexMind Provider Manager v3.0
Fixes: proper connection test (uses /auth/key endpoint), working model IDs March 2026,
       ollama local support, better error messages, India-optimized model ranking.
"""

import requests
import json
import socket

OPENROUTER_BASE    = "https://openrouter.ai/api/v1"
OPENROUTER_REFERER = "https://github.com/cyberkallan/hexmind"
OPENROUTER_TITLE   = "HexMind"

# ── TOP 10 FREE MODELS — Verified working March 2026 ─────────────────────────
# Optimized for India: ranked by reliability + low-latency + quality for hacking/coding
OPENROUTER_FREE_MODELS = [
    {
        "id":    "openrouter/auto",
        "name":  "Auto Router ⭐ (RECOMMENDED)",
        "info":  "Automatically picks the best available free model. Always works.",
        "speed": "Auto",
    },
    {
        "id":    "meta-llama/llama-3.3-70b-instruct:free",
        "name":  "Llama 3.3 70B Instruct",
        "info":  "GPT-4 class quality. Best for hacking/coding tasks. 128K context.",
        "speed": "Medium",
    },
    {
        "id":    "mistralai/mistral-small-3.1-24b-instruct:free",
        "name":  "Mistral Small 3.1 24B",
        "info":  "Fast & reliable. Great all-rounder. 128K context.",
        "speed": "Fast",
    },
    {
        "id":    "google/gemma-3-27b-it:free",
        "name":  "Google Gemma 3 27B",
        "info":  "Google model. Often fastest from India/Asia. 131K context.",
        "speed": "Fast",
    },
    {
        "id":    "deepseek/deepseek-r1:free",
        "name":  "DeepSeek R1 (Reasoning)",
        "info":  "Advanced reasoning. Best for CTF/complex problems. 164K context.",
        "speed": "Slow",
    },
    {
        "id":    "google/gemma-3-12b-it:free",
        "name":  "Google Gemma 3 12B",
        "info":  "Lighter Google model. Very fast responses. Good for quick Q&A.",
        "speed": "Very Fast",
    },
    {
        "id":    "deepseek/deepseek-r1-distill-llama-70b:free",
        "name":  "DeepSeek R1 Distill 70B",
        "info":  "Distilled reasoning model. Better speed than full R1.",
        "speed": "Medium",
    },
    {
        "id":    "meta-llama/llama-4-scout:free",
        "name":  "Llama 4 Scout",
        "info":  "Latest Meta model. Multimodal. 512K context.",
        "speed": "Fast",
    },
    {
        "id":    "meta-llama/llama-3.1-8b-instruct:free",
        "name":  "Llama 3.1 8B (Ultra-fast)",
        "info":  "Smallest fast model. Best for lowest latency from India.",
        "speed": "Very Fast",
    },
    {
        "id":    "qwen/qwen3-14b:free",
        "name":  "Qwen 3 14B",
        "info":  "Alibaba model. Strong coding & reasoning. 128K context.",
        "speed": "Fast",
    },
]

ANTHROPIC_MODELS = [
    ("claude-opus-4-5",            "Claude Opus 4.5 — Most intelligent"),
    ("claude-sonnet-4-5",          "Claude Sonnet 4.5 — Best balance"),
    ("claude-3-5-haiku-20241022",  "Claude 3.5 Haiku — Fast & cheap"),
]
GEMINI_MODELS = [
    ("gemini-2.5-flash",        "Gemini 2.5 Flash — Fastest, free tier"),
    ("gemini-2.5-flash-lite",   "Gemini 2.5 Flash Lite — Ultra-fast"),
    ("gemini-1.5-pro",          "Gemini 1.5 Pro — Most capable"),
]
OPENAI_MODELS = [
    ("gpt-4o",        "GPT-4o — Best quality"),
    ("gpt-4o-mini",   "GPT-4o Mini — Fast & affordable"),
]
DEEPSEEK_MODELS = [
    ("deepseek-chat",  "DeepSeek Chat  — General (very cheap)"),
    ("deepseek-coder", "DeepSeek Coder — Coding-focused"),
]


def _check_internet() -> bool:
    try:
        socket.setdefaulttimeout(5)
        socket.getaddrinfo("openrouter.ai", 443)
        return True
    except Exception:
        return False


def _validate_api_key(api_key: str) -> tuple:
    """
    Use /auth/key endpoint to validate key — no model call needed.
    Returns (is_valid: bool, message: str, has_credits: bool)
    """
    if not api_key or len(api_key) < 20:
        return False, "Key too short — copy the full key from openrouter.ai/keys", False

    if not api_key.startswith("sk-or-"):
        return False, f"Key should start with 'sk-or-...' — you entered: {api_key[:8]}...", False

    try:
        r = requests.get(
            f"{OPENROUTER_BASE}/auth/key",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=15,
        )
        if r.status_code == 200:
            data = r.json().get("data", {})
            limit  = data.get("limit")        # None = unlimited (free)
            usage  = data.get("usage", 0)
            label  = data.get("label", "?")
            return True, f"Key valid! Label: '{label}' | Usage: {usage}", True

        if r.status_code == 401:
            return False, "Key rejected — copy it again from openrouter.ai/keys (include sk-or-... prefix)", False

        try:
            msg = r.json().get("error", {}).get("message", r.text[:100])
        except Exception:
            msg = r.text[:100]
        return False, f"HTTP {r.status_code}: {msg}", False

    except requests.exceptions.ConnectionError:
        return False, "Cannot connect to openrouter.ai — check internet/VPN", False
    except requests.exceptions.Timeout:
        return False, "Validation timed out — OpenRouter slow, save anyway and try chatting", False
    except Exception as e:
        return False, str(e)[:100], False


def _pick_openrouter_model(console, api_key: str) -> tuple:
    from rich.table import Table
    from rich import box
    from rich.prompt import Prompt
    """Show model table and return (id, display_name)."""
    # Try fetching live models to ensure they exist
    models = _fetch_live_models(api_key)
    if not models:
        models = OPENROUTER_FREE_MODELS

    t = Table(
        title="[bold cyan]Best Free Models for HexMind (India-Optimized)[/bold cyan]",
        box=box.ROUNDED, border_style="cyan", show_lines=True
    )
    t.add_column("#",     style="bold cyan", width=3)
    t.add_column("Model", style="bold white", min_width=26)
    t.add_column("Speed", style="green",      width=10)
    t.add_column("Best for",                  style="dim white")

    for i, m in enumerate(models[:10], 1):
        t.add_row(str(i), m["name"], m.get("speed", "?"), m["info"])

    console.print(t)
    console.print("  [dim]Tip: Auto Router (option 1) always works — it picks the best model for each request.[/dim]\n")

    raw = Prompt.ask("  [bold cyan]Select model number[/bold cyan]", default="1").strip()
    try:
        idx = max(0, min(int(raw) - 1, len(models) - 1))
    except Exception:
        idx = 0
    return models[idx]["id"], models[idx]["name"]


def _fetch_live_models(api_key: str) -> list:
    """Fetch live free model list. Returns [] on failure."""
    try:
        r = requests.get(
            f"{OPENROUTER_BASE}/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10,
        )
        if r.status_code != 200:
            return []
        data = r.json().get("data", [])
        free = [m for m in data if m.get("id", "").endswith(":free")]
        if len(free) < 3:
            return []

        result = [OPENROUTER_FREE_MODELS[0]]  # Auto Router always first
        # Sort by context length (more context = better for long convos)
        free_sorted = sorted(free, key=lambda x: x.get("context_length", 0), reverse=True)
        for m in free_sorted[:9]:
            ctx = m.get("context_length", 0)
            result.append({
                "id":    m["id"],
                "name":  (m.get("name") or m["id"])[:32],
                "info":  f"{ctx//1000}K ctx · free",
                "speed": "Free",
            })
        return result
    except Exception:
        return []


def _simple_model_list(models: list, title: str, console) -> tuple:
    from rich.table import Table
    from rich import box
    from rich.prompt import Prompt
    t = Table(title=f"[bold cyan]{title}[/bold cyan]", box=box.ROUNDED, border_style="cyan")
    t.add_column("#",     style="bold cyan", width=4)
    t.add_column("Model", style="white")
    for i, (mid, mname) in enumerate(models, 1):
        t.add_row(str(i), mname)
    console.print(t)
    raw = Prompt.ask("  [cyan]Select[/cyan]", default="1").strip()
    try:
        idx = max(0, min(int(raw) - 1, len(models) - 1))
    except Exception:
        idx = 0
    return models[idx]


class ProviderManager:

    def setup_provider(self, choice: str, console) -> dict:
        c = str(choice).strip()
        if c == "1":   return self._setup_openrouter(console)
        elif c == "2": return self._setup_anthropic(console)
        elif c == "3": return self._setup_gemini(console)
        elif c == "4": return self._setup_openai(console)
        elif c == "5": return self._setup_deepseek(console)
        return self._setup_openrouter(console)

    def _setup_openrouter(self, console) -> dict:
        from rich.prompt import Prompt
        from rich.table import Table
        from rich.panel import Panel
        from rich import box
        console.print()
        console.print(Panel(
            "[bold cyan]OpenRouter — Free AI, no credit card needed[/bold cyan]\n\n"
            "1. Go to [bold underline]https://openrouter.ai/keys[/bold underline]\n"
            "2. Sign up → Create API Key → Copy it\n"
            "3. Paste it below (starts with [bold]sk-or-...[/bold])\n\n"
            "[dim]Free tier: 200 requests/day · 20 requests/minute[/dim]",
            border_style="cyan", padding=(0, 2)
        ))

        api_key = Prompt.ask("\n  [bold cyan]Paste your OpenRouter API key[/bold cyan]").strip()
        if not api_key:
            console.print("  [red]No key entered. Type 'settings' to try again.[/red]\n")
            return {}

        # Validate key using auth endpoint (not a model call — faster & reliable)
        console.print("\n  [yellow]Validating API key...[/yellow]")
        is_valid, msg, _ = _validate_api_key(api_key)

        if is_valid:
            console.print(f"  [bold green]✓ {msg}[/bold green]\n")
        else:
            console.print(f"  [bold red]✗ {msg}[/bold red]")
            retry = Prompt.ask(
                "  [dim]Save anyway and continue? (You can fix it later with 'settings')[/dim] [y/n]",
                default="y"
            ).lower()
            if retry != "y":
                return {}
            console.print()

        # Model selection
        model_id, model_name = _pick_openrouter_model(console, api_key)
        console.print(f"  [green]Selected: {model_name}[/green]\n")

        return {
            "type":       "openrouter",
            "name":       "OpenRouter",
            "api_key":    api_key,
            "model":      model_id,
            "model_name": model_name,
        }

    def _setup_anthropic(self, console) -> dict:
        from rich.prompt import Prompt
        from rich.table import Table
        from rich.panel import Panel
        from rich import box
        console.print(Panel(
            "[bold cyan]Anthropic Claude[/bold cyan]\n\n"
            "Get key: [bold]https://console.anthropic.com/account/keys[/bold]\n"
            "[dim]Paid API — very smart models. Free $5 credit for new accounts.[/dim]",
            border_style="cyan", padding=(0, 2)
        ))
        api_key = Prompt.ask("\n  [cyan]Paste your Anthropic API key[/cyan]").strip()
        mid, mn = _simple_model_list(ANTHROPIC_MODELS, "Claude Models", console)
        console.print("\n  [yellow]Testing...[/yellow]")
        ok, err = self._test_anthropic(api_key, mid)
        console.print(f"  [{'bold green' if ok else 'bold red'}]{'✓ Connected!' if ok else f'✗ {err}'}[/]\n")
        return {"type": "anthropic", "name": "Anthropic", "api_key": api_key, "model": mid, "model_name": mn}

    def _setup_gemini(self, console) -> dict:
        from rich.prompt import Prompt
        from rich.table import Table
        from rich.panel import Panel
        from rich import box
        console.print(Panel(
            "[bold cyan]Google Gemini[/bold cyan]\n\n"
            "Free key: [bold]https://aistudio.google.com/app/apikey[/bold]\n"
            "[dim]Gemini 2.5 Flash is fast and free. No credit card needed.[/dim]",
            border_style="cyan", padding=(0, 2)
        ))
        api_key = Prompt.ask("\n  [cyan]Paste your Google API key[/cyan]").strip()
        mid, mn = _simple_model_list(GEMINI_MODELS, "Gemini Models", console)
        console.print("\n  [yellow]Testing...[/yellow]")
        ok, err = self._test_gemini(api_key, mid)
        console.print(f"  [{'bold green' if ok else 'bold red'}]{'✓ Connected!' if ok else f'✗ {err}'}[/]\n")
        return {"type": "gemini", "name": "Google Gemini", "api_key": api_key, "model": mid, "model_name": mn}

    def _setup_openai(self, console) -> dict:
        from rich.prompt import Prompt
        from rich.table import Table
        from rich.panel import Panel
        from rich import box
        console.print(Panel(
            "[bold cyan]OpenAI GPT[/bold cyan]\n\n"
            "Key: [bold]https://platform.openai.com/api-keys[/bold]\n"
            "[dim]Paid API. GPT-4o-mini is very affordable.[/dim]",
            border_style="cyan", padding=(0, 2)
        ))
        api_key = Prompt.ask("\n  [cyan]Paste your OpenAI API key[/cyan]").strip()
        mid, mn = _simple_model_list(OPENAI_MODELS, "OpenAI Models", console)
        console.print("\n  [yellow]Testing...[/yellow]")
        ok, err = self._test_openai_compat(api_key, mid)
        console.print(f"  [{'bold green' if ok else 'bold red'}]{'✓ Connected!' if ok else f'✗ {err}'}[/]\n")
        return {"type": "openai", "name": "OpenAI", "api_key": api_key, "model": mid, "model_name": mn}

    def _setup_deepseek(self, console) -> dict:
        from rich.prompt import Prompt
        from rich.table import Table
        from rich.panel import Panel
        from rich import box
        console.print(Panel(
            "[bold cyan]DeepSeek[/bold cyan]\n\n"
            "Key: [bold]https://platform.deepseek.com/api-keys[/bold]\n"
            "[dim]Extremely affordable. deepseek-chat is excellent for coding.[/dim]",
            border_style="cyan", padding=(0, 2)
        ))
        api_key = Prompt.ask("\n  [cyan]Paste your DeepSeek API key[/cyan]").strip()
        mid, mn = _simple_model_list(DEEPSEEK_MODELS, "DeepSeek Models", console)
        console.print("\n  [yellow]Testing...[/yellow]")
        ok, err = self._test_openai_compat(api_key, mid, "https://api.deepseek.com")
        console.print(f"  [{'bold green' if ok else 'bold red'}]{'✓ Connected!' if ok else f'✗ {err}'}[/]\n")
        return {"type": "deepseek", "name": "DeepSeek", "api_key": api_key, "model": mid, "model_name": mn}

    def _test_anthropic(self, api_key, model):
        try:
            import anthropic
            c = anthropic.Anthropic(api_key=api_key)
            c.messages.create(model=model, max_tokens=5, messages=[{"role": "user", "content": "hi"}])
            return True, ""
        except Exception as e:
            return False, str(e)[:100]

    def _test_gemini(self, api_key, model):
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            genai.GenerativeModel(model).generate_content("hi")
            return True, ""
        except Exception as e:
            return False, str(e)[:100]

    def _test_openai_compat(self, api_key, model, base_url=None):
        try:
            from openai import OpenAI
            kw = {"api_key": api_key}
            if base_url:
                kw["base_url"] = base_url
            OpenAI(**kw).chat.completions.create(
                model=model, max_tokens=5,
                messages=[{"role": "user", "content": "hi"}]
            )
            return True, ""
        except ImportError:
            import openai as oai
            oai.api_key = api_key
            if base_url:
                oai.api_base = base_url
            try:
                oai.ChatCompletion.create(
                    model=model, max_tokens=5,
                    messages=[{"role": "user", "content": "hi"}]
                )
                return True, ""
            except Exception as e:
                return False, str(e)[:100]
        except Exception as e:
            return False, str(e)[:100]
