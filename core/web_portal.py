import os
import sys
import threading
import time
import webbrowser
import json
import logging
import secrets
from pathlib import Path
from flask import Flask, render_template, jsonify, request, abort

try:
    from flask_socketio import SocketIO, emit
    HAS_SOCKETIO = True
except ImportError:
    HAS_SOCKETIO = False

try:
    import psutil
except ImportError:
    psutil = None

# Configure Flask app to use the web folder
BASE_DIR = Path(__file__).parent.parent / "web"
app = Flask(__name__, template_folder=BASE_DIR / "templates", static_folder=BASE_DIR / "static")

if HAS_SOCKETIO:
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading", ping_timeout=60, ping_interval=25)
else:
    socketio = None

# Global state
HEXMIND_STATE = {
    "target": "None",
    "telemetry": {"cpu": 0, "ram": 0},
    "skills": {
        "voice": False,
        "sentinel": False,
        "ghost": False,
        "autopwn": False
    }
}

ENGINE_INSTANCE = None
WEB_AUTH_TOKEN = secrets.token_hex(16)

def verify_token():
    token = request.args.get("token") or request.headers.get("Authorization")
    if token != WEB_AUTH_TOKEN:
        abort(403)

# ── Flask Routes ─────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/verify", methods=["GET"])
def verify_api_token():
    token = request.args.get("token") or request.headers.get("Authorization")
    if token != WEB_AUTH_TOKEN:
        return jsonify({"status": "error"}), 403
    return jsonify({"status": "success"})

@app.route("/api/status", methods=["GET"])
def get_status():
    verify_token()
    if psutil:
        HEXMIND_STATE["telemetry"]["cpu"] = psutil.cpu_percent(interval=None)
        HEXMIND_STATE["telemetry"]["ram"] = psutil.virtual_memory().percent
    
    os_name = "WINDOWS" if os.name == "nt" else "LINUX/TERMUX"
    
    # Determine Active Model & Stats
    active_model = "UNKNOWN"
    latency = 0.0
    tokens_sec = 0.0
    
    if ENGINE_INSTANCE:
        latency = getattr(ENGINE_INSTANCE.engine, "last_latency", 0.0) if ENGINE_INSTANCE.engine else 0.0
        tokens_sec = getattr(ENGINE_INSTANCE.engine, "last_tokens_sec", 0.0) if ENGINE_INSTANCE.engine else 0.0
        
        if getattr(ENGINE_INSTANCE, "local_ai", False):
            try:
                active_model = ENGINE_INSTANCE.engine.offline_brain.get_local_llm().model_name()
            except Exception:
                active_model = "Offline Local Brain"
        else:
            try:
                active_model = ENGINE_INSTANCE.config.get("provider", {}).get("name", "OpenRouter (Cloud)")
            except Exception:
                active_model = "Cloud Provider"
                
    return jsonify({
        "telemetry": HEXMIND_STATE["telemetry"],
        "skills": HEXMIND_STATE["skills"],
        "os": os_name,
        "target": HEXMIND_STATE["target"],
        "active_model": active_model,
        "analytics": {
            "latency": latency,
            "tokens_sec": tokens_sec
        }
    })

@app.route("/api/config", methods=["GET"])
def get_config():
    verify_token()
    if ENGINE_INSTANCE:
        cfg = ENGINE_INSTANCE.config
        return jsonify({
            "provider": cfg.get("provider", {}),
            "telegram_token": cfg.get("telegram_token", "")
        })
    return jsonify({})

@app.route("/api/config", methods=["POST"])
def set_config():
    verify_token()
    data = request.json
    if ENGINE_INSTANCE:
        if "provider_key" in data:
            if "provider" not in ENGINE_INSTANCE.config:
                ENGINE_INSTANCE.config["provider"] = {"name": "OpenRouter", "type": "openrouter"}
            ENGINE_INSTANCE.config["provider"]["key"] = data["provider_key"]
        
        if "telegram_token" in data:
            ENGINE_INSTANCE.config["telegram_token"] = data["telegram_token"]
            
        ENGINE_INSTANCE.cfg_mgr.save(ENGINE_INSTANCE.config)
        return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "Engine not attached."})

