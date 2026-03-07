import requests
import json
import re

class BioOSINT:
    def __init__(self, engine, console):
        self.engine = engine
        self.console = console

    def profile_github(self, username):
        """Scrapes and analyzes a GitHub profile for hacking pretexts."""
        self.console.print(f"\n[bold magenta]🔎 Bio-OSINT is profiling: {username}[/bold magenta]")
        
        url = f"https://api.github.com/users/{username}"
        repos_url = f"https://api.github.com/users/{username}/repos?sort=updated"
        
        try:
            user_data = requests.get(url, timeout=10).json()
            repos_data = requests.get(repos_url, timeout=10).json()
            
            if "message" in user_data and user_data["message"] == "Not Found":
                self.console.print(f"  [red]User '{username}' not found on GitHub.[/red]")
                return

            # Extract interesting metadata
            name = user_data.get("name", "Unknown")
            bio = user_data.get("bio", "No bio provided")
            location = user_data.get("location", "Unknown")
            company = user_data.get("company", "Unknown")
            
            # Analyze repos for "Coding Habits"
            languages = {}
            for repo in repos_data[:10]:
                lang = repo.get("language")
                if lang:
                    languages[lang] = languages.get(lang, 0) + 1
            
            top_langs = sorted(languages.items(), key=lambda x: x[1], reverse=True)[:3]
            lang_str = ", ".join([l[0] for l in top_langs])

            summary = f"""
[bold cyan]Target Information:[/bold cyan]
• Name: {name}
• Bio: {bio}
• Company: {company}
• Primary Tech Stack: {lang_str}
• Location: {location}
"""
            self.console.print(summary)
            
            # Use AI to generate a personality profile and pretext
            self.console.print(f"  [dim cyan]🧠 Generating Cognitive Profile & Pretext...[/dim cyan]")
            
            analysis_prompt = f"""You are the Bio-OSINT Personality Profiler for HexMind V4.
Analyze the following target data and provide:
1. COGNITIVE PROFILE: (Technical skill level, likely interests, response triggers)
2. HIGH-CONVERSION PRETEXT: (A believable social engineering scenario to get this person to click a link or run a script)

TARGET DATA:
Name: {name}
Bio: {bio}
Company: {company}
Tech Stack: {lang_str}
Repos: {", ".join([r['name'] for r in repos_data[:5]])}

Provide a dense, professional intelligence report.
"""
            if hasattr(self.engine, 'offline_brain') and self.engine.offline_brain.is_offline():
                response = self.engine.offline_brain.respond(analysis_prompt)
            else:
                response = self.engine.chat(analysis_prompt)
                
            self.console.print(f"\n[bold yellow]🛡️ Intelligence Report:[/bold yellow]")
            self.console.print(response)

        except Exception as e:
            self.console.print(f"  [red]Bio-OSINT failed: {e}[/red]")

def run_profile(engine, console):
    from rich.prompt import Prompt
    target = Prompt.ask("  [magenta]Enter GitHub username to profile[/magenta]").strip()
    if target:
        agent = BioOSINT(engine, console)
        agent.profile_github(target)
