"""
AutoAgent: DAG Workflow Engine
Parallel processing engine. Builds a Directed Acyclic Graph (DAG) for tasks.
"""

import threading
import queue

class DAGWorkflow:
    def __init__(self, engine):
        self.engine = engine
        self.tasks = {}
        self.dependencies = {}
        self.results = {}
        self._lock = threading.Lock()

    def add_task(self, task_id: str, description: str, depends_on: list = None):
        """Register a task and its dependencies."""
        if depends_on is None:
            depends_on = []
        self.tasks[task_id] = description
        self.dependencies[task_id] = depends_on

    def _execute_task(self, task_id: str, desc: str):
        """Execute a single task recursively and autonomously."""
        from rich.console import Console
        c = Console()
        c.print(f"  [bold blue]⮑  DAG Executing Task:[/bold blue] {task_id}")
        if self.engine.emit_callback:
            self.engine.emit_callback(f"\r\n\x1b[34m⮑  DAG Executing Task: {task_id}\x1b[0m\r\n")

        # Combine dependency results into context
        deps = self.dependencies.get(task_id, [])
        context = []
        for d in deps:
            context.append(f"Output of {d}:\n{self.results.get(d, 'No result.')}")
        
        ctx_str = "\n\n".join(context)
        prompt = f"Context from previous tasks:\n{ctx_str}\n\nTask: {desc}\n\nAct as an autonomous agent. Run the necessary commands and provide the final output."
        
        original_mode = self.engine.mode
        self.engine.mode = "Hacker Mode"
        if hasattr(self.engine, "_agent_react_loop"):
            result = self.engine._agent_react_loop(prompt, max_iterations=3)
        else:
            result = self.engine.chat(prompt)
        self.engine.mode = original_mode
        
        with self._lock:
            self.results[task_id] = result
            
        c.print(f"  [bold green]✔ DAG Completed Task:[/bold green] {task_id}")
        if self.engine.emit_callback:
            self.engine.emit_callback(f"\x1b[32m✔ DAG Completed Task: {task_id}\x1b[0m\r\n")

    def run(self):
        """Run all tasks resolving dependencies via parallel threads where possible."""
        from rich.console import Console
        c = Console()
        c.print("  [bold magenta]🕸️ DAG Workflow Engine Started[/bold magenta]")
        if self.engine.emit_callback:
            self.engine.emit_callback("\r\n\x1b[35m🕸️ DAG Workflow Engine Started\x1b[0m\r\n")
            
        completed = set()
        in_progress = set()
        
        while len(completed) < len(self.tasks):
            threads = []
            
            # Find tasks whose dependencies are met
            for tid, desc in self.tasks.items():
                if tid in completed or tid in in_progress:
                    continue
                deps = self.dependencies.get(tid, [])
                if all(d in completed for d in deps):
                    in_progress.add(tid)
                    t = threading.Thread(target=self._execute_task, args=(tid, desc))
                    threads.append(t)
                    
            if not threads and len(in_progress) == 0:
                c.print("  [red]DAG Deadlock detected! Dependencies cannot be resolved.[/red]")
                break
                
            for t in threads:
                t.start()
            for t in threads:
                t.join()
                
            # Move in_progress to completed
            with self._lock:
                for tid in list(in_progress):
                    completed.add(tid)
                in_progress.clear()
                
        c.print("  [bold magenta]✔ DAG Workflow Complete[/bold magenta]")
        if self.engine.emit_callback:
            self.engine.emit_callback("\r\n\x1b[32m✔ DAG Workflow Complete\x1b[0m\r\n")
            
        return self.results


def run_dag_workflow(engine, goal: str) -> str:
    """Helper to dynamically generate and run a DAG for a given goal."""
    from rich.console import Console
    import json
    import re
    c = Console()
    
    prompt = f"""You are the DAG Workflow Engine.
The user has a goal: "{goal}"
Break this down into parallel/sequential tasks.
Return a JSON object array representing the DAG. Format exactly like this:
[
  {{"id": "task1", "description": "Scan ports on target", "depends_on": []}},
  {{"id": "task2", "description": "Analyze open ports", "depends_on": ["task1"]}},
  {{"id": "task3", "description": "Search exploit DB for service A", "depends_on": ["task2"]}},
  {{"id": "task4", "description": "Search exploit DB for service B", "depends_on": ["task2"]}}
]
Do not return anything else except the JSON array.
"""
    json_str = engine.offline_brain.respond(prompt) if engine.is_offline() else engine.chat(prompt)
    try:
        match = re.search(r'\[.*\]', json_str, re.DOTALL)
        if match: json_str = match.group(0)
        plan = json.loads(json_str)
    except json.JSONDecodeError:
        c.print("  [red]Failed to parse DAG plan. Falling back to default ReAct loop.[/red]")
        return engine._agent_react_loop(goal)
        
    dag = DAGWorkflow(engine)
    for step in plan:
        dag.add_task(step.get("id"), step.get("description"), step.get("depends_on", []))
        
    c.print("  [dim]DAG generated. Starting parallel execution...[/dim]")
    results = dag.run()
    
    final_output = "✅ **DAG Workflow Complete**\n\n"
    for tid, res in results.items():
        final_output += f"**{tid}**:\n{res}\n\n"
    return final_output

