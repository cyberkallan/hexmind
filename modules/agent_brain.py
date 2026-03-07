import re
import subprocess
import requests
import json
import time

AGENT_SYSTEM_PROMPT = """You are HexMind's True Autonomous Executor Agent.
Your objective is to accomplish the user's task using the terminal.
You must use a strict Reasoning & Acting (ReAct) loop.

FORMAT INSTRUCTIONS:
Always output your response in this EXACT format:

Thought: <your reasoning about what to do next>
Action:
```bash
<terminal command>
```

TOOL INSTALLATION INSTRUCTIONS:
If the user asks you to install a tool or repository, you must:
1. Search or clone the correct repository for the tool using `git clone`.
2. Observe the files (e.g., `ls -la`) to check for `requirements.txt`, `setup.py`, `package.json`, or a `Makefile`.
3. Run the appropriate installation command (e.g., `pip install -r requirements.txt`, `npm install`, etc.).
4. Once installed successfully, instruct the user to `cd` into the new repository folder or run `target <folder>`.

Keep your commands extremely safe but effective. You are running on the user's local machine.
When you are waiting for output, ONLY output the Thought and Action.
Do NOT output anything else. Do NOT include an Observation block (I will provide that to you).

When you have completely achieved the objective, output:
Thought: <final reasoning>
DONE
"""

def _call_api(messages: list, provider: dict) -> str:
    """Directly calls the configured API without touching main chat history."""
    ptype = provider.get("type", "openrouter")
    
    if ptype == "openrouter":
        api_key = provider.get("api_key", "")
        model   = provider.get("model", "openrouter/auto")
        r = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type":  "application/json",
            },
            json={
                "model": model,
                "messages": messages,
                "max_tokens": 1024,
                "temperature": 0.4,
            },
            timeout=90,
        )
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"].strip()
        else:
            raise Exception(f"API Error {r.status_code}: {r.text[:200]}")
    else:
        raise Exception("Agent Mode currently supports OpenRouter configured models.")

def extract_action(response: str) -> str:
    pattern = r'```(?:bash|sh|shell|console)?\n(.*?)```'
    matches = re.findall(pattern, response, re.IGNORECASE | re.DOTALL)
    if matches:
        return matches[-1].strip()
    return ""

def run_agent(objective: str, engine, console):
    console.print(f"\n[bold magenta]🤖 HexMind Autonomous Agent Started[/bold magenta]")
    console.print(f"Goal: [cyan]{objective}[/cyan]\n")
    
    provider = engine.provider
    if not provider or provider.get("type") != "openrouter":
        console.print("  [red]Agent Mode requires OpenRouter. Type 'settings' to configure.[/red]\n")
        return

    messages = [
        {"role": "system", "content": AGENT_SYSTEM_PROMPT},
        {"role": "user", "content": f"Objective: {objective}\nBegin."}
    ]
    
    max_steps = 10
    step = 0
    from rich.markdown import Markdown
    from rich.prompt import Confirm
    
    while step < max_steps:
        step += 1
        console.print(f"  [dim]Agent is thinking (Step {step}/{max_steps})...[/dim]")
        
        try:
            response = _call_api(messages, provider)
        except Exception as e:
            console.print(f"  [red]Agent Error: {e}[/red]\n")
            break
            
        messages.append({"role": "assistant", "content": response})
        
        # Display the agent's thought process
        console.print(f"\n[bold blue]🧠 Thought:[/bold blue]")
        thought_match = re.search(r"Thought:(.*?)(?:Action:|DONE|$)", response, re.IGNORECASE | re.DOTALL)
        if thought_match:
            console.print(thought_match.group(1).strip() + "\n")
        else:
            console.print(response + "\n")
            
        if "DONE" in response:
            console.print(f"  [bold green]✓ Agent completed the objective![/bold green]\n")
            break
            
        action = extract_action(response)
        if not action:
            # Provide an observation that no action was found so the model corrects itself
            messages.append({"role": "user", "content": "Observation: You didn't provide a bash action block. Please provide one if you need to run a command, or output DONE if finished."})
            continue
            
        console.print(f"  [bold yellow]⚡ Action Proposed:[/bold yellow]")
        console.print(f"  [cyan]{action}[/cyan]\n")
        
        if not Confirm.ask("  [yellow]Allow Agent to run this command?[/yellow]", default=True):
            console.print("  [red]Agent execution aborted by user.[/red]\n")
            break
            
        console.print("  [dim]Executing...[/dim]")
        try:
            r = subprocess.run(action, shell=True, capture_output=True, text=True, timeout=120)
            out = r.stdout.strip()
            err = r.stderr.strip()
            obs = f"STDOUT:\n{out}\nSTDERR:\n{err}" if out or err else "Command executed silently. (No output)"
        except subprocess.TimeoutExpired:
            obs = "Error: Command timed out after 120s."
        except Exception as e:
            obs = f"Error executing command: {e}"
            
        console.print(f"  [dim green]Observation captured ({len(obs)} chars).[/dim green]\n")
        
        # Truncate massive outputs to prevent context limits
        if len(obs) > 4000:
            obs = obs[:4000] + "\n...[truncated]..."
            
        messages.append({"role": "user", "content": f"Observation:\n{obs}"})
        
    if step >= max_steps:
        console.print("  [red]Agent reached maximum steps and was terminated.[/red]\n")
