"""
AutoAgent: AST Exploit Mutator & 0-Day Crafter
Scrambles payloads using polynomial encodings, polyglots, and syntax
obfuscation to automatically bypass Web Application Firewalls (WAFs).
"""

import json
from collections import deque

class ExploitMutatorAgent:
    def __init__(self, engine):
        self.engine = engine
        
    def mutate(self, base_payload: str, waf_type: str = "generic") -> list:
        """
        Takes a base payload and generates 5 highly sophisticated WAF-bypass mutations.
        """
        if self.engine.emit_callback:
            self.engine.emit_callback(f"\r\n\x1b[35m[Mutator] Analyzing base payload: {base_payload}\x1b[0m\r\n")
            
        prompt = f"""You are the Advanced AST Exploit Mutator Agent.
The user has provided a base payload that gets blocked by a '{waf_type}' WAF:
{base_payload}

Your goal is to generate 5 completely different, highly obfuscated mutations
of this payload to bypass the WAF. Use techniques like:
- Hex encoding, Unicode normalization abuses
- Polyglots (valid in multiple contexts)
- Blank space bypass (tabs, newlines, comments)
- SQL/NoSQL specific dialect quirks (if applicable)

Return ONLY a valid JSON array of strings containing the 5 mutated payloads. No markdown, no explanations.
Example: ["mutation1", "mutation2"]
"""
        json_str = self.engine.offline_brain.respond(prompt) if self.engine.is_offline() else self.engine.chat(prompt)
        
        # Clean up JSON
        import re
        try:
            match = re.search(r'\[.*\]', json_str, re.DOTALL)
            if match:
                json_str = match.group(0)
            mutations = json.loads(json_str)
        except json.JSONDecodeError:
            mutations = [
                f"/* Bypass */{base_payload}", 
                base_payload.replace(" ", "/**/"),
            ]
            
        if self.engine.emit_callback:
            self.engine.emit_callback(f"\x1b[32m✔ [Mutator] Generated {len(mutations)} stealth variations.\x1b[0m\r\n")

        return mutations

def run_exploit_mutator(engine, payload: str, waf: str = "generic") -> str:
    agent = ExploitMutatorAgent(engine)
    mutations = agent.mutate(payload, waf)
    
    res = f"🧬 **Automated Exploit Mutator (WAF: {waf})**\n\nBase Payload: `{payload}`\n\n**Generated Mutations:**\n\n"
    for i, m in enumerate(mutations):
        res += f"{i+1}. `{m}`\n"
        
    res += "\n*Try these variants. If they fail, provide the WAF error response to the Mutator for dynamic learning.*"
    return res
