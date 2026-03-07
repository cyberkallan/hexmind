"""
HexMind Memory & Self-Learning System
- Stores conversation history, learned patterns, user preferences
- Learns from API responses — what worked, what didn't
- Builds a personal knowledge graph per user
- Improves response quality over time using accumulated context
- All data stored in ~/.hexmind/memory/
"""

import json
import os
import hashlib
import re
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict, Counter

MEMORY_DIR = Path.home() / ".hexmind" / "memory"
MEMORY_DIR.mkdir(parents=True, exist_ok=True)

PREFS_FILE      = MEMORY_DIR / "user_prefs.json"
PATTERNS_FILE   = MEMORY_DIR / "learned_patterns.json"
HISTORY_FILE    = MEMORY_DIR / "chat_history.jsonl"
SKILLS_FILE     = MEMORY_DIR / "skill_index.json"
DAILY_FILE      = MEMORY_DIR / f"daily_{datetime.now().strftime('%Y%m%d')}.jsonl"


def _load_json(path: Path, default):
    try:
        if path.exists():
            return json.loads(path.read_text())
    except Exception:
        pass
    return default


def _save_json(path: Path, data):
    try:
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    except Exception:
        pass


def _append_jsonl(path: Path, obj: dict):
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")
    except Exception:
        pass


