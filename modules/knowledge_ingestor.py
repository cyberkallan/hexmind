import os
import subprocess
import threading
import time
from pathlib import Path

INTELLIGENCE_DIR = Path.home() / ".hexmind" / "intelligence"

KNOWLEDGE_REPOS = {
    "awesome-chatgpt-prompts": "https://github.com/f/awesome-chatgpt-prompts.git",
    "PayloadsAllTheThings": "https://github.com/swisskyrepo/PayloadsAllTheThings.git",
    "hacktricks": "https://github.com/carlospolop/hacktricks.git"
}

class KnowledgeIngestor:
    def __init__(self, console=None):
        self.console = console
        INTELLIGENCE_DIR.mkdir(parents=True, exist_ok=True)
        self._thread = None

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._ingest_loop, daemon=True)
        self._thread.start()

    def _ingest_loop(self):
        # Delay start to avoid lagging the initial boot sequence
        time.sleep(3)
        
        for name, url in KNOWLEDGE_REPOS.items():
            repo_path = INTELLIGENCE_DIR / name
            if not repo_path.exists():
                if self.console:
                    # Silent in standard mode, but we could log it if needed.
                    pass
                try:
                    # Using --depth 1 to save massive amounts of disk space and time
                    subprocess.run(
                        ["git", "clone", "--depth", "1", url, str(repo_path)],
                        check=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                except Exception:
                    pass # Fail silently if no git or offline

# Global Daemon
_ingestor = None

def start_ingestor(console=None):
    global _ingestor
    if not _ingestor:
        _ingestor = KnowledgeIngestor(console)
    _ingestor.start()

def get_persona_prompt(persona_name: str) -> str:
    """Read prompts.csv from awesome-chatgpt-prompts and return the behavior."""
    try:
        csv_path = INTELLIGENCE_DIR / "awesome-chatgpt-prompts" / "prompts.csv"
        if not csv_path.exists():
            return ""
            
        import csv
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader, None) # Skip header
            for row in reader:
                if len(row) >= 2 and persona_name.lower() in row[0].lower():
                    return row[1].strip()
    except Exception:
        pass
    return ""

def search_payloads(topic: str) -> str:
    """Grep local payload directories for specific keywords to augment knowledge."""
    try:
        patt_path = INTELLIGENCE_DIR / "PayloadsAllTheThings"
        if not patt_path.exists():
            return ""
            
        # Recursive glob search for markdown files
        results = []
        for path in patt_path.rglob("*.md"):
            if topic.lower() in path.name.lower():
                content = path.read_text(encoding="utf-8", errors="ignore")
                results.append(f"Source: {path.name}\n{content[:1500]}") # Take first 1500 chars 
                if len(results) >= 2:
                    break
        
        return "\n\n".join(results)
    except Exception:
        return ""
