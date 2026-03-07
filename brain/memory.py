"""
HexMind Memory & Intelligence System v3.0 (LightMem-Inspired)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
GOD MODE Memory System — Inspired by LightMem (ICLR 2026) + lagent memory-as-state

Features:
  - Persistent conversation history + daily journals
  - Semantic topic extraction + frequency tracking  
  - Explicit user memories ("remember X" → recall later)
  - Emotion/mood detection from user messages
  - Conversation summarization for long-term storage
  - Correction tracking (learns from mistakes)
  - Cross-session context persistence
  - User personality profile building

All data stored in ~/.hexmind/memory/
"""

import json
import os
import re
from pathlib import Path
from datetime import datetime, timedelta
from collections import Counter

MEMORY_DIR = Path.home() / ".hexmind" / "memory"
MEMORY_DIR.mkdir(parents=True, exist_ok=True)

PREFS_FILE       = MEMORY_DIR / "user_prefs.json"
PATTERNS_FILE    = MEMORY_DIR / "learned_patterns.json"
HISTORY_FILE     = MEMORY_DIR / "chat_history.jsonl"
DAILY_FILE       = MEMORY_DIR / f"daily_{datetime.now().strftime('%Y%m%d')}.jsonl"
MEMORIES_FILE    = MEMORY_DIR / "explicit_memories.json"
CORRECTIONS_FILE = MEMORY_DIR / "corrections.json"
MOOD_FILE        = MEMORY_DIR / "mood_history.json"
SUMMARIES_FILE   = MEMORY_DIR / "conversation_summaries.json"

# AutoAgent Partitions
CODE_MEM_FILE    = MEMORY_DIR / "code_memory.json"
TOOL_MEM_FILE    = MEMORY_DIR / "tool_memory.json"
PAPER_MEM_FILE   = MEMORY_DIR / "paper_memory.json"
RAG_MEM_FILE     = MEMORY_DIR / "rag_memory.json"


