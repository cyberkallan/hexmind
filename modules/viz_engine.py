import os
import json
from pathlib import Path
from modules.workspace import get_active_workspace

def get_viz_data():
    """Scans the active workspace and returns nodes/edges for visualization."""
    workspace = get_active_workspace()
    if not workspace:
        return {
            "target": "None",
            "nodes": [],
            "edges": []
        }
        
    target_name = workspace.get("target", "Unknown")
    target_path = Path(workspace.get("path", "."))
    recon_dir = target_path / "recon"
    
    nodes = [{"label": target_name, "type": "Target Root"}]
    edges = []
    
    # Try to find subdomains or IP addresses in recon files
    # Logic: Look for files like subdomains.txt, nmap.txt, etc.
    if recon_dir.exists():
        for f in recon_dir.glob("*"):
            if f.is_file():
                # Add file as a node
                fname = f.name
                nodes.append({"label": fname, "type": "Recon Data"})
                edges.append({"source": target_name.replace(".","_"), "target": fname.replace(".","_")})
                
                # Check for interesting content inside (very basic)
                try:
                    content = f.read_text(errors='ignore')
                    # Simple heuristic: if it looks like a list of IP/domains
                    lines = [l.strip() for l in content.split("\n") if l.strip() and len(l) < 100]
                    for i, line in enumerate(lines[:10]): # Limit to first 10 for viz clarity
                         clean_node = line.replace(".","_").replace("-","_")
                         nodes.append({"label": line, "type": "Sub-Asset"})
                         edges.append({"source": fname.replace(".","_"), "target": clean_node})
                except:
                    pass

    # Normalize IDs for Mermaid (no dots/dashes in node names)
    final_edges = []
    for e in edges:
        final_edges.append({
            "source": e["source"].replace(".","_").replace("-","_"),
            "target": e["target"].replace(".","_").replace("-","_")
        })

    return {
        "target": target_name,
        "nodes": nodes,
        "edges": final_edges
    }
