"""
AutoAgent: Meta-Agent Orchestrator
Breaks down complex goals into sub-tasks and assigns them to specialized agents.
"""

import re
import json
from collections import deque

class SubAgent:
    def __init__(self, name: str, role: str, chat_engine):
        self.name = name
        self.role = role
        self.engine = chat_engine

    def execute(self, task: str) -> str:
        """Run a single sub-agent execution loop."""
        # Temporarily inject the sub-agent's role into the system prompt context
        original_mode = self.engine.mode
        self.engine.mode = "Agent Mode"
        
        # We append a stark directive so the ReAct loop knows its specific specialty
        directive = f"You are the {self.name}. Your role is: {self.role}.\nTask: {task}"
        
        # Ideally, we call the _agent_react_loop directly
        if hasattr(self.engine, "_agent_react_loop"):
            result = self.engine._agent_react_loop(directive, max_iterations=5)
        else:
            result = self.engine.chat(directive)
            
        self.engine.mode = original_mode
        return result


class MetaAgent:
    def __init__(self, engine):
        self.engine = engine
        
        # Predefined hyper-specialized sub-agents
        self.sub_agents = {
            "ReconAgent": SubAgent("ReconAgent", "Gather intelligence, scan ports, enumerate directories. Do NOT exploit.", engine),
            "ExploitAgent": SubAgent("ExploitAgent", "Analyze vulnerabilities and execute safe authorized exploits.", engine),
            "ReportAgent": SubAgent("ReportAgent", "Synthesize findings into clean, professional markdown reports.", engine),
            "DevAgent": SubAgent("DevAgent", "Write, debug and optimize Python or Bash scripts.", engine)
        }

    def orchestrate(self, global_goal: str) -> str:
        """
        The Meta-Agent parses the user's objective, breaks it down, and assigns tasks to sub-agents.
        """
        from rich.console import Console
        c = Console()
        c.print(f"  [bold magenta]👑 Meta-Agent Orchestrator Initiated[/bold magenta]")
        if self.engine.emit_callback:
            self.engine.emit_callback("\r\n\x1b[35m[Meta-Agent] Analyzing complex objective...\x1b[0m\r\n")

        # 1. Ask the LLM to break down the task
        prompt = f"""You are the Meta-Agent Orchestrator. 
The user has a complex objective: "{global_goal}"

Available Sub-Agents:
- ReconAgent: Passive & active reconnaissance.
- ExploitAgent: Vulnerability exploitation.
- ReportAgent: Summarizing and documenting.
- DevAgent: Writing code/tools.

Return a JSON array of tasks required to achieve the objective in sequential order.
Format strictly as JSON:
[
  {{"agent": "ReconAgent", "task": "Scan ports on target"}},
  {{"agent": "ExploitAgent", "task": "Exploit identified open service"}}
]
Do not include any other text besides the JSON array.
"""
        plan_json_str = self.engine.offline_brain.respond(prompt) if self.engine.is_offline() else self.engine.chat(prompt)
        
        # Clean up JSON formatting
        try:
            match = re.search(r'\[.*\]', plan_json_str, re.DOTALL)
            if match:
                plan_json_str = match.group(0)
            plan = json.loads(plan_json_str)
        except json.JSONDecodeError:
            c.print("  [red]Failed to parse Meta-Agent plan. Falling back to default execution.[/red]")
            return self.engine._agent_react_loop(global_goal)

        c.print("  [dim]Meta-Agent generated plan:[/dim]")
        for idx, step in enumerate(plan):
            c.print(f"    {idx+1}. [{step.get('agent', 'Unknown')}] {step.get('task', '')}")
            if self.engine.emit_callback:
                self.engine.emit_callback(f"\x1b[36m  Step {idx+1}: [{step.get('agent')}] {step.get('task')}\x1b[0m\r\n")

        # 2. Execute tasks sequentially
        results = []
        for step in plan:
            agent_name = step.get("agent")
            task_desc = step.get("task")
            if agent_name in self.sub_agents:
                c.print(f"\n  [bold cyan]▶ Handing off to {agent_name}...[/bold cyan]")
                if self.engine.emit_callback:
                    self.engine.emit_callback(f"\r\n\x1b[35m▶ Handing off to {agent_name}...\x1b[0m\r\n")
                
                # Feed previous results as context
                context = "\n".join(results[-2:]) if results else "No prior context."
                full_task = f"Prior Context:\n{context}\n\nYour Task: {task_desc}"
                
                sub_result = self.sub_agents[agent_name].execute(full_task)
                results.append(f"Result from {agent_name}: {sub_result}")
            else:
                results.append(f"Skipped unknown agent: {agent_name}")

        final_summary = "\n\n".join(results)
        
        # 3. Final aggregation (optional)
        if self.engine.emit_callback:
            self.engine.emit_callback("\r\n\x1b[32m✔ Meta-Agent execution complete.\x1b[0m\r\n")
            
        return "✅ **Meta-Agent Execution Complete**\n\n" + final_summary

def run_meta_agent(engine, goal: str) -> str:
    orchestrator = MetaAgent(engine)
    return orchestrator.orchestrate(goal)