@app.route("/api/skills/toggle", methods=["POST"])
def toggle_skill():
    verify_token()
    data = request.json
    skill = data.get("skill")
    if skill in HEXMIND_STATE["skills"]:
        is_active = not HEXMIND_STATE["skills"][skill]
        HEXMIND_STATE["skills"][skill] = is_active
        
        # Dispatch to engine
        if ENGINE_INSTANCE:
            if skill == "voice":
                ENGINE_INSTANCE.cmd_queue.put("voice")
            elif skill == "autopwn":
                ENGINE_INSTANCE.cmd_queue.put("autopwn")
        
        return jsonify({"status": "success", "is_active": is_active})
    return jsonify({"status": "error"})

@app.route("/api/reset", methods=["POST"])
def hard_reset():
    verify_token()
    import shutil
    try:
        shutil.rmtree(Path.home() / ".hexmind")
    except Exception:
        pass
    os._exit(0)
    return jsonify({"status": "nuked"})

@app.route("/api/readme", methods=["GET"])
def get_readme():
    verify_token()
    readme_path = Path(__file__).parent.parent / "README.md"
    if readme_path.exists():
        with open(readme_path, "r", encoding="utf-8") as f:
            return jsonify({"status": "success", "content": f.read()})
    return jsonify({"status": "error", "message": "README.md not found"}), 404

@app.route("/api/history", methods=["GET"])
def get_history():
    """Return session chat history for the WebUI history panel."""
    verify_token()
    if ENGINE_INSTANCE and hasattr(ENGINE_INSTANCE, 'engine') and ENGINE_INSTANCE.engine:
        history = ENGINE_INSTANCE.engine.conversation_history[-50:]  # Last 50 messages
        return jsonify({"status": "success", "history": history})
    return jsonify({"status": "success", "history": []})


# ── Web Terminal Bridge (with typing indicators) ─────────────────────────────
class HexMindTerminal:
    def __init__(self, socketio_app):
        self.socketio = socketio_app
        self.buffer = ""
        self._processing = False
        
        try:
            from core.interactive_runner import InteractiveRunner
            output_emitter = lambda text: self.socketio.emit("term_output", {"text": text})
            self.runner = InteractiveRunner(self, output_emitter)
        except ImportError:
            self.runner = None
        
    def write(self, char: str):
        # 1. Route to InteractiveRunner if it's currently running a process
        if self.runner and self.runner._running:
            if char == '\r':
                cmd = self.buffer
                self.socketio.emit("term_output", {"text": "\r\n"})
                self.buffer = ""
                self.runner.write_input(cmd + '\n')
            elif char == '\x7f':
                if len(self.buffer) > 0:
                    self.buffer = self.buffer[:-1]
                    self.socketio.emit("term_output", {"text": "\b \b"})
            elif char == '\x03':
                self.buffer = ""
                self.socketio.emit("term_output", {"text": "^C\r\n"})
                self.runner.kill()
            else:
                if not char.startswith('\x1b'):
                    self.buffer += char
                    self.socketio.emit("term_output", {"text": char})
            return

        # 2. Normal HexMind Hub Routing
        if char == '\r':
            cmd = self.buffer.strip()
            self.socketio.emit("term_output", {"text": "\r\n"})
            self.buffer = ""
            
            if not cmd:
                self._prompt()
                return

            if cmd.lower() in ["clear", "cls"]:
                self.socketio.emit("term_output", {"text": "\x1b[2J\x1b[H"})
                self._prompt()
                return
                
            if ENGINE_INSTANCE:
                def _run_chat():
                    try:
                        self._processing = True
                        # Show typing indicator
                        self.socketio.emit("typing_start")
                        
                        # Log voice interactions for learning
                        try:
                            if hasattr(ENGINE_INSTANCE, 'memory') and ENGINE_INSTANCE.memory:
                                ENGINE_INSTANCE.memory.record_exchange(cmd, "")
                        except Exception:
                            pass
                        
                        ENGINE_INSTANCE.engine.emit_callback = lambda text: self.socketio.emit("term_output", {"text": text})
                        response = ENGINE_INSTANCE.engine.chat(cmd)
                        ENGINE_INSTANCE.engine.emit_callback = None
                        
                        # Intercept if HexMind decides to spawn an interactive tool directly
                        if response and response.startswith("__SPAWN__ "):
                            spawn_cmd = response.split("__SPAWN__ ", 1)[1].strip()
                            self.socketio.emit("term_output", {"text": f"\x1b[32m✔ HexMind Spawning:\x1b[0m {spawn_cmd}\r\n"})
                            self.socketio.emit("typing_end")
                            self._processing = False
                            if self.runner:
                                self.runner.spawn(spawn_cmd)
                            return
                        
                        # Format response for terminal
                        if response:
                            # Clean up response for xterm.js
                            clean_resp = response.replace('\n', '\r\n')
                            self.socketio.emit("term_output", {
                                "text": f"\x1b[32m✔ HexMind:\x1b[0m\r\n{clean_resp}\r\n"
                            })
                        else:
                            self.socketio.emit("term_output", {
                                "text": "\x1b[2mCommand processed.\x1b[0m\r\n"
                            })
                            
                        # Update memory with response
                        try:
                            if hasattr(ENGINE_INSTANCE, 'memory') and ENGINE_INSTANCE.memory:
                                ENGINE_INSTANCE.memory.record_exchange(cmd, response or "")
                        except Exception:
                            pass
                            
                    except Exception as e:
                        self.socketio.emit("term_output", {
                            "text": f"\r\n\x1b[31m[ERROR] {str(e)}\x1b[0m\r\n"
                        })
                    finally:
                        self._processing = False
                        self.socketio.emit("typing_end")
                        self._prompt()
                        
                threading.Thread(target=_run_chat, daemon=True).start()
            else:
                self.socketio.emit("term_output", {"text": "\r\nENGINE NOT ATTACHED.\r\n"})
                self._prompt()
        elif char == '\x7f':
            if len(self.buffer) > 0:
                self.buffer = self.buffer[:-1]
                self.socketio.emit("term_output", {"text": "\b \b"})
        elif char == '\x03':
            self.buffer = ""
            self.socketio.emit("term_output", {"text": "^C\r\n"})
            self._prompt()
        else:
            if not char.startswith('\x1b'):
                self.buffer += char
                self.socketio.emit("term_output", {"text": char})

    def _prompt(self):
        self.socketio.emit("term_output", {"text": "\x1b[36mYou ❯\x1b[0m "})

