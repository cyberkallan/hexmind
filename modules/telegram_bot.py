import time
import requests
import threading

class TelegramDaemon(threading.Thread):
    def __init__(self, token, engine):
        super().__init__()
        self.token = token
        self.engine = engine
        self.daemon = True
        self.offset = 0
        self.api_url = f"https://api.telegram.org/bot{self.token}"

    def run(self):
        # We need to test the token first
        try:
            resp = requests.get(f"{self.api_url}/getMe", timeout=5).json()
            if not resp.get("ok"):
                return  # Invalid token
        except:
            return

        while True:
            try:
                updates = requests.get(f"{self.api_url}/getUpdates?offset={self.offset}&timeout=30", timeout=40).json()
                if updates.get("ok"):
                    for update in updates.get("result", []):
                        self.offset = update["update_id"] + 1
                        message = update.get("message")
                        if message and "text" in message:
                            chat_id = message["chat"]["id"]
                            user_text = message["text"]
                            
                            # Handle HexMind Chat
                            try:
                                # Start thinking notice
                                requests.post(f"{self.api_url}/sendChatAction", json={"chat_id": chat_id, "action": "typing"}, timeout=5)
                                
                                # Process through actual engine
                                response = self.engine.chat(user_text)
                                
                                # Send response back
                                self.send_message(chat_id, response)
                            except Exception as e:
                                self.send_message(chat_id, f"❌ HexMind Agent Error: {e}")
                                
            except Exception:
                time.sleep(5)  # Re-try loop on connection errors

    def send_message(self, chat_id, text):
        max_len = 4000
        for i in range(0, len(text), max_len):
            chunk = text[i:i+max_len]
            requests.post(f"{self.api_url}/sendMessage", json={"chat_id": chat_id, "text": chunk}, timeout=10)

def start_telegram_daemon(engine, token, console):
    if not token or not engine:
        return None
    daemon = TelegramDaemon(token, engine)
    daemon.start()
    return daemon
