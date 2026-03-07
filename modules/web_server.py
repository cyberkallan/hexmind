import os
import sys
import threading
import subprocess
import json
from pathlib import Path

try:
    from flask import Flask, request, jsonify, send_from_directory
    from flask_cors import CORS
except ImportError:
    pass

import logging

web_dir = Path(__file__).parent.parent / "web"

def start_gui(engine, port=8080):
    try:
        from flask import Flask, request, jsonify, send_from_directory
        from flask_cors import CORS
    except ImportError:
        print("\n  [red]Flask is not installed. Run 'pip install flask flask-cors' first.[/red]\n")
        return

    app = Flask(__name__, static_folder=str(web_dir))
    CORS(app)
    
    # Disable default Flask logging to keep terminal clean
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)

    @app.route('/')
    def index():
        return send_from_directory(app.static_folder, 'index.html')
        
    @app.route('/<path:path>')
    def serve_static(path):
        return send_from_directory(app.static_folder, path)

    @app.route('/api/chat', methods=['POST'])
    def api_chat():
        data = request.json
        if not data or 'message' not in data:
            return jsonify({"error": "No message provided"}), 400
            
        message = data['message']
        try:
            # We bypass the console printing from normal chat and just return the AI output string
            response = engine.chat(message)
            return jsonify({
                "response": response,
                "latency": getattr(engine, 'last_latency', 0),
                "speed": getattr(engine, 'last_tokens_sec', 0)
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route('/api/history', methods=['GET'])
    def api_history():
        return jsonify({"history": engine.history})
        
    @app.route('/api/terminal', methods=['POST'])
    def api_terminal():
        data = request.json
        cmd = data.get('command')
        if not cmd:
            return jsonify({"error": "No command"}), 400
            
        try:
            # Execute inline, grab stdout/stderr
            r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
            out = r.stdout
            err = r.stderr
            return jsonify({
                "stdout": out,
                "stderr": err,
                "code": r.returncode
            })
        except subprocess.TimeoutExpired:
            return jsonify({"error": "Command timed out."}), 504
        except Exception as e:
            return jsonify({"error": str(e)}), 500
            
    # Open browser on Windows/Mac/Linux
    def open_browser():
        import webbrowser
        import time
        time.sleep(1) # wait for server to start
        try:
            webbrowser.open(f'http://127.0.0.1:{port}')
        except:
            pass
            
    threading.Thread(target=open_browser, daemon=True).start()
    
    from rich.console import Console
    Console().print(f"\n  [bold green]🚀 HexMind Premium UI Engine Started on http://127.0.0.1:{port}[/bold green]")
    Console().print("  [dim]Press Ctrl+C here in the terminal to shut down the server.[/dim]\n")
    
    app.run(host='127.0.0.1', port=port, debug=False, use_reloader=False)