TTY_INSTANCE = None

# ── Socket.IO Terminal ────────────────────────────────────────────────────────
if HAS_SOCKETIO:
    @socketio.on("connect")
    def handle_connect():
        global TTY_INSTANCE
        if not TTY_INSTANCE:
            TTY_INSTANCE = HexMindTerminal(socketio)
        
        socketio.emit("term_output", {"text": "\r\n\x1b[1;36mHexMind V13 Ultimate Gateway Online.\x1b[0m\r\n"})
        socketio.emit("term_output", {"text": "\x1b[2mVoice: Click 🎙️ VOICE to activate | Keyboard: Ctrl+1-5 for tabs\x1b[0m\r\n"})
        TTY_INSTANCE._prompt()

    @socketio.on("term_input")
    def handle_term_input(data):
        if TTY_INSTANCE:
            TTY_INSTANCE.write(data.get("text", ""))

    @socketio.on("disconnect")
    def handle_disconnect():
        pass  # Client disconnected gracefully


# ── Web Server Daemon ─────────────────────────────────────────────────────────
def run_server(port):
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    
    if HAS_SOCKETIO:
        socketio.run(app, host="127.0.0.1", port=port, allow_unsafe_werkzeug=True)
    else:
        app.run(host="127.0.0.1", port=port, debug=False)

def start_command_center(main_app, port=8888, console=None):
    global ENGINE_INSTANCE
    ENGINE_INSTANCE = main_app
    
    import socket
    def find_free_port(start_port, max_port=8999):
        for p in range(start_port, max_port + 1):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                if s.connect_ex(('127.0.0.1', p)) != 0:
                    return p
        return start_port
        
    actual_port = find_free_port(port)
    
    if psutil:
        psutil.cpu_percent(interval=None)  # Initialize
        
    t = threading.Thread(target=run_server, args=(actual_port,), daemon=True)
    t.start()
    
    time.sleep(1)
    url = f"http://127.0.0.1:{actual_port}/"
    if console:
        console.print(f"  [bold green]✓[/bold green] [cyan]God-Mode Command Center active:[/cyan]")
        console.print(f"  [u]{url}[/u]\n", soft_wrap=True)
        console.print(f"  [cyan]Authentication Token:[/cyan] [bold yellow]{WEB_AUTH_TOKEN}[/bold yellow]\n")
        try:
            webbrowser.open(url)
        except Exception:
            pass
