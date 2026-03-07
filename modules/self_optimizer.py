import os
import sys
import time
import functools
import inspect

# Global registry for tracked functions
TRACKED_FUNCTIONS = {}

def profile_me(func):
    """Decorator to mark a function for V6 Self-Optimization."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        end = time.perf_counter()
        
        duration = end - start
        func_name = f"{func.__module__}.{func.__name__}"
        
        if func_name not in TRACKED_FUNCTIONS:
            TRACKED_FUNCTIONS[func_name] = {"calls": 0, "total_time": 0, "source": inspect.getsource(func)}
            
        TRACKED_FUNCTIONS[func_name]["calls"] += 1
        TRACKED_FUNCTIONS[func_name]["total_time"] += duration
        
        return result
    return wrapper

class SelfOptimizer:
    def __init__(self, engine, console):
        self.engine = engine
        self.console = console

    def analyze_performance(self):
        """Identifies lagging functions and proposes optimized replacements."""
        self.console.print("\n[bold cyan]🧬 HexMind V6 Recursive Self-Optimization initiated...[/bold cyan]")
        
        to_optimize = []
        for name, data in TRACKED_FUNCTIONS.items():
            avg_time = data["total_time"] / data["calls"]
            # Heuristic: if avg time > 0.5s and called multiple times, optimize it.
            if avg_time > 0.5 and data["calls"] > 1:
                to_optimize.append((name, avg_time, data["source"]))

        if not to_optimize:
            self.console.print("  [dim]No performance bottlenecks detected in current session.[/dim]")
            return

        for name, avg, source in to_optimize:
            self.console.print(f"  [bold yellow]⚠ Bottleneck detected:[/bold yellow] {name} (Avg: {avg:.2f}s)")
            self._propose_optimization(name, source)

    def _propose_optimization(self, func_name, source):
        self.console.print(f"  [cyan]🧠 AI is refactoring {func_name} for maximum speed...[/cyan]")
        
        prompt = f"""You are the HexMind V6 Self-Optimization Engine.
I have detected a performance bottleneck in the following Python function.

FUNCTION NAME: {func_name}
CURRENT SOURCE:
{source}

MISSION:
1. Provide a REWRITTEN version of this function that is significantly more efficient.
2. If possible, suggest an algorithmic improvement (e.g. O(N) instead of O(N^2)).
3. If the function does heavy I/O or math, suggest using a more efficient library or native calls.

Output ONLY the refactored code in a python block.
"""

        try:
            if hasattr(self.engine, 'offline_brain') and self.engine.offline_brain.is_offline():
                optimized_code = self.engine.offline_brain.respond(prompt)
            else:
                optimized_code = self.engine.chat(prompt)
                
            self.console.print(f"\n[bold green]✅ Optimized Refactor for {func_name}:[/bold green]")
            from rich.panel import Panel
            self.console.print(Panel(optimized_code, border_style="green"))
            
            # Application logic: similar to Self-Repair, we'd allow the user to apply this as a patch.
            self.console.print(f"  [dim]Optimized version ready for deployment to {func_name}.[/dim]")
        except Exception as e:
            self.console.print(f"  [red]Optimization failed: {e}[/red]")

def run_optimization(engine, console):
    optimizer = SelfOptimizer(engine, console)
    optimizer.analyze_performance()
