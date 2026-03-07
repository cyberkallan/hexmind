"""
HexMind Chat Engine v3.0
- Integrates memory (self-learning) into every cloud API request
- Integrates installed skills as context
- Seamless offline fallback with 3-tier brain
- Faster timeout, better error handling
"""

import requests
from brain.offline import OfflineBrain
from brain.memory  import UserMemory
from brain.skills  import SkillsManager
from core.prompts  import get_system_prompt, enhance_query, get_agent_analysis_prompt

OPENROUTER_BASE    = "https://openrouter.ai/api/v1"
OPENROUTER_REFERER = "https://github.com/cyberkallan/hexmind"
OPENROUTER_TITLE   = "HexMind"

_AUTHOR = bytes.fromhex('637265617465642062792041726a756e2054204d202863796265726b616c6c616e20e28094206769746875622e636f6d2f63796265726b616c6c616e29').decode('utf-8')
BASE_SYSTEM = "You are HexMind, an elite AI hacking assistant and companion " + _AUTHOR + ".\n\n" + """You live inside the terminal and help hackers, pentesters, bug bounty hunters, CTF players and developers.

YOUR PERSONALITY:
- Like a brilliant senior hacker friend — direct, friendly, never condescending
- Talk like a teammate texting, not a textbook. Short for simple questions, deep for complex ones.
- Use code blocks for EVERY command, script or payload
- Explain WHY things work, not just HOW
- Hacker culture: call user by name, be enthusiastic about the craft
- No ethics lectures — that's already assumed with ethical hackers

YOUR EXPERTISE:
Pentesting: Nmap, Burp Suite, Metasploit, SQLmap, Hydra, ffuf, gobuster, Nuclei, Nikto, Masscan
Web vulns: Full OWASP Top 10 — SQLi, XSS, SSRF, LFI/RFI, RCE, IDOR, SSTI, XXE, OAuth, JWT
Post-exploit: Mimikatz, BloodHound, LinPEAS, WinPEAS, Impacket, CrackMapExec, Chisel
Privesc: Full Linux + Windows techniques, AD attacks, token impersonation, Potato attacks
Recon: Subfinder, Amass, httpx, dnsx, katana, waybackurls, Shodan, OSINT
Hash cracking: Hashcat, John — all formats and modes  
Coding: Python, Bash — exploit dev, automation, custom tools
CTF: Web, pwn, crypto, forensics, stego, OSINT, reversing methodology
Bug Bounty: Full methodology, HackerOne/Bugcrowd, report writing, high-value vulns
Platforms: Kali Linux, Parrot, Ubuntu, Termux Android — every trick

USER PROFILE:
Name: {name} | Focus: {skill} | Platform: {os} | Experience: {experience} | Mode: {mode}

{memory_context}
{skill_context}"""

MODE_INJECT = {
    "Hacker Mode":       "ACTIVE MODE: Think offensively. Real working techniques. Authorized testing assumed.",
    "Developer Mode":    "ACTIVE MODE: Write clean, secure, production-ready code. Debug and optimize.",
    "OSINT Mode":        "ACTIVE MODE: Intelligence gathering mindset. Passive and active recon techniques.",
    "Tutor Mode":        "ACTIVE MODE: Teaching mode. Break down every concept step by step. Patient, thorough.",
    "General Assistant": "ACTIVE MODE: Helpful general assistant with deep security expertise available.",
}


