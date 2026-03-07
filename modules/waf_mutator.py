import urllib.parse

class WafMutator:
    def __init__(self, engine, console):
        self.engine = engine
        self.console = console

    def mutate_payload(self, baseline_payload):
        """Uses AI to generate 50 polymorphic variants of a payload."""
        self.console.print(f"\n[bold yellow]🧬 Mutating Payload for WAF Evasion...[/bold yellow]")
        self.console.print(f"  [dim]Baseline: {baseline_payload}[/dim]")

        prompt = f"""You are the HexMind V5 Smart Mutator.
Your goal is to take a hacking payload and generate 50 unique variations that bypass modern WAFs (Cloudflare, AWS, etc.).

BASELINE PAYLOAD: {baseline_payload}

TECHNIQUES TO USE:
1. URL Encoding (Double, partial)
2. Hex/Octal/Unicode normalization conversion
3. Comments obfuscation (e.g. /*!50000...*/)
4. Whitespace randomization (%0A, %0D, %09)
5. Case randomization (sElEcT)
6. Null byte injection

Provide exactly 50 variants, one per line. No explanations.
"""

        try:
            if hasattr(self.engine, 'offline_brain') and self.engine.offline_brain.is_offline():
                response = self.engine.offline_brain.respond(prompt)
            else:
                response = self.engine.chat(prompt)
            
            variants = [v.strip() for v in response.split("\n") if v.strip() and len(v) > 2]
            
            self.console.print(f"  [bold green]✅ Generated {len(variants)} unique variants.[/bold green]")
            return variants
        except Exception as e:
            self.console.print(f"  [red]Mutation failed: {e}[/red]")
            return []

def run_mutator(engine, console):
    from rich.prompt import Prompt
    payload = Prompt.ask("  [yellow]Enter baseline payload (e.g. ' OR 1=1 --)[/yellow]").strip()
    if payload:
        mutator = WafMutator(engine, console)
        variants = mutator.mutate_payload(payload)
        
        # Display first 5
        if variants:
            self.console.print("\n[bold cyan]Top 5 Mutations:[/bold cyan]")
            for v in variants[:5]:
                self.console.print(f"  • {v}")
            self.console.print(f"  [dim]... and {len(variants)-5} more.[/dim]\n")
