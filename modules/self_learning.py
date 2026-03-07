"""
HexMind Self-Learning Daemon v3.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Background intelligence that grows HexMind's knowledge daily.

Features:
  - Research new cybersecurity + general tech concepts
  - Learn from user corrections (mistake tracking)
  - Learn from successful interactions
  - Broader topic categories beyond just hacking
  - Keyword indexing for fast retrieval
  - Configurable learning intervals
"""

import os
import time
import random
import hashlib
import threading
import json
from pathlib import Path
from datetime import datetime

MEMORY_DIR = Path.home() / ".hexmind" / "memory"
LEARNED_DIR = MEMORY_DIR / "learned"
INDEX_FILE = LEARNED_DIR / "topic_index.json"
LEARNED_DIR.mkdir(parents=True, exist_ok=True)

# Expanded topic categories — beyond just hacking
TOPICS = [
    # Cybersecurity Core
    "latest CVEs in web applications",
    "advanced privilege escalation on Linux 2025",
    "Windows Active Directory attack techniques",
    "cloud security misconfigurations AWS Azure GCP",
    "API security testing methodology",
    "mobile application security testing",
    "container and Kubernetes security",
    "supply chain attacks and software security",
    "web cache poisoning techniques",
    "GraphQL security vulnerabilities",
    "OAuth and JWT exploitation",
    "DNS rebinding attacks",
    "SSRF bypass techniques",
    "deserialization vulnerabilities",
    "race condition exploitation",
    # AI and Machine Learning
    "LLM prompt injection attacks and defenses",
    "AI red teaming and adversarial attacks",
    "local LLM deployment with Ollama",
    "RAG retrieval augmented generation",
    "fine-tuning small language models",
    # Programming & DevOps
    "Python async programming best practices",
    "Rust for security tools",
    "reverse engineering with Ghidra",
    "malware analysis with dynamic analysis",
    "CI/CD pipeline security hardening",
    # General Knowledge (for personality)
    "latest technology trends 2025",
    "cybersecurity career growth tips",
    "how to write better CTF writeups",
    "open source intelligence OSINT techniques",
    "network forensics with Wireshark advanced",
]

MAX_STORAGE_MB = 15


class SelfLearningDaemon:
    def __init__(self, engine=None, interval_hours: float = 6):
        self.engine = engine
        self.interval = interval_hours * 3600  # Convert to seconds
        self._thread = None
        self._running = False
        self._topic_index = self._load_index()
        
    def _load_index(self) -> dict:
        """Load the keyword index for fast topic lookup."""
        try:
            if INDEX_FILE.exists():
                return json.loads(INDEX_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
        return {}
    
    def _save_index(self):
        """Save the keyword index."""
        try:
            INDEX_FILE.write_text(json.dumps(self._topic_index, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    def _loop(self):
        """Background learning loop."""
        # Wait a bit before first learning cycle
        time.sleep(30)
        
        while self._running:
            try:
                self._learn_new_concept()
                self._learn_from_corrections()
                self._prune_memories()
                self._save_index()
            except Exception:
                pass
            time.sleep(self.interval)

    def _learn_new_concept(self):
        """Research a random topic using the Deep Research Loop."""
        topic = random.choice(TOPICS)
        slug = hashlib.md5(topic.encode()).hexdigest()[:10]
        filepath = LEARNED_DIR / f"learned_{slug}.md"
        
        # Skip if already learned
        if filepath.exists():
            return
            
        content = None
        if self.engine:
            try:
                # Use AutoAgent's Deep Research instead of a simple prompt
                from brain.autoagent.deep_research import run_deep_research
                content = run_deep_research(self.engine, topic)
            except Exception as e:
                pass

        if not content:
            # Fallback
            content = f"# {topic}\n\nTopic queued for research. Will be populated when AI engine is available."

        # Save to file (Deep Research already saves it, but we handle fallback here)
        if "Topic queued" in content:
            filepath.write_text(content, encoding="utf-8")
        
        # Update keyword index
        keywords = topic.lower().split()
        for kw in keywords:
            if len(kw) > 3:  # Skip short words
                if kw not in self._topic_index:
                    self._topic_index[kw] = []
                self._topic_index[kw].append(str(filepath.name))

    def _learn_from_corrections(self):
        """Process user corrections to improve future responses."""
        corrections_file = MEMORY_DIR / "corrections.json"
        if not corrections_file.exists():
            return
            
        try:
            corrections = json.loads(corrections_file.read_text(encoding="utf-8"))
            if not corrections:
                return
                
            # Create a corrections knowledge file
            corrections_knowledge = LEARNED_DIR / "learned_corrections.md"
            
            parts = [f"# Learned Corrections\n_Updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}_\n"]
            parts.append("These are mistakes the AI made that the user corrected:\n")
            
            for c in corrections[-10:]:  # Last 10 corrections
                parts.append(f"- **Wrong:** {c.get('original', '')[:100]}")
                parts.append(f"  **Correct:** {c.get('corrected', '')[:100]}")
                parts.append("")
            
            corrections_knowledge.write_text("\n".join(parts), encoding="utf-8")
        except Exception:
            pass

    def _prune_memories(self):
        """Keep storage under the limit by removing oldest files."""
        try:
            files = list(LEARNED_DIR.glob("learned_*.md"))
            total_size = sum(f.stat().st_size for f in files)
            max_bytes = MAX_STORAGE_MB * 1024 * 1024
            
            if total_size > max_bytes:
                # Sort by age (oldest first), skip corrections file
                files = [f for f in files if "corrections" not in f.name]
                files.sort(key=lambda f: f.stat().st_mtime)
                
                while total_size > max_bytes * 0.8 and files:
                    oldest = files.pop(0)
                    total_size -= oldest.stat().st_size
                    oldest.unlink()
        except Exception:
            pass

    def get_knowledge_by_keyword(self, keyword: str) -> str:
        """Search learned knowledge by keyword."""
        keyword = keyword.lower().strip()
        matches = set()
        
        for kw, files in self._topic_index.items():
            if keyword in kw or kw in keyword:
                matches.update(files)
        
        if not matches:
            return ""
        
        results = []
        for fname in list(matches)[:3]:
            fpath = LEARNED_DIR / fname
            if fpath.exists():
                results.append(fpath.read_text(encoding="utf-8")[:500])
        
        return "\n\n---\n\n".join(results)


def start_learning(engine=None, interval_hours: float = 6):
    """Start the background learning daemon."""
    daemon = SelfLearningDaemon(engine=engine, interval_hours=interval_hours)
    daemon.start()
    return daemon