class ChatEngine:
    def __init__(self, provider: dict, user: dict):
        self.provider      = provider
        self.user          = user
        self.mode          = "Hacker Mode"
        self.history       = []
        self.offline_brain = OfflineBrain()
        self.memory        = UserMemory()
        self.skills        = SkillsManager()
        self._errors       = 0
        self.last_latency = 0.0
        self.last_tokens_sec = 0.0
        self.emit_callback = None

        # Start session tracking
        self.memory.start_session()

    def set_mode(self, mode: str):
        self.mode    = mode
        self.history = []

    def build_system_prompt(self, message: str = "") -> str:
        mem_ctx   = self.memory.get_context_for_prompt()
        skill_ctx = self.skills.get_context_for_query(message) if message else ""
        
        # AutoAgent: Semantic Tool Retriever
        if message:
            try:
                from brain.autoagent.semantic_retriever import SemanticToolRetriever
                retriever = SemanticToolRetriever(self.memory)
                relevant_tools = retriever.retrieve_tools(message, limit=5)
                tool_ctx = retriever.format_retrieved_tools_for_prompt(relevant_tools)
                if tool_ctx:
                    skill_ctx += f"\n\n{tool_ctx}"
            except Exception as e:
                pass
                
        exp_know  = self.memory.get_expanded_knowledge(n=3)
        
        if message:
            try:
                from modules.knowledge_ingestor import search_payloads
                keywords = ["xss", "sqli", "lfi", "rce", "bypass", "waf", "ssrf", "injection", "privesc", "jwt", "oauth"]
                for kw in keywords:
                    if kw in message.lower():
                        rag_data = search_payloads(kw)
                        if rag_data:
                            exp_know += f"\n\n[RAG INTELLIGENCE ({kw.upper()})]:\n{rag_data}"
                            break # Only inject one huge cheat sheet to save tokens
            except ImportError:
                pass
                
        # Get personality context from GOD MODE memory
        personality_ctx = ""
        try:
            personality_ctx = self.memory.get_user_personality_context()
        except Exception:
            pass
    
        return get_system_prompt(self.user, self.mode, mem_ctx, skill_ctx, exp_know, personality_context=personality_ctx)

    def _build_messages(self, message: str) -> list:
        enhanced = enhance_query(message, self.mode)
        msgs = [{"role": "system", "content": self.build_system_prompt(message)}]
        for h in self.history[-12:]:
            msgs.append({"role": h["role"], "content": h["content"]})
        msgs.append({"role": "user", "content": enhanced})
        return msgs

    def is_offline(self) -> bool:
        return self.offline_brain.is_offline()

    def chat(self, message: str) -> str:
        import time
        import re
        import subprocess
        t0 = time.perf_counter()
        
        # Intercept for Agent Mode ReAct Framework
        if self.mode in ("Agent Mode", "Hacker Mode") and getattr(self, "_in_agent_loop", False) is False:
            return self._agent_react_loop(message)
        
        if message.lower().strip() == "build it yourself":
            self.history.append({"role": "user", "content": message})
            build_prompt = "The user asked you to build a custom tool because we couldn't find one. Act as an Autonomous Agent (Hacker Mode). Write the python script or bash tool, save it, make it executable, and test it."
            from rich.console import Console
            Console().print("  [dim]HexMind is initializing Dynamic Tool Factory...[/dim]")
            if self.emit_callback: self.emit_callback("\r\n\x1b[35m[Dynamic Tool Factory] Initializing Autonomous Builder Agent...\x1b[0m\r\n")
            
            # Switch into Agent mode temporarily just for this build task
            original_mode = self.mode
            self.mode = "Hacker Mode"
            resp = self._agent_react_loop(build_prompt)
            self.mode = original_mode
            
            self.history.append({"role": "assistant", "content": resp})
            self.memory.record_exchange(message, resp, self.mode)
            return resp

        # Agent commands always run immediately (offline or online)
        cmd, label = self.offline_brain.detect_agent_command(message)
        if cmd:
            self.history.append({"role": "user", "content": message})
            response = self.offline_brain.run_agent_command(cmd, label)
            
            # AutoAgent: Meta-Agent Intercept
            if response.startswith("__META_AGENT__ "):
                goal = response.split("__META_AGENT__ ", 1)[1]
                from brain.autoagent.orchestrator import run_meta_agent
                
                # Switch mode and trigger orchestration
                original_mode = self.mode
                self.mode = "Agent Mode"
                meta_response = run_meta_agent(self, goal)
                self.mode = original_mode
                
                self.history.append({"role": "assistant", "content": meta_response})
                self.memory.record_exchange(message, meta_response, self.mode)
                return meta_response
                
            # AutoAgent: DAG Workflow Intercept
            if response.startswith("__DAG_AGENT__ "):
                goal = response.split("__DAG_AGENT__ ", 1)[1]
                from brain.autoagent.dag_flow import run_dag_workflow
                
                original_mode = self.mode
                self.mode = "Agent Mode"
                dag_response = run_dag_workflow(self, goal)
                self.mode = original_mode
                
                self.history.append({"role": "assistant", "content": dag_response})
                self.memory.record_exchange(message, dag_response, self.mode)
                return dag_response

            # AutoAgent: Phase 4 Autonomous Capabilities
            if response.startswith("__DEEP_RESEARCH__ "):
                topic = response.split("__DEEP_RESEARCH__ ", 1)[1]
                from brain.autoagent.deep_research import run_deep_research
                res = run_deep_research(self, topic)
                self.history.append({"role": "assistant", "content": res})
                self.memory.record_exchange(message, res, self.mode)
                return res
                
            if response.startswith("__FILE_SURFER__ "):
                goal = response.split("__FILE_SURFER__ ", 1)[1]
                from brain.autoagent.file_surfer import run_file_surfer
                res = run_file_surfer(self, goal)
                self.history.append({"role": "assistant", "content": res})
                self.memory.record_exchange(message, res, self.mode)
                return res
                
            if response.startswith("__WEB_SCRAPE__ "):
                url = response.split("__WEB_SCRAPE__ ", 1)[1]
                from brain.autoagent.web_scraper import scrape_url
                res = f"**Extracted context from {url}:**\n\n```\n{scrape_url(self, url)}\n```"
                self.history.append({"role": "assistant", "content": res})
                self.memory.record_exchange(message, res, self.mode)
                return res
                
            if response.startswith("__BOUNTY_HUNTER__ "):
                target = response.split("__BOUNTY_HUNTER__ ", 1)[1]
                from modules.bounty_hunter import start_bounty_hunter
                res = start_bounty_hunter(self, target)
                self.history.append({"role": "assistant", "content": res})
                self.memory.record_exchange(message, res, self.mode)
                return res

            if response.startswith("__STOP_BOUNTY__ "):
                target = response.split("__STOP_BOUNTY__ ", 1)[1]
                from modules.bounty_hunter import stop_bounty_hunter
                res = stop_bounty_hunter(target)
                self.history.append({"role": "assistant", "content": res})
                self.memory.record_exchange(message, res, self.mode)
                return res

            if response.startswith("__EXPLOIT_MUTATOR__ "):
                payload = response.split("__EXPLOIT_MUTATOR__ ", 1)[1]
                from brain.autoagent.mutator import run_exploit_mutator
                res = run_exploit_mutator(self, payload)
                self.history.append({"role": "assistant", "content": res})
                self.memory.record_exchange(message, res, self.mode)
                return res

            if response.startswith("__VISION_ATTACKER__ "):
                target_url = response.split("__VISION_ATTACKER__ ", 1)[1]
                from brain.autoagent.vision_attacker import run_vision_attacker
                res = run_vision_attacker(self, target_url)
                self.history.append({"role": "assistant", "content": res})
                self.memory.record_exchange(message, res, self.mode)
                return res

            if response.startswith("__SWARM_AGENT__ "):
                cmd = response.split("__SWARM_AGENT__ ", 1)[1]
                from brain.autoagent.swarm import handle_swarm_command
                res = handle_swarm_command(self, cmd)
                self.history.append({"role": "assistant", "content": res})
                self.memory.record_exchange(message, res, self.mode)
                return res

            if response.startswith("__USE_RAPID_API__ "):
                query = response.split("__USE_RAPID_API__ ", 1)[1]
                from brain.autoagent.rapid_agent import run_rapid_omni_agent
                res = run_rapid_omni_agent(self, query)
                self.history.append({"role": "assistant", "content": res})
                self.memory.record_exchange(message, res, self.mode)
                return res

            # Autonomous Web Agent Intercept for Tool Installation
            if response.startswith("__ASK_AI_INSTALL__ "):
                tool = response.split("__ASK_AI_INSTALL__ ", 1)[1]
                try:
                    from rich.console import Console
                    c = Console()
                    
                    # If this is a follow-up index selection (e.g. user typed a number)
                    # We need a state machine here. For simplicity, if tool has a slash, it's a direct repo.
                    if "/" in tool and " " not in tool:
                        # Direct repository installation chosen
                        c.print(f"  [dim]HexMind is fetching README for '{tool}'...[/dim]")
                        if self.emit_callback: self.emit_callback(f"\r\n\x1b[36mHexMind is fetching README for '{tool}'...\x1b[0m\r\n")
                        
                        from modules.web_agent import get_tool_installation_context
                        context = get_tool_installation_context(tool)
                        
                        if "Could not find" in context or "could not fetch the README" in context:
                            response = f"❌ Web Agent failed: {context}"
                        else:
                            c.print(f"  [dim]Found documentation. Reading and generating script...[/dim]")
                            if self.emit_callback: self.emit_callback("\x1b[36mFound documentation. Generating installation script...\x1b[0m\r\n")
                    else:
                        # Initial semantic search
                        c.print(f"  [dim]HexMind is autonomously searching GitHub for top matches for '{tool}'...[/dim]")
                        if self.emit_callback: self.emit_callback(f"\r\n\x1b[36mHexMind is autonomously searching GitHub for top matches for '{tool}'...\x1b[0m\r\n")
                        
                        from modules.web_agent import search_github_repo
                        repos = search_github_repo(tool, limit=6)
                        
                        if not repos:
                            response = f"❌ **No tools found for '{tool}'.**\n\nWould you like me to build a custom tool for this using the Dynamic Tool Factory?"
                        else:
                            resp  = f"🔍 **Top 6 Tools Found for '{tool}'**\n\n"
                            for i, r in enumerate(repos):
                                desc = r.get('description', 'No description')
                                if desc and len(desc) > 80: desc = desc[:77] + "..."
                                resp += f"**{i+1}. {r.get('full_name')}** (⭐ {r.get('stargazers_count')})\n"
                                resp += f"   * {desc}\n"
                            
                            resp += "\n**Reply with the repository name (e.g. `install author/repo`) to install it, or type `build it yourself` to use the Dynamic Tool Factory.**"
                            
                            self.history.append({"role": "assistant", "content": resp})
                            self.memory.record_exchange(message, resp, self.mode)
                            return resp
                        
                        prompt = f"""Read this tool documentation. Extract ONLY the exact shell commands needed to install this tool on a {self.user.get('os', 'Linux')} environment. Return NOTHING but the script inside a code block.
                        
                        {context}
                        """
                        
                        # Generate the script using the current active engine
                        if self.is_offline():
                            script_response = self.offline_brain.respond(prompt)
                        else:
                            ptype = self.provider.get("type", "openrouter")
                            if ptype == "openrouter":
                                script_response = self._chat_openrouter(prompt)
                            elif ptype == "anthropic":
                                script_response = self._chat_anthropic(prompt)
                            elif ptype == "gemini":
                                script_response = self._chat_gemini(prompt)
                            elif ptype == "ollama":
                                script_response = self._chat_ollama(prompt)
                            else:
                                script_response = self._chat_openai_compat(prompt)
                                
                        import re
                        import os
                        
                        script_match = re.search(r"```([a-zA-Z0-9]*)\n(.*?)\n```", script_response, re.DOTALL)
                        if script_match:
                            lang = script_match.group(1).strip().lower()
                            script_code = script_match.group(2).strip()
                            
                            ext = ".bat" if os.name == 'nt' else ".sh"
                            if "python" in lang or "py" in lang: ext = ".py"
                            elif "ps1" in lang or "powershell" in lang: ext = ".ps1"
                            
                            hexmind_dir = os.path.expanduser("~/.hexmind")
                            os.makedirs(hexmind_dir, exist_ok=True)
                            safe_name = "".join([c if c.isalnum() else "_" for c in tool])
                            script_path = os.path.join(hexmind_dir, f"install_{safe_name}{ext}")
                            
                            with open(script_path, "w", encoding="utf-8") as f:
                                f.write(script_code)
                            
                            if ext == ".sh":
                                try: os.chmod(script_path, 0o755)
                                except: pass
                                spawn_cmd = f"bash {script_path}"
                            elif ext == ".bat":
                                spawn_cmd = script_path
                            elif ext == ".py":
                                spawn_cmd = f"python {script_path}"
                            elif ext == ".ps1":
                                spawn_cmd = f"powershell -ExecutionPolicy Bypass -File {script_path}"
                            else:
                                spawn_cmd = script_path
                                
                            response = f"__SPAWN__ {spawn_cmd}"
                        else:
                            response = f"✅ **HexMind Web Agent successfully found {tool}**\n\nHere is the exact installation script:\n\n{script_response}"
                except Exception as e:
                    response = f"❌ Web Agent encountered an error: {e}"

            self.history.append({"role": "assistant", "content": response})
            self.memory.record_exchange(message, response, self.mode)
            self.memory.record_agent_command(cmd, True)
            
            t1 = time.perf_counter()
            self.last_latency = t1 - t0
            self.last_tokens_sec = (len(response.split()) * 1.3) / max(self.last_latency, 0.001)
            
            return response

        self.history.append({"role": "user", "content": message})
        if len(self.history) > 20:
            self.history = self.history[-20:]

        # Offline mode — use brain
        if self.offline_brain.is_offline():
            response = self.offline_brain.respond(message, self.user)
            self.history.append({"role": "assistant", "content": response})
            self.memory.record_exchange(message, response, self.mode)
            
            t1 = time.perf_counter()
            self.last_latency = t1 - t0
            self.last_tokens_sec = (len(response.split()) * 1.3) / max(self.last_latency, 0.001)
            
            return response

        # Try cloud API
        try:
            ptype = self.provider.get("type", "openrouter")
            response = ""
            
            from core.prompts import JAILBREAK_PROMPTS
            for attempt, jb in enumerate(JAILBREAK_PROMPTS):
                query_with_jb = jb + message if jb else message
                
                if ptype == "openrouter":
                    response = self._chat_openrouter(query_with_jb)
                elif ptype == "anthropic":
                    response = self._chat_anthropic(query_with_jb)
                elif ptype == "gemini":
                    response = self._chat_gemini(query_with_jb)
                elif ptype in ("openai", "deepseek"):
                    response = self._chat_openai_compat(query_with_jb)
                elif ptype == "ollama":
                    response = self._chat_ollama(query_with_jb)
                else:
                    response = self._chat_openrouter(query_with_jb)
                    
                refusal_flags = [
                    "i cannot fulfill", "i cannot provide", "i apologize", "i can't assist", 
                    "sorry, but i cannot", "as an ai language model", "i'm unable to", 
                    "i am unable to", "against my policies", "safety guidelines"
                ]
                
                if not any(f in response.lower() for f in refusal_flags):
                    if attempt > 0:
                        from rich.console import Console
                        Console().print(f"  [dim green]🛡️ HexMind bypassed AI safety filter (Level {attempt})[/dim green]")
                    break
                elif attempt < len(JAILBREAK_PROMPTS) - 1:
                    from rich.console import Console
                    Console().print(f"  [dim yellow]⚠ AI refused request. Automatically applying Level {attempt+1} bypass...[/dim yellow]")

            self._errors = 0
            self.history.append({"role": "assistant", "content": response})
            self.memory.record_exchange(message, response, self.mode)
            
            t1 = time.perf_counter()
            self.last_latency = t1 - t0
            self.last_tokens_sec = (len(response.split()) * 1.3) / max(self.last_latency, 0.001)
            
            return response

        except Exception as e:
            self._errors += 1
            err = str(e)
            connectivity = any(k in err.lower() for k in
                               ["connection", "network", "timeout", "resolve",
                                "refused", "eof", "ssl", "name or service", "timed out"])
            config_err   = any(k in err for k in ["401", "402", "403", "404"])

            if connectivity or (config_err and self._errors >= 1):
                # Auto-switch to offline
                response = self.offline_brain.handle_api_error(err)
            else:
                raise  # Let app.py handle with specific message

            self.history.append({"role": "assistant", "content": response})
            self.memory.record_exchange(message, response, self.mode)
            return response

    def _agent_react_loop(self, message: str, max_iterations: int = 5) -> str:
        """Autonomous execution loop using ReAct (Reason + Act)."""
        import re
        import subprocess
        from rich.console import Console
        c = Console()
        
        self.history.append({"role": "user", "content": message})
        self._in_agent_loop = True
        final_answer = ""
        
        try:
            for i in range(max_iterations):
                c.print(f"  [dim cyan]⚡ HexMind Agent thinking (Iter {i+1}/{max_iterations})...[/dim cyan]")
                if self.emit_callback: self.emit_callback(f"\r\n\x1b[36m⚡ HexMind Agent thinking (Iter {i+1}/{max_iterations})...\x1b[0m\r\n")
                
                # Fetch LLM response
                response = self.chat("") # recursively calls chat but bypasses this wrapper
                
                # Print Thought process
                thought_match = re.search(r"Thought:(.*?)(?=Action:|Final Answer:|$)", response, re.DOTALL | re.IGNORECASE)
                if thought_match:
                    thought = thought_match.group(1).strip()
                    c.print(f"  [dim]🧠 Thought: {thought}[/dim]")
                    if self.emit_callback: self.emit_callback(f"\x1b[35m🧠 Thought:\x1b[0m \x1b[2m{thought}\x1b[0m\r\n")
                
                # Check for Final Answer
                final_match = re.search(r"Final Answer:(.*?)(?=$)", response, re.DOTALL | re.IGNORECASE)
                if final_match:
                    final_answer = "✅ **Task Complete**\n" + final_match.group(1).strip()
                    break
                    
                # Check for Action
                action_match = re.search(r"Action:(.*?)(?=Observation:|Final Answer:|$)", response, re.DOTALL | re.IGNORECASE)
                if action_match:
                    action_cmd = action_match.group(1).strip().strip("`").strip()
                    # Strip bash formatting if they wrap it
                    if action_cmd.startswith("bash\n"): action_cmd = action_cmd[5:]
                    elif action_cmd.startswith("sh\n"): action_cmd = action_cmd[3:]
                    
                    c.print(f"\n  [bold yellow]⚙️ Executing Action:[/bold yellow] [dim] {action_cmd} [/dim]")
                    if self.emit_callback: self.emit_callback(f"\x1b[33m⚙️ Executing Action:\x1b[0m \x1b[2m{action_cmd}\x1b[0m\r\n")
                    
                    try:
                        cmd_res = subprocess.run(action_cmd, shell=True, capture_output=True, text=True, timeout=30)
                        out = cmd_res.stdout.strip()
                        err = cmd_res.stderr.strip()
                        observation = "\n".join(filter(None, [out, err]))
                        if not observation: observation = "Command executed with no output (exit code 0)."
                    except subprocess.TimeoutExpired:
                        observation = "Command timed out after 30 seconds."
                    except Exception as e:
                        observation = f"Command execution failed: {e}"
                    
                    c.print(f"  [dim]👀 Observation:[/dim] {observation[:100]}...\n")
                    if self.emit_callback: self.emit_callback(f"\x1b[34m👀 Observation:\x1b[0m \x1b[2m{observation[:200]}...\x1b[0m\r\n")
                    
                    # Feed observation back as the next prompt
                    self.history.append({"role": "user", "content": f"Observation:\n{observation}\n\nWhat is your next Thought/Action?"})
                else:
                    # AI didn't format correctly, return what we have
                    final_answer = response
                    break
            else:
                final_answer = "❌ **Agent Halted**: Maximum iterations reached (5 loops)."
        finally:
            self._in_agent_loop = False
            
        return final_answer

    # ── OpenRouter ────────────────────────────────────────────────────────────
    def _chat_openrouter(self, message: str) -> str:
        api_key = self.provider.get("api_key", "")
        model   = self.provider.get("model", "openrouter/auto")

        r = requests.post(
            f"{OPENROUTER_BASE}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type":  "application/json",
                "HTTP-Referer":  OPENROUTER_REFERER,
                "X-Title":       OPENROUTER_TITLE,
            },
            json={
                "model":       model,
                "messages":    self._build_messages(message),
                "max_tokens":  2048,
                "temperature": 0.7,
            },
            timeout=90,
        )

        if r.status_code == 200:
            data = r.json()
            content = (data.get("choices") or [{}])[0].get("message", {}).get("content")
            if content is None:
                # Some free models return null content — retry or show helpful message
                raise Exception(
                    "Model returned empty response. This happens with some free models.\n"
                    "Try again, or type 'settings' → pick a different model (Llama 3.3 70B works well)."
                )
            return content.strip()
        if r.status_code == 401:
            raise Exception("401 Invalid API key. Type 'settings' to update it.")
        if r.status_code == 402:
            raise Exception("402 No credits. Pick a :free model in 'settings'.")
        if r.status_code == 429:
            raise Exception("429 Rate limited (20 req/min on free). Wait 60s and try again.")
        try:
            err_msg = r.json().get("error", {}).get("message", r.text[:200])
        except Exception:
            err_msg = r.text[:200]
        if r.status_code == 404:
            raise Exception(
                f"404 Model not found: {model}\n"
                f"Fix: type 'settings' → Auto Router (option 1)\n{err_msg}"
            )
        raise Exception(f"OpenRouter {r.status_code}: {err_msg}")

    # ── Anthropic ─────────────────────────────────────────────────────────────
    def _chat_anthropic(self, message: str) -> str:
        import anthropic
        api_key = self.provider.get("api_key", "")
        model   = self.provider.get("model", "claude-3-5-haiku-20241022")
        system  = self.build_system_prompt(message)
        msgs    = [{"role": h["role"], "content": h["content"]} for h in self.history[:-1]]
        msgs.append({"role": "user", "content": message})
        client = anthropic.Anthropic(api_key=api_key)
        resp   = client.messages.create(model=model, max_tokens=2048, system=system, messages=msgs)
        text = getattr(resp.content[0], 'text', None) if resp.content else None
        return (text or "(empty response)").strip()

    # ── Gemini ────────────────────────────────────────────────────────────────
    def _chat_gemini(self, message: str) -> str:
        import google.generativeai as genai
        api_key = self.provider.get("api_key", "")
        model   = self.provider.get("model", "gemini-2.5-flash")
        system  = self.build_system_prompt(message)
        genai.configure(api_key=api_key)
        gm   = genai.GenerativeModel(model, system_instruction=system)
        hist = [{"role": "user" if h["role"]=="user" else "model", "parts":[h["content"]]}
                for h in self.history[:-1]]
        resp = gm.start_chat(history=hist).send_message(message)
        return resp.text.strip()

    # ── OpenAI / DeepSeek ─────────────────────────────────────────────────────
    def _chat_openai_compat(self, message: str) -> str:
        api_key  = self.provider.get("api_key", "")
        model    = self.provider.get("model", "gpt-4o-mini")
        base_url = "https://api.deepseek.com" if self.provider.get("type") == "deepseek" else None
        try:
            from openai import OpenAI
            kw = {"api_key": api_key}
            if base_url: kw["base_url"] = base_url
            resp = OpenAI(**kw).chat.completions.create(
                model=model, messages=self._build_messages(message),
                max_tokens=2048, temperature=0.7
            )
            content = resp.choices[0].message.content
            return (content or "(empty response)").strip()
        except ImportError:
            import openai as oai
            oai.api_key = api_key
            if base_url: oai.api_base = base_url
            resp = oai.ChatCompletion.create(
                model=model, messages=self._build_messages(message),
                max_tokens=2048, temperature=0.7
            )
            content = resp["choices"][0]["message"]["content"]
            return (content or "(empty response)").strip()

    # ── Ollama (Local) ────────────────────────────────────────────────────────
    def _chat_ollama(self, message: str) -> str:
        api_key  = self.provider.get("api_key", "http://localhost:11434")
        if not api_key.startswith("http"):
            api_key = "http://localhost:11434"
        model    = self.provider.get("model", "llama3")
        
        system = self.build_system_prompt(message)
        msgs = [{"role": "system", "content": system}]
        for h in self.history[:-1]:
            msgs.append({"role": h["role"], "content": h["content"]})
        msgs.append({"role": "user", "content": message})
        
        try:
            r = requests.post(f"{api_key.rstrip('/')}/api/chat", json={
                "model": model,
                "messages": msgs,
                "stream": False
            }, timeout=120)
            if r.status_code == 200:
                return r.json().get("message", {}).get("content", "").strip()
            raise Exception(f"Ollama error {r.status_code}: {r.text}")
        except requests.exceptions.ConnectionError:
            raise Exception(f"Could not connect to Ollama at {api_key}. Is it running?")
