"""
AutoAgent: File Surfer Agent
Autonomous filesystem navigation and analysis without user input.
"""

import os
from pathlib import Path

class FileSurferAgent:
    def __init__(self, engine, start_dir=None):
        self.engine = engine
        self.current_dir = Path(start_dir) if start_dir else Path.cwd()

    def surf(self, goal: str) -> str:
        """
        Takes a goal like "Find the database password in this project"
        and autonomously `cd`, `ls`, and `cat` files until it finds the answer.
        """
        if self.engine.emit_callback:
            self.engine.emit_callback(f"\r\n\x1b[35m[File Surfer] Commencing search for: {goal}\x1b[0m\r\n")

        prompt = f"""You are the File Surfer Agent.
Goal: {goal}
Current Directory: {self.current_dir.absolute()}

You have autonomous control over the terminal. Use `ls`, `cat`, `grep`, and `cd` commands
to navigate the filesystem and locate the necessary information.
Think step-by-step. If a file is too large, use `head` or `grep`.
Do NOT stop until you achieve the goal or determine it's impossible.
"""
        # Save previous mode and force Hacker Mode (ReAct framework)
        original_mode = self.engine.mode
        self.engine.mode = "Hacker Mode"
        
        # Call the auto-retry ReAct loop
        if hasattr(self.engine, "_agent_react_loop"):
            result = self.engine._agent_react_loop(prompt, max_iterations=10)
        else:
            result = self.engine.chat(prompt)
            
        self.engine.mode = original_mode
        
        if self.engine.emit_callback:
            self.engine.emit_callback(f"\r\n\x1b[32m✔ [File Surfer] Search complete.\x1b[0m\r\n")
            
        return result

def run_file_surfer(engine, goal: str, path: str = None) -> str:
    agent = FileSurferAgent(engine, path)
    return agent.surf(goal)