class UserMemory:
    """
    Persistent memory that learns from every conversation.
    Tracks: topics, good answers, user patterns, tool preferences.
    """

    def __init__(self):
        self.prefs    = _load_json(PREFS_FILE,    {})
        self.patterns = _load_json(PATTERNS_FILE, {
            "topic_frequency": {},
            "successful_answers": [],   # answers that got follow-up positive signals
            "tool_usage": {},           # which tools are used most
            "agent_commands": {},       # which agent commands run most
            "time_of_day": {},          # when user is most active
            "session_count": 0,
            "total_messages": 0,
            "first_seen": datetime.now().isoformat(),
            "last_seen": datetime.now().isoformat(),
        })

    # ── Session tracking ──────────────────────────────────────────────────────
    def start_session(self):
        self.patterns["session_count"] = self.patterns.get("session_count", 0) + 1
        self.patterns["last_seen"] = datetime.now().isoformat()
        hour = str(datetime.now().hour)
        self.patterns["time_of_day"][hour] = self.patterns["time_of_day"].get(hour, 0) + 1
        self._save()

    def end_session(self):
        self._save()

    # ── Message learning ──────────────────────────────────────────────────────
    def record_exchange(self, user_msg: str, assistant_reply: str, mode: str = ""):
        """Record every message for learning."""
        self.patterns["total_messages"] = self.patterns.get("total_messages", 0) + 1

        # Extract topics from user message
        topics = self._extract_topics(user_msg)
        for t in topics:
            self.patterns["topic_frequency"][t] = \
                self.patterns["topic_frequency"].get(t, 0) + 1

        # Save to history
        entry = {
            "ts":    datetime.now().isoformat(),
            "user":  user_msg[:500],
            "reply": assistant_reply[:1000],
            "mode":  mode,
            "topics": topics,
        }
        _append_jsonl(HISTORY_FILE, entry)
        _append_jsonl(DAILY_FILE,   entry)

        # Rotate history file if too large (keep last 5000 lines)
        try:
            if HISTORY_FILE.stat().st_size > 10_000_000:  # 10MB
                lines = HISTORY_FILE.read_text().splitlines()
                HISTORY_FILE.write_text("\n".join(lines[-3000:]) + "\n")
        except Exception:
            pass

        self._save()

    def record_agent_command(self, command: str, success: bool):
        """Track which agent commands the user runs."""
        key = command.split()[0] if command else "?"
        self.patterns["agent_commands"][key] = \
            self.patterns["agent_commands"].get(key, 0) + 1

    def record_tool_use(self, tool_name: str):
        self.patterns["tool_usage"][tool_name] = \
            self.patterns["tool_usage"].get(tool_name, 0) + 1

    # ── Context building ───────────────────────────────────────────────────────
    def get_context_for_prompt(self, current_topic: str = "") -> str:
        """
        Build a context string to inject into the system prompt.
        This is what makes HexMind 'learn' — it injects user patterns into every request.
        """
        parts = []

        # Top 5 topics this user cares about
        top_topics = sorted(
            self.patterns.get("topic_frequency", {}).items(),
            key=lambda x: x[1], reverse=True
        )[:5]
        if top_topics:
            topic_str = ", ".join(t for t, _ in top_topics)
            parts.append(f"User's main interests: {topic_str}")

        # Session stats
        sc = self.patterns.get("session_count", 0)
        tm = self.patterns.get("total_messages", 0)
        if sc > 1:
            parts.append(f"Returning user: {sc} sessions, {tm} total messages")

        # Most used tools
        top_tools = sorted(
            self.patterns.get("tool_usage", {}).items(),
            key=lambda x: x[1], reverse=True
        )[:3]
        if top_tools:
            tool_str = ", ".join(t for t, _ in top_tools)
            parts.append(f"Frequently uses: {tool_str}")

        # Preferred time
        prefs = self.prefs
        if prefs.get("prefers_short_answers"):
            parts.append("Prefers concise answers")
        if prefs.get("prefers_code_examples"):
            parts.append("Always wants code examples")

        return "\n".join(parts) if parts else ""

    def get_recent_context(self, n: int = 5) -> list:
        """Get last N exchanges for context injection."""
        try:
            lines = HISTORY_FILE.read_text().strip().splitlines()
            recent = []
            for line in reversed(lines[-50:]):
                try:
                    e = json.loads(line)
                    recent.append(e)
                    if len(recent) >= n:
                        break
                except Exception:
                    continue
            return list(reversed(recent))
        except Exception:
            return []

    def get_expanded_knowledge(self, n: int = 3) -> str:
        """Fetch the latest background-learned knowledge."""
        try:
            learned_dir = MEMORY_DIR / "learned"
            if not learned_dir.exists():
                return ""
            files = list(learned_dir.glob("learned_*.md"))
            if not files:
                return ""
            # Sort by modification time (newest first)
            files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
            knowledge = []
            for f in files[:n]:
                content = f.read_text(encoding="utf-8").strip()
                if content:
                    knowledge.append(content)
            return "\n\n".join(knowledge)
        except Exception:
            return ""

    # ── Preference learning ────────────────────────────────────────────────────
    def learn_from_feedback(self, message_len: int, follow_up_positive: bool):
        """Infer preferences from behavior."""
        if message_len < 100 and follow_up_positive:
            self.prefs["prefers_short_answers"] = True
        if message_len > 500 and follow_up_positive:
            self.prefs["prefers_detailed_answers"] = True
        self._save()

    def set_pref(self, key: str, value):
        self.prefs[key] = value
        self._save()

    # ── Topic stats ───────────────────────────────────────────────────────────
    def get_top_topics(self, n: int = 10) -> list:
        freq = self.patterns.get("topic_frequency", {})
        return sorted(freq.items(), key=lambda x: x[1], reverse=True)[:n]

    def get_stats(self) -> dict:
        return {
            "sessions":      self.patterns.get("session_count", 0),
            "messages":      self.patterns.get("total_messages", 0),
            "top_topics":    self.get_top_topics(5),
            "first_seen":    self.patterns.get("first_seen", "?"),
            "last_seen":     self.patterns.get("last_seen", "?"),
            "tools_used":    self.patterns.get("tool_usage", {}),
            "commands_run":  self.patterns.get("agent_commands", {}),
        }

    # ── Internals ─────────────────────────────────────────────────────────────
    def _extract_topics(self, text: str) -> list:
        text_lower = text.lower()
        topic_map = {
            "nmap":           ["nmap", "port scan", "network scan"],
            "burp":           ["burp", "proxy", "intercept"],
            "sqlmap":         ["sqlmap", "sql injection", "sqli"],
            "metasploit":     ["metasploit", "msfconsole", "meterpreter", "exploit"],
            "hydra":          ["hydra", "brute force", "credential"],
            "gobuster":       ["gobuster", "ffuf", "directory", "fuzz"],
            "privesc_linux":  ["linpeas", "suid", "sudo -l", "linux privesc", "root"],
            "privesc_win":    ["winpeas", "windows privesc", "impersonat"],
            "reverse_shell":  ["reverse shell", "bind shell", "netcat", "nc -lvnp"],
            "recon":          ["subfinder", "amass", "recon", "osint", "subdomain"],
            "xss":            ["xss", "cross site", "alert("],
            "ctf":            ["ctf", "hackthebox", "tryhackme", "picoctf"],
            "python":         ["python", ".py", "script", "automate"],
            "hash":           ["hashcat", "john", "hash", "crack"],
            "web":            ["http", "website", "web app", "endpoint", "api"],
            "network":        ["ping", "traceroute", "ip address", "network"],
            "termux":         ["termux", "android", "phone"],
            "git":            ["git", "github", "repo"],
        }
        found = []
        for topic, keywords in topic_map.items():
            if any(kw in text_lower for kw in keywords):
                found.append(topic)
        return found

    def _save(self):
        _save_json(PREFS_FILE,    self.prefs)
        _save_json(PATTERNS_FILE, self.patterns)