def _load_json(path: Path, default):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def _save_json(path: Path, data):
    try:
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
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
    GOD MODE Memory System.
    Tracks everything: topics, moods, corrections, explicit memories,
    daily summaries, and builds a user personality profile over time.
    """

    def __init__(self):
        self.prefs    = _load_json(PREFS_FILE, {})
        self.patterns = _load_json(PATTERNS_FILE, {
            "topic_frequency": {},
            "successful_answers": [],
            "tool_usage": {},
            "agent_commands": {},
            "time_of_day": {},
            "session_count": 0,
            "total_messages": 0,
            "first_seen": datetime.now().isoformat(),
            "last_seen": datetime.now().isoformat(),
        })
        # Explicit memories: user says "remember X" → stored here
        self.explicit_memories = _load_json(MEMORIES_FILE, {})
        # Corrections: tracks when user corrects the AI
        self.corrections = _load_json(CORRECTIONS_FILE, [])
        # Mood history: detected moods over time
        self.mood_history = _load_json(MOOD_FILE, [])
        # Conversation summaries
        self.summaries = _load_json(SUMMARIES_FILE, [])
        
        # AutoAgent Partitions
        self.code_memory  = _load_json(CODE_MEM_FILE, [])
        self.tool_memory  = _load_json(TOOL_MEM_FILE, [])
        self.paper_memory = _load_json(PAPER_MEM_FILE, [])
        self.rag_memory   = _load_json(RAG_MEM_FILE, [])
        
        # Current session buffer (for summarization)
        self._session_buffer = []
        self._current_mood = "neutral"

    # ── Session tracking ──────────────────────────────────────────────────────
    def start_session(self):
        self.patterns["session_count"] = self.patterns.get("session_count", 0) + 1
        self.patterns["last_seen"] = datetime.now().isoformat()
        hour = str(datetime.now().hour)
        self.patterns["time_of_day"][hour] = self.patterns["time_of_day"].get(hour, 0) + 1
        self._session_buffer = []
        self._save()

    def end_session(self):
        # Summarize session before ending
        if len(self._session_buffer) >= 3:
            self._summarize_session()
        self._save()

    # ── Message learning (lagent memory-as-state pattern) ─────────────────────
    def record_exchange(self, user_msg: str, assistant_reply: str, mode: str = ""):
        """Record every message — the core of memory-as-state."""
        if not user_msg.strip():
            return
            
        self.patterns["total_messages"] = self.patterns.get("total_messages", 0) + 1

        # Extract topics
        topics = self._extract_topics(user_msg)
        for t in topics:
            self.patterns["topic_frequency"][t] = \
                self.patterns["topic_frequency"].get(t, 0) + 1

        # Detect mood
        mood = self._detect_mood(user_msg)
        self._current_mood = mood

        # Check for explicit memory commands
        self._check_memory_command(user_msg)

        # Check for corrections
        self._check_correction(user_msg)

        # Build entry
        entry = {
            "ts":     datetime.now().isoformat(),
            "user":   user_msg[:500],
            "reply":  assistant_reply[:1000],
            "mode":   mode,
            "topics": topics,
            "mood":   mood,
        }
        _append_jsonl(HISTORY_FILE, entry)
        _append_jsonl(DAILY_FILE, entry)

        # Add to session buffer for summarization
        self._session_buffer.append(entry)

        # Record mood
        if mood != "neutral":
            self.mood_history.append({
                "ts": datetime.now().isoformat(),
                "mood": mood,
                "trigger": user_msg[:100]
            })
            # Keep only last 100 mood entries
            self.mood_history = self.mood_history[-100:]
            _save_json(MOOD_FILE, self.mood_history)

        # Auto-summarize every 20 messages
        if len(self._session_buffer) >= 20:
            self._summarize_session()
            self._session_buffer = []

        # Rotate history if too large
        try:
            if HISTORY_FILE.stat().st_size > 10_000_000:  # 10MB
                lines = HISTORY_FILE.read_text(encoding="utf-8").splitlines()
                HISTORY_FILE.write_text("\n".join(lines[-3000:]) + "\n", encoding="utf-8")
        except Exception:
            pass

        self._save()

    def record_agent_command(self, command: str, success: bool):
        key = command.split()[0] if command else "?"
        self.patterns["agent_commands"][key] = \
            self.patterns["agent_commands"].get(key, 0) + 1

    def record_tool_use(self, tool_name: str):
        self.patterns["tool_usage"][tool_name] = \
            self.patterns["tool_usage"].get(tool_name, 0) + 1

    # ══════════════════════════════════════════════════════════════════════════
    # AUTOAGENT SPECIALIZED MEMORIES
    # ══════════════════════════════════════════════════════════════════════════
    def add_code_memory(self, snippet_name: str, code: str, desc: str):
        self.code_memory.append({
            "name": snippet_name, "code": code, "desc": desc, "ts": datetime.now().isoformat()
        })
        _save_json(CODE_MEM_FILE, self.code_memory)

    def add_tool_memory(self, tool_name: str, usage: str, success: bool):
        self.tool_memory.append({
            "name": tool_name, "usage": usage, "success": success, "ts": datetime.now().isoformat()
        })
        _save_json(TOOL_MEM_FILE, self.tool_memory)

    def add_paper_memory(self, title: str, summary: str, url: str = ""):
        self.paper_memory.append({
            "title": title, "summary": summary, "url": url, "ts": datetime.now().isoformat()
        })
        _save_json(PAPER_MEM_FILE, self.paper_memory)

    def add_rag_memory(self, doc_id: str, content: str):
        self.rag_memory.append({
            "doc_id": doc_id, "content": content, "ts": datetime.now().isoformat()
        })
        _save_json(RAG_MEM_FILE, self.rag_memory)

    # ══════════════════════════════════════════════════════════════════════════
    # EXPLICIT MEMORY — "remember X" / "recall Y"
    # ══════════════════════════════════════════════════════════════════════════
    def save_memory(self, key: str, value: str):
        """Save an explicit memory. User says 'remember my favorite color is blue'."""
        self.explicit_memories[key.lower().strip()] = {
            "value": value,
            "saved_at": datetime.now().isoformat(),
            "recall_count": 0
        }
        _save_json(MEMORIES_FILE, self.explicit_memories)

    def recall_memory(self, query: str) -> str:
        """Recall explicit memories by keyword match (semantic-lite)."""
        query_lower = query.lower().strip()
        matches = []

        for key, mem in self.explicit_memories.items():
            # Direct match
            if query_lower in key or key in query_lower:
                mem["recall_count"] = mem.get("recall_count", 0) + 1
                matches.append(f"• {key}: {mem['value']}")
            # Word overlap match
            else:
                q_words = set(query_lower.split())
                k_words = set(key.split())
                overlap = q_words & k_words
                if len(overlap) >= 1 and len(overlap) / max(len(q_words), 1) > 0.3:
                    matches.append(f"• {key}: {mem['value']}")

        if matches:
            _save_json(MEMORIES_FILE, self.explicit_memories)
            return "\n".join(matches)
        return ""

    def get_all_memories(self) -> dict:
        """Get all explicit memories for display."""
        return self.explicit_memories

    def _check_memory_command(self, text: str):
        """Auto-detect 'remember X' patterns in user messages."""
        text_lower = text.lower().strip()
        
        remember_patterns = [
            r"remember\s+(?:that\s+)?(?:my\s+)?(.+?)(?:\s+is\s+|\s*[:=]\s*)(.+)",
            r"(?:my|i)\s+(?:like|love|prefer|hate|use|have|am|work|live)\s+(.+)",
        ]
        
        # Pattern 1: "remember my X is Y"
        match = re.match(r"remember\s+(?:that\s+)?(?:my\s+)?(.+?)(?:\s+is\s+|\s*[:=]\s*)(.+)", text_lower)
        if match:
            key = match.group(1).strip()
            value = match.group(2).strip()
            self.save_memory(key, value)
            return

        # Pattern 2: "remember <statement>"
        match = re.match(r"remember\s+(?:that\s+)?(.{10,})", text_lower)
        if match:
            statement = match.group(1).strip()
            self.save_memory(statement, statement)

    # ══════════════════════════════════════════════════════════════════════════
    # CORRECTION TRACKING — Learn from mistakes
    # ══════════════════════════════════════════════════════════════════════════
    def record_correction(self, original: str, corrected: str):
        """Track when user corrects the AI."""
        self.corrections.append({
            "ts": datetime.now().isoformat(),
            "original": original[:300],
            "corrected": corrected[:300],
        })
        # Keep last 50 corrections
        self.corrections = self.corrections[-50:]
        _save_json(CORRECTIONS_FILE, self.corrections)

    def get_correction_context(self) -> str:
        """Build context from recent corrections for prompt injection."""
        if not self.corrections:
            return ""
        recent = self.corrections[-5:]
        parts = ["PAST CORRECTIONS (avoid repeating these mistakes):"]
        for c in recent:
            parts.append(f"- Wrong: {c['original'][:80]} → Right: {c['corrected'][:80]}")
        return "\n".join(parts)

    def _check_correction(self, text: str):
        """Detect correction patterns like 'no, I meant X' or 'that's wrong'."""
        correction_phrases = [
            "no, ", "no i meant", "that's wrong", "that is wrong",
            "actually,", "i said ", "not ", "incorrect", "you're wrong",
            "thats not", "that's not", "wrong answer", "fix that",
        ]
        text_lower = text.lower().strip()
        if any(text_lower.startswith(p) or p in text_lower[:50] for p in correction_phrases):
            # Record the correction attempt
            recent = self.get_recent_context(1)
            if recent:
                last = recent[0]
                self.record_correction(
                    original=last.get("reply", "")[:200],
                    corrected=text[:200]
                )

    # ══════════════════════════════════════════════════════════════════════════
    # MOOD/EMOTION DETECTION
    # ══════════════════════════════════════════════════════════════════════════
    def _detect_mood(self, text: str) -> str:
        """Simple keyword-based mood detection."""
        text_lower = text.lower()
        
        mood_map = {
            "frustrated": ["fuck", "shit", "damn", "stupid", "hate", "annoying",
                          "broken", "not working", "doesn't work", "failed", "useless"],
            "excited": ["awesome", "amazing", "perfect", "love it", "great", "excellent",
                       "cool", "wow", "nice", "brilliant", "superb", "🔥", "💪"],
            "curious": ["how", "why", "what", "explain", "tell me", "show me",
                       "can you", "is it possible", "?"],
            "grateful": ["thanks", "thank you", "appreciate", "helpful", "saved me",
                        "perfect", "exactly what"],
            "confused": ["confused", "don't understand", "what do you mean",
                        "unclear", "lost", "help me understand"],
            "tired": ["tired", "exhausted", "sleepy", "boring", "bored", "long day"],
            "happy": ["haha", "lol", "😂", "🤣", "funny", "happy", "good",
                     "hi", "hello", "hey", "namaste", "salam"],
        }
        
        for mood, keywords in mood_map.items():
            if any(kw in text_lower for kw in keywords):
                return mood
        return "neutral"

    def get_current_mood(self) -> str:
        return self._current_mood

    def get_mood_summary(self) -> str:
        """Get recent mood trends."""
        if not self.mood_history:
            return "No mood data yet."
        
        recent = self.mood_history[-20:]
        mood_counts = Counter(m["mood"] for m in recent)
        dominant = mood_counts.most_common(1)[0][0] if mood_counts else "neutral"
        return f"Recent mood trend: {dominant} | Distribution: {dict(mood_counts)}"

    # ══════════════════════════════════════════════════════════════════════════
    # CONVERSATION SUMMARIZATION (LightMem-inspired)
    # ══════════════════════════════════════════════════════════════════════════
    def _summarize_session(self):
        """Create a compressed summary of the current session buffer."""
        if not self._session_buffer:
            return
            
        topics_in_session = set()
        moods_in_session = set()
        msg_count = len(self._session_buffer)
        
        for entry in self._session_buffer:
            topics_in_session.update(entry.get("topics", []))
            mood = entry.get("mood", "neutral")
            if mood != "neutral":
                moods_in_session.add(mood)
        
        summary = {
            "date": datetime.now().isoformat(),
            "message_count": msg_count,
            "topics": list(topics_in_session),
            "moods": list(moods_in_session),
            "first_msg": self._session_buffer[0].get("user", "")[:100],
            "last_msg": self._session_buffer[-1].get("user", "")[:100],
        }
        
        self.summaries.append(summary)
        # Keep last 100 summaries
        self.summaries = self.summaries[-100:]
        _save_json(SUMMARIES_FILE, self.summaries)

    # ══════════════════════════════════════════════════════════════════════════
    # CONTEXT BUILDING — For AI prompt injection
    # ══════════════════════════════════════════════════════════════════════════
    def get_context_for_prompt(self, current_topic: str = "") -> str:
        """
        Build context string for system prompt injection.
        This is what makes HexMind truly learn and personalize.
        """
        parts = []

        # Top interests
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

        # Preferred tools
        top_tools = sorted(
            self.patterns.get("tool_usage", {}).items(),
            key=lambda x: x[1], reverse=True
        )[:3]
        if top_tools:
            tool_str = ", ".join(t for t, _ in top_tools)
            parts.append(f"Frequently uses: {tool_str}")

        # AutoAgent: Inject recent code snippets
        if self.code_memory:
            recent_code = self.code_memory[-2:]
            code_parts = [f"[{c['name']}]: {c['desc']}" for c in recent_code]
            parts.append(f"Recent Code Context: " + " | ".join(code_parts))
            
        # AutoAgent: Inject recent tool usages
        if self.tool_memory:
            recent_tools = [t for t in self.tool_memory[-3:] if t.get('success')]
            tool_parts = [f"Used {t['name']}" for t in recent_tools]
            if tool_parts: parts.append(f"Recent Successful Tools: " + ", ".join(tool_parts))

        # User preferences
        prefs = self.prefs
        if prefs.get("prefers_short_answers"):
            parts.append("Prefers concise answers")
        if prefs.get("prefers_code_examples"):
            parts.append("Always wants code examples")

        # Current mood context
        if self._current_mood != "neutral":
            mood_str = {
                "frustrated": "User seems frustrated — be patient and empathetic",
                "excited": "User is excited — match their energy",
                "confused": "User seems confused — explain step by step",
                "grateful": "User is appreciative — acknowledge warmly",
                "tired": "User seems tired — keep responses brief and friendly",
                "happy": "User is in a good mood — be friendly and warm",
                "curious": "User is in learning mode — be thorough",
            }.get(self._current_mood, "")
            if mood_str:
                parts.append(mood_str)

        # Explicit memories
        if self.explicit_memories:
            mem_items = list(self.explicit_memories.items())[:5]
            mem_str = "; ".join(f"{k}: {v['value']}" for k, v in mem_items)
            parts.append(f"Remembered facts: {mem_str}")

        # Recent corrections
        correction_ctx = self.get_correction_context()
        if correction_ctx:
            parts.append(correction_ctx)

        # Active time patterns
        time_data = self.patterns.get("time_of_day", {})
        if time_data:
            peak_hour = max(time_data, key=time_data.get)
            parts.append(f"Most active hour: {peak_hour}:00")

        return "\n".join(parts) if parts else ""

    def get_user_personality_context(self) -> str:
        """Build a personality summary for emotionally-aware interactions."""
        parts = []
        
        # Determine user type from topics
        topics = self.patterns.get("topic_frequency", {})
        if topics:
            top = sorted(topics.items(), key=lambda x: x[1], reverse=True)[:3]
            focus = [t[0] for t in top]
            parts.append(f"Primary focus areas: {', '.join(focus)}")

        # Activity level
        sessions = self.patterns.get("session_count", 0)
        if sessions > 20:
            parts.append("Power user — deeply invested in the platform")
        elif sessions > 5:
            parts.append("Regular user — building expertise")
        elif sessions > 0:
            parts.append("New user — provide welcoming, supportive guidance")

        # Mood trends
        if self.mood_history:
            recent_moods = [m["mood"] for m in self.mood_history[-10:]]
            mood_counter = Counter(recent_moods)
            dominant = mood_counter.most_common(1)
            if dominant:
                parts.append(f"Recent mood trend: {dominant[0][0]}")

        return "\n".join(parts) if parts else ""

    def get_recent_context(self, n: int = 5) -> list:
        """Get last N exchanges for context injection."""
        try:
            lines = HISTORY_FILE.read_text(encoding="utf-8").strip().splitlines()
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
        if message_len < 100 and follow_up_positive:
            self.prefs["prefers_short_answers"] = True
        if message_len > 500 and follow_up_positive:
            self.prefs["prefers_detailed_answers"] = True
        self._save()

    def set_pref(self, key: str, value):
        self.prefs[key] = value
        self._save()

    # ── Stats ─────────────────────────────────────────────────────────────────
    def get_top_topics(self, n: int = 10) -> list:
        freq = self.patterns.get("topic_frequency", {})
        return sorted(freq.items(), key=lambda x: x[1], reverse=True)[:n]

    def get_stats(self) -> dict:
        return {
            "sessions":       self.patterns.get("session_count", 0),
            "messages":       self.patterns.get("total_messages", 0),
            "top_topics":     self.get_top_topics(5),
            "first_seen":     self.patterns.get("first_seen", "?"),
            "last_seen":      self.patterns.get("last_seen", "?"),
            "tools_used":     self.patterns.get("tool_usage", {}),
            "commands_run":   self.patterns.get("agent_commands", {}),
            "explicit_memories": len(self.explicit_memories),
            "corrections":    len(self.corrections),
            "mood":           self._current_mood,
            "summaries":      len(self.summaries),
        }

    # ── Topic extraction ──────────────────────────────────────────────────────
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
            "ai":             ["machine learning", "deep learning", "neural", "llm", "gpt", "model"],
            "voice":          ["voice", "speech", "microphone", "speak"],
            "learning":       ["learn", "study", "tutorial", "course", "understand"],
        }
        found = []
        for topic, keywords in topic_map.items():
            if any(kw in text_lower for kw in keywords):
                found.append(topic)
        return found

    def _save(self):
        _save_json(PREFS_FILE, self.prefs)
        _save_json(PATTERNS_FILE, self.patterns)
