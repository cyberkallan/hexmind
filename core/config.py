import json
from pathlib import Path


class ConfigManager:
    def __init__(self, config_dir: Path, config_file: Path):
        self.config_dir  = config_dir
        self.config_file = config_file

    def load(self):
        self.config_dir.mkdir(parents=True, exist_ok=True)
        if self.config_file.exists():
            try:
                with open(self.config_file, "r") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def save(self, data: dict):
        self.config_dir.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, "w") as f:
            json.dump(data, f, indent=2)
