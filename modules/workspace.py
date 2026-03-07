import os
import json
from pathlib import Path

WORKSPACE_CONFIG = Path.home() / ".hexmind" / "active_workspace.json"

def set_target(target_name: str, base_path: str = None) -> str:
    """Creates the workspace directory tree and sets the active target."""
    if base_path is None:
        base_path = os.getcwd()
        
    target_dir = Path(base_path) / target_name
    
    folders = ["recon", "scans", "exploits", "loot"]
    for f in folders:
        (target_dir / f).mkdir(parents=True, exist_ok=True)
        
    report = target_dir / "report.md"
    if not report.exists():
        report.write_text(f"# Target: {target_name}\n\n## Engagement Notes\n\n## Assets\n\n## Vulnerabilities\n")
        
    WORKSPACE_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    WORKSPACE_CONFIG.write_text(json.dumps({
        "target": target_name,
        "path": str(target_dir)
    }))
    
    return str(target_dir)

def get_active_workspace() -> dict:
    if WORKSPACE_CONFIG.exists():
        try:
            return json.loads(WORKSPACE_CONFIG.read_text())
        except:
            pass
    return {}

def clear_workspace():
    if WORKSPACE_CONFIG.exists():
        WORKSPACE_CONFIG.unlink()
