"""
AutoAgent: Computer Vision / Web-UI Sandbox Attacker
Integrates Playwright to physically open a browser, take screenshots, 
and use Vision Language Models to bypass logical UI vulnerabilities.
"""

import os
import time
from pathlib import Path

class VisionAttackerAgent:
    def __init__(self, engine):
        self.engine = engine
        self.workspace = Path.home() / ".hexmind" / "workspaces" / "vision_sandbox"
        self.workspace.mkdir(parents=True, exist_ok=True)

    def attack(self, target_url: str) -> str:
        """Launch Playwright, screenshot the target, and analyze the UI."""
        if self.engine.emit_callback:
            self.engine.emit_callback(f"\r\n\x1b[35m[Vision Attacker] Initializing Playwright Sandbox for {target_url}\x1b[0m\r\n")
            
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            err = "Playwright is not installed. To use the Vision Attacker, run: `pip install playwright && playwright install`"
            if self.engine.emit_callback:
                self.engine.emit_callback(f"\x1b[31m✖ {err}\x1b[0m\r\n")
            return err

        screenshot_path = str(self.workspace / f"target_{int(time.time())}.png")
        
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.set_viewport_size({"width": 1280, "height": 800})
                
                if self.engine.emit_callback:
                    self.engine.emit_callback("\x1b[36m  Navigating to target and waiting for network idle...\x1b[0m\r\n")
                
                page.goto(target_url, wait_until="networkidle", timeout=15000)
                
                # Optional: Handle basic auth or bypass modals here in the future
                
                page.screenshot(path=screenshot_path, full_page=True)
                browser.close()
                
            if self.engine.emit_callback:
                self.engine.emit_callback(f"\x1b[32m✔ Snapshot captured at {screenshot_path}\x1b[0m\r\n")
                
        except Exception as e:
            return f"Failed to open Sandbox: {str(e)}"

        # Now we pass the screenshot to the Vision API
        if self.engine.emit_callback:
            self.engine.emit_callback("\x1b[36m[Vision Attacker] Sending UI snapshot to VLM for logical vulnerability analysis...\x1b[0m\r\n")

        # Reuse HexMind's vision module but with an aggressive attacker prompt
        from modules.vision import encode_image
        try:
            base64_img = encode_image(screenshot_path)
            
            # Retrieve LLM config
            config_file = Path.home() / ".hexmind" / "keys.json"
            cfg = {}
            if config_file.exists():
                import json
                try: cfg = json.loads(config_file.read_text())
                except: pass
                
            api_key = cfg.get("openrouter_key", "")
            if not api_key:
                return f"Vision snapshot saved to `{screenshot_path}`, but no OpenRouter API key found for VLM analysis."
                
            prompt = (
                f"You are the Vision Sandbox Attacker. Analyze this screenshot of {target_url}.\n"
                f"1. Identify the authentication mechanism, CMS, or framework visually.\n"
                f"2. Look for logical bypasses, visible admin panels, debug info, or CAPTCHA presence.\n"
                f"3. Provide a step-by-step UI hacking plan based on what you see."
            )
            
            import requests
            url = "https://openrouter.ai/api/v1/chat/completions"
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            payload = {
                "model": "google/gemini-2.5-pro", # Strong vision capabilities
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_img}"}}
                        ]
                    }
                ],
                "max_tokens": 1500
            }
            r = requests.post(url, headers=headers, json=payload, timeout=60)
            if r.status_code == 200:
                analysis = r.json()["choices"][0]["message"]["content"]
                
                # Clean up local screenshot after analysis
                os.remove(screenshot_path)
                
                return f"👁️ **Vision Attacker Analysis Complete**\n\nTarget: {target_url}\n\n{analysis}"
            else:
                return f"Vision API Error: HTTP {r.status_code} - {r.text}"
                
        except Exception as e:
            return f"Error during UI analysis: {e}"

def run_vision_attacker(engine, target: str) -> str:
    agent = VisionAttackerAgent(engine)
    return agent.attack(target)
