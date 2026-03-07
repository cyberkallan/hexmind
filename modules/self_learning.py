import threading
import time
import random
import os
from pathlib import Path

LEARNED_DIR = Path.home() / ".hexmind" / "memory" / "learned"

# A list of advanced topics the AI can pick from to learn if there's no chat history
LEARNING_SEED_TOPICS = [
    "Advanced Active Directory Kerberoasting evasion",
    "Bypassing modern Web Application Firewalls (WAF) using chunked encoding",
    "Latest techniques in Process Hollowing on Windows 11",
    "Exploiting GraphQL endpoints with introspection disabled",
    "Zero-click RCE vectors in modern email clients",
    "Techniques for escaping Docker containers using privileged mode",
    "Bypassing EDR hooks using direct syscalls (Hell's Gate)",
    "Exploiting deserialization vulnerabilities in Java Spring Boot",
    "Advanced Server-Side Request Forgery (SSRF) bypasses in AWS",
    "Techniques for bypassing AMSI in PowerShell"
]

class SelfLearningDaemon:
    def __init__(self, engine, console, interval_minutes=20):
        self.engine = engine
        self.console = console
        self.interval = interval_minutes * 60
        self._stop_event = threading.Event()
        self._thread = None
        LEARNED_DIR.mkdir(parents=True, exist_ok=True)

    def start(self):
        if self._thread and self._thread.is_alive():
            return
            
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._learning_loop, daemon=True)
        self._thread.start()
        # Ensure we don't clobber the prompt
        # self.console.print("  [dim]🧠 Background auto-learning initiated...[/dim]")

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=1.0)
            
    def _learning_loop(self):
        # Initial delay so it doesn't trigger exactly on startup when user is doing things
        time.sleep(120) 
        
        while not self._stop_event.is_set():
            self._learn_new_concept()
            
            # Wait for the interval, checking stop event periodically
            for _ in range(self.interval):
                if self._stop_event.is_set():
                    return
                time.sleep(1)
                
    def _learn_new_concept(self):
        # Prune old memories to keep disk size infinitely scalable
        self._prune_memories(max_files=50)
        
        # Decide what to learn. EITHER extract from history OR pick a random seed.
        topic = random.choice(LEARNING_SEED_TOPICS)
        if self.engine.history and len(self.engine.history) > 3:
            # 30% chance to learn deeper about current conversation topic
            if random.random() < 0.3:
                last_messages = " ".join([m["content"] for m in self.engine.history[-3:] if m["role"] == "user"])
                if len(last_messages) > 10:
                    topic = f"Deep dive on the concepts mentioned here: {last_messages[:100]}"
                    
        prompt = f"""You are HexMind, an advanced autonomous hacking AI.
You are currently running in your BACKGROUND SELF-LEARNING loop. The user is not talking to you.
Your objective is to independently research and learn a new concept to store in your long-term memory.

Topic to learn: {topic}

Provide a Highly Compressed Markdown Summary of this topic.
Include:
1. Core mechanics (How it works deeply)
2. Tooling/Commands (Concrete bash/python examples)
3. Exploitation vectors

Keep it under 300 words. Be dense and highly technical.
"""
        
        try:
            # Use offline brain if possible to save API
            if hasattr(self.engine, 'offline_brain') and self.engine.offline_brain.local_llm_ready():
                res = self.engine.offline_brain.respond(prompt)
            else:
                # Fallback to cloud API
                ptype = self.engine.provider.get("type", "openrouter")
                from core.prompts import SYSTEM_PROMPT
                messages = [
                    {"role": "system", "content": SYSTEM_PROMPT["Hacker Mode"]},
                    {"role": "user", "content": prompt}
                ]
                
                if ptype == "openrouter":
                    res = self.engine._chat_openrouter(prompt)
                elif ptype == "anthropic":
                    res = self.engine._chat_anthropic(prompt)
                else:
                    return # Skip if using an unsupported background provider
                    
            if res and len(res) > 50:
                # Save the new knowledge
                fname = f"learned_{int(time.time())}.md"
                (LEARNED_DIR / fname).write_text(f"# Topic: {topic}\n\n{res}", encoding="utf-8")
                
                # Optional: We could print a tiny toast, but better to be silent so UX isn't ruined
                
        except Exception:
            pass # Background thread should never crash the main app

    def _prune_memories(self, max_files=50):
        # Keep disk ultra clean by deleting the oldest files exceeding max_files
        try:
            files = list(LEARNED_DIR.glob("learned_*.md"))
            if len(files) > max_files:
                # Sort by modification time (oldest first)
                files.sort(key=lambda f: f.stat().st_mtime)
                files_to_delete = files[:len(files)-max_files]
                for f in files_to_delete:
                    f.unlink()
        except Exception:
            pass

# Global singleton
_daemon = None

def start_daemon(engine, console):
    global _daemon
    if not _daemon:
        _daemon = SelfLearningDaemon(engine, console)
    _daemon.start()
    
def stop_daemon():
    global _daemon
    if _daemon:
        _daemon.stop()
        _daemon = None
