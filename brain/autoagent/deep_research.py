"""
AutoAgent: Deep Research Loop (OpenAI o3 rival)
Orchestrates web searches, url scraping, and massive document synthesis.
"""

import json
from pathlib import Path
from .web_scraper import scrape_url

class DeepResearchAgent:
    def __init__(self, engine):
        self.engine = engine

    def research(self, topic: str) -> str:
        """Execute a deep multi-step research loop."""
        from rich.console import Console
        c = Console()
        c.print(f"\n  [bold cyan]🔬 Deep Research Initiated: {topic}[/bold cyan]")
        if self.engine.emit_callback:
            self.engine.emit_callback(f"\r\n\x1b[36m[Deep Research] Initiating profound analysis on: {topic}\x1b[0m\r\n")

        # Step 1: Brainstorm Search Queries
        query_prompt = f"We are doing deep research on: '{topic}'. Return a JSON array of 3 distinct, highly targeted Google search queries to gather comprehensive intel. Output ONLY the JSON array."
        queries_json = self.engine.offline_brain.respond(query_prompt) if self.engine.is_offline() else self.engine.chat(query_prompt)
        
        import re
        try:
            match = re.search(r'\[.*\]', queries_json, re.DOTALL)
            if match: queries_json = match.group(0)
            queries = json.loads(queries_json)
        except json.JSONDecodeError:
            queries = [topic, f"{topic} technical analysis", f"{topic} Github"]

        # Step 2: Execute Searches & Collect URLs
        from modules.web_agent import search_web
        all_content = []
        
        for idx, q in enumerate(queries[:3]):
            if self.engine.emit_callback:
                self.engine.emit_callback(f"\x1b[35m  Query {idx+1}: {q}\x1b[0m\r\n")
            results = search_web(q, num_results=2) # Get top 2 URLs per query
            for res in results:
                url = res.get('href')
                if url and "youtube.com" not in url:
                    text = scrape_url(self.engine, url)
                    if not text.startswith("Failed to scrape"):
                        all_content.append(f"Source ({url}):\n{text[:2000]}") # Only take first 2000 chars of each to save context

        # Step 3: Synthesis
        if self.engine.emit_callback:
            self.engine.emit_callback(f"\r\n\x1b[36m[Deep Research] Synthesizing {len(all_content)} data sources into a comprehensive markdown report...\x1b[0m\r\n")
            
        synthesis_prompt = f"""You are a Deep Research Agent (similar to OpenAI o3).
Topic: {topic}
RAW DATA COMPILED FROM {len(all_content)} SOURCES:
{'='*40}
{"\n\n".join(all_content)}
{'='*40}

Task: Write an exhaustive, elite-tier technical markdown report on the topic. 
Include an Executive Summary, Deep Technical Breakdown, Key Findings, and Actionable Takeaways.
Do not hallucinate. Base everything strictly on the provided research.
"""
        report = self.engine.offline_brain.respond(synthesis_prompt) if self.engine.is_offline() else self.engine.chat(synthesis_prompt)
        
        # Save to memory
        try:
            import hashlib
            slug = hashlib.md5(topic.encode()).hexdigest()[:8]
            filepath = Path.home() / ".hexmind" / "memory" / "learned" / f"deep_research_{slug}.md"
            filepath.parent.mkdir(parents=True, exist_ok=True)
            filepath.write_text(f"# {topic}\n\n{report}", encoding="utf-8")
            
            # Save into AutoAgent paper memory
            if hasattr(self.engine, "memory") and hasattr(self.engine.memory, "add_paper_memory"):
                self.engine.memory.add_paper_memory(
                    title=f"Deep Research: {topic}",
                    summary=report[:300] + "..."
                )
                
            footer = f"\n\n*Report autonomously generated and saved to {filepath.absolute()}*"
        except Exception as e:
            footer = f"\n\n*(Failed to save to disk: {e})*"

        if self.engine.emit_callback:
            self.engine.emit_callback("\r\n\x1b[32m✔ Deep Research Complete.\x1b[0m\r\n")
            
        return report + footer

def run_deep_research(engine, topic: str) -> str:
    agent = DeepResearchAgent(engine)
    return agent.research(topic)
