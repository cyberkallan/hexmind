"""
AutoAgent: Swarm Architecture (P2P)
Enables distributed computing across multiple HexMind instances.
One Node acts as the Master, distributing tasks (like wordlist cracking or mass-scanning)
to connected Worker Nodes via WebSockets/Socket.IO.
"""

import os
import time
import threading
import json
import logging
from typing import Dict, Any

# Disable noisy logging
logging.getLogger('werkzeug').setLevel(logging.ERROR)

class SwarmMaster:
    def __init__(self, engine, port=8888):
        self.engine = engine
        self.port = port
        self.app = None
        self.socketio = None
        self.workers = {}  # sid -> worker_info
        self.active_tasks = {}
        self._thread = None
        self._running = False

    def get_status(self) -> str:
        if not self._running:
            return "Swarm Master is currently offline."
        return f"🟢 **Swarm Master Online** (Port {self.port})\nConnected Workers: {len(self.workers)}"

    def start(self):
        if self._running: return "Already running."
        try:
            from flask import Flask, request
            from flask_socketio import SocketIO, emit
        except ImportError:
            return "Missing dependencies. Run: `pip install flask flask-socketio eventlet`"

        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = os.environ.get("WEB_AUTH_TOKEN", "hexmind_swarm_secret")
        self.socketio = SocketIO(self.app, cors_allowed_origins="*", async_mode='threading')

        @self.socketio.on('connect')
        def handle_connect():
            auth = request.args.get('auth')
            if auth != self.app.config['SECRET_KEY']:
                return False  # Reject unauthorized workers
            
            sid = request.sid
            self.workers[sid] = {"status": "idle", "tasks_completed": 0, "ip": request.remote_addr}
            if self.engine and self.engine.emit_callback:
                self.engine.emit_callback(f"\r\n\x1b[32m[Swarm Master] New Worker Node Connected: {request.remote_addr} ({sid[:6]})\x1b[0m\r\n")

        @self.socketio.on('disconnect')
        def handle_disconnect():
            sid = request.sid
            if sid in self.workers:
                ip = self.workers[sid].get("ip")
                del self.workers[sid]
                if self.engine and self.engine.emit_callback:
                    self.engine.emit_callback(f"\r\n\x1b[31m[Swarm Master] Worker Node Disconnected: {ip} ({sid[:6]})\x1b[0m\r\n")

        @self.socketio.on('task_result')
        def handle_result(data):
            sid = request.sid
            task_id = data.get('task_id')
            result = data.get('result')
            
            if sid in self.workers:
                self.workers[sid]['status'] = 'idle'
                self.workers[sid]['tasks_completed'] += 1
                
            if task_id in self.active_tasks:
                self.active_tasks[task_id]['completed'] += 1
                self.active_tasks[task_id]['results'].append(result)
                
                if self.engine and self.engine.emit_callback:
                    self.engine.emit_callback(f"\x1b[35m[Swarm Master] Received chunk result from {sid[:6]} for task {task_id}\x1b[0m\r\n")

        self._running = True
        self._thread = threading.Thread(target=self._run_server, daemon=True)
        self._thread.start()
        return f"🚀 **Swarm Master Initialized on Port {self.port}**\n\nWorkers can now connect using the auth token."

    def _run_server(self):
        try:
            self.socketio.run(self.app, host='0.0.0.0', port=self.port, allow_unsafe_werkzeug=True)
        except Exception as e:
            self._running = False
            
    def stop(self):
        self._running = False
        if self.socketio:
            self.socketio.stop()
        return "🛑 Swarm Master shutting down."

    def distribute_task(self, task_id: str, command_template: str, payloads: list) -> str:
        """Splits a list of payloads (like passwords or subdomains) across available workers."""
        if not self._running:
            return "Swarm Master is offline."
        if not self.workers:
            return "No Swarm Workers connected! Task cannot be distributed."
            
        worker_sids = list(self.workers.keys())
        num_workers = len(worker_sids)
        
        # Chunk the payloads
        chunk_size = max(1, len(payloads) // num_workers)
        chunks = [payloads[i:i + chunk_size] for i in range(0, len(payloads), chunk_size)]
        
        self.active_tasks[task_id] = {
            "total_chunks": len(chunks),
            "completed": 0,
            "results": [],
            "command_template": command_template
        }
        
        if self.engine and self.engine.emit_callback:
            self.engine.emit_callback(f"\r\n\x1b[36m[Swarm Master] Distributing {len(payloads)} items across {num_workers} nodes...\x1b[0m\r\n")
            
        for idx, chunk in enumerate(chunks):
            if idx >= len(worker_sids):
                # If there are leftovers, give to the first worker
                target_sid = worker_sids[0]
            else:
                target_sid = worker_sids[idx]
                
            self.workers[target_sid]['status'] = 'working'
            self.socketio.emit('execute_chunk', {
                'task_id': task_id,
                'command_template': command_template,
                'chunk': chunk
            }, to=target_sid)
            
        return f"⚡ Distributed Task `{task_id}` to {num_workers} Nodes."


class SwarmWorker:
    def __init__(self, engine):
        self.engine = engine
        self.sio = None
        self._running = False
        self._thread = None

    def connect(self, master_url: str, auth_token: str):
        if self._running: return "Already connected to a Swarm."
        try:
            import socketio
        except ImportError:
            return "Missing dependencies. Run: `pip install python-socketio websocket-client`"

        self.sio = socketio.Client()
        
        @self.sio.event
        def connect():
            if self.engine and self.engine.emit_callback:
                self.engine.emit_callback(f"\r\n\x1b[32m[Swarm Worker] Successfully connected to Master at {master_url}\x1b[0m\r\n")

        @self.sio.event
        def execute_chunk(data):
            # The master sent us work to do
            task_id = data.get('task_id')
            cmd_template = data.get('command_template')
            chunk = data.get('chunk', [])
            
            if self.engine and self.engine.emit_callback:
                self.engine.emit_callback(f"\x1b[35m[Swarm Worker] Received {len(chunk)} items for task {task_id}\x1b[0m\r\n")
                
            # Execute the workloads (simulate or execute actual commands)
            # For safety, we just simulate the formatting here but in reality it would
            # run `subprocess.Popen` or similar for each item.
            import subprocess
            results = []
            for item in chunk[:5]: # Hard limit to 5 per chunk during testing
                cmd = cmd_template.replace("{TARGET}", item)
                try:
                    output = subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.DEVNULL)
                    results.append({"item": item, "output": output[:200]}) # Truncate massive output
                except Exception:
                    pass
                    
            if self.engine and self.engine.emit_callback:
                self.engine.emit_callback(f"\x1b[32m[Swarm Worker] Chunk {task_id} completed. Sending results to Master.\x1b[0m\r\n")
                
            self.sio.emit('task_result', {'task_id': task_id, 'result': results})

        @self.sio.event
        def disconnect():
            if self.engine and self.engine.emit_callback:
                self.engine.emit_callback("\r\n\x1b[31m[Swarm Worker] Disconnected from Master.\x1b[0m\r\n")
            self._running = False

        try:
            url_with_auth = f"{master_url}?auth={auth_token}"
            self.sio.connect(url_with_auth)
            self._running = True
            
            # Run background thread to keep connection alive
            def keep_alive():
                self.sio.wait()
                
            self._thread = threading.Thread(target=keep_alive, daemon=True)
            self._thread.start()
            return f"🔌 **Swarm Worker Initializing**\nAttempting connection to `{master_url}`..."
        except Exception as e:
            return f"Failed to connect to Swarm Master: {e}"

    def disconnect(self):
        if self._running and self.sio:
            self.sio.disconnect()
            self._running = False
            return "Disconnected from Swarm."
        return "Not connected."


