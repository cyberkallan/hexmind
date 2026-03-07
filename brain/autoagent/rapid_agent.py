"""
AutoAgent: RapidAPI Omni-Agent (The Swiss Army Knife)
Dynamically translates natural language queries into RapidAPI REST requests,
fetches the data, and synthesizes it for the user.
"""

import json
from pathlib import Path
import re

class RapidOmniAgent:
    def __init__(self, engine):
        self.engine = engine
        self.api_key = self._get_rapid_key()

    def _get_rapid_key(self):
        config_file = Path.home() / ".hexmind" / "keys.json"
        if config_file.exists():
            try:
                data = json.loads(config_file.read_text())
                return data.get("rapidapi_key", "")
            except:
                pass
        return ""

    def execute(self, query: str) -> str:
        if not self.api_key:
            return "❌ **RapidAPI Key Missing**\n\nThe Omni-Agent requires an `X-RapidAPI-Key`. Please restart HexMind to run the Onboarding setup again, or add it manually to `~/.hexmind/keys.json` under `rapidapi_key`."

        if self.engine.emit_callback:
            self.engine.emit_callback(f"\r\n\x1b[35m[Omni-API] Formulating dynamic RapidAPI request for: '{query}'\x1b[0m\r\n")

        # Step 1: LLM determines the exact endpoint and parameters
        prompt = f"""You are the RapidAPI Omni-Agent. The user wants information about: "{query}"

Given your knowledge of RapidAPI Hub, deduce a highly probable and standard API endpoint that provides this data (e.g., virustotal, truecaller, openweather, etc., on the `.p.rapidapi.com` domain).

You must return ONLY a raw JSON object with the following structure. No markdown, no explanations:
{{
    "url": "https://<api-name>.p.rapidapi.com/<endpoint>",
    "method": "GET",
    "headers": {{
        "X-RapidAPI-Host": "<api-name>.p.rapidapi.com"
    }},
    "querystring": {{"param1": "value1"}}
}}
Do NOT include the X-RapidAPI-Key in the JSON, I will inject it securely.
"""
        json_str = self.engine.offline_brain.respond(prompt) if self.engine.is_offline() else self.engine.chat(prompt)
        
        # Clean JSON
        try:
            match = re.search(r'\{.*\}', json_str, re.DOTALL)
            if match:
                json_str = match.group(0)
            req_data = json.loads(json_str)
        except json.JSONDecodeError:
            return "🧠 Omni-Agent failed to synthesize a valid RapidAPI endpoint configuration."

        # Step 2: Inject Auth & Execute
        url = req_data.get("url", "")
        method = req_data.get("method", "GET").upper()
        headers = req_data.get("headers", {})
        querystring = req_data.get("querystring", {})

        headers["X-RapidAPI-Key"] = self.api_key

        if self.engine.emit_callback:
            self.engine.emit_callback(f"\x1b[36m  > Fetching: {method} {url}\x1b[0m\r\n")

        import requests
        try:
            if method == "GET":
                response = requests.get(url, headers=headers, params=querystring, timeout=15)
            elif method == "POST":
                response = requests.post(url, headers=headers, json=querystring, timeout=15)
            else:
                response = requests.request(method, url, headers=headers, params=querystring, timeout=15)
                
            if response.status_code == 200:
                raw_data = response.text
                if len(raw_data) > 3000:
                    raw_data = raw_data[:3000] + "... [TRUNCATED]"
                    
                if self.engine.emit_callback:
                    self.engine.emit_callback("\x1b[32m✔ Data retrieved. Synthesizing intelligence...\x1b[0m\r\n")

                # Step 3: Synthesis
                syn_prompt = f"Summarize this raw API JSON data into a clean, professional intelligence report for the user:\n\n{raw_data}"
                final_res = self.engine.offline_brain.respond(syn_prompt) if self.engine.is_offline() else self.engine.chat(syn_prompt)
                
                return f"🔌 **Omni-API Intelligence Report**\n\n{final_res}"
            else:
                return f"⚠️ **RapidAPI Error** ({response.status_code})\n\n```json\n{response.text}\n```"
                
        except Exception as e:
            return f"❌ Request failed: {e}"

def run_rapid_omni_agent(engine, query: str) -> str:
    agent = RapidOmniAgent(engine)
    return agent.execute(query)
