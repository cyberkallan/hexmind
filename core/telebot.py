import requests
import os
import json
from pathlib import Path

class TeleBot:
    def __init__(self, api_token=None, chat_id=None):
        self.api_token = api_token
        self.chat_id = chat_id
        
        # Try to load from config if not provided
        if not self.api_token or not self.chat_id:
            self._load_config()

    def _load_config(self):
        conf_path = Path.home() / ".hexmind" / "config.json"
        if conf_path.exists():
            try:
                data = json.loads(conf_path.read_text())
                hive = data.get("hive", {})
                self.api_token = hive.get("token")
                self.chat_id = hive.get("chat_id")
            except:
                pass

    def send_message(self, text):
        """Sends a notification to the configured Telegram chat."""
        if not self.api_token or not self.chat_id:
            return False
            
        url = f"https://api.telegram.org/bot{self.api_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": f"🧬 HexMind Hive Alert:\n\n{text}",
            "parse_mode": "Markdown"
        }
        
        try:
            r = requests.post(url, json=payload, timeout=10)
            return r.status_code == 200
        except Exception:
            return False

def notify_hive(text):
    """Convenience function for system-wide Hive notifications."""
    bot = TeleBot()
    bot.send_message(text)