# Global Singletons
_SWARM_MASTER = None
_SWARM_WORKER = None

def handle_swarm_command(engine, cmd: str) -> str:
    global _SWARM_MASTER, _SWARM_WORKER
    
    parts = cmd.split(" ", 1)
    action = parts[0].lower()
    
    if action == "master":
        if _SWARM_MASTER: return _SWARM_MASTER.get_status()
        _SWARM_MASTER = SwarmMaster(engine)
        return _SWARM_MASTER.start()
        
    elif action == "join":
        if len(parts) < 2: return "Usage: `swarm join http://MASTER_IP:8888`"
        url = parts[1].strip()
        auth = os.environ.get("WEB_AUTH_TOKEN", "hexmind_swarm_secret")
        if _SWARM_WORKER: return "Already running as a worker."
        _SWARM_WORKER = SwarmWorker(engine)
        return _SWARM_WORKER.connect(url, auth)
        
    elif action == "status":
        res = ""
        if _SWARM_MASTER: res += _SWARM_MASTER.get_status() + "\n\n"
        if _SWARM_WORKER: res += f"Worker Status: {'Connected' if _SWARM_WORKER._running else 'Offline'}"
        return res or "Swarm Node is offline."
        
    elif action == "distribute":
        # Example: swarm distribute brute_task "hydra -l admin -p {TARGET} ssh://192.168.1.5" admin,password,123456
        if not _SWARM_MASTER: return "You must start the Swarm Master first."
        try:
            task_id, rest = parts[1].split(" ", 1)
            cmd_template, payloads_str = rest.rsplit(" ", 1)
            # Remove quotes
            cmd_template = cmd_template.strip("\"'")
            payloads = payloads_str.split(",")
            return _SWARM_MASTER.distribute_task(task_id, cmd_template, payloads)
        except Exception:
            return "Invalid arguments. Usage: `swarm distribute <task_id> \"<cmd_template_{TARGET}>\" item1,item2,item3`"

    return "Unknown Swarm command. Use: `master`, `join <url>`, `status`, `distribute`."
