"""
AutoAgent: Web Scraper & Synthesizer Agent
Advanced web scraping integration for Intelligence extraction.
"""

import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urlparse

class WebScraperAgent:
    def __init__(self, engine):
        self.engine = engine
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        })

    def fetch_and_extract(self, url: str) -> str:
        """Fetch a URL and extract meaningful text content."""
        if self.engine.emit_callback:
            self.engine.emit_callback(f"\r\n\x1b[36m[WebScraper] Fetching: {url}\x1b[0m\r\n")
            
        try:
            resp = self.session.get(url, timeout=10)
            resp.raise_for_status()
            
            soup = BeautifulSoup(resp.text, "html.parser")
            
            # Remove junk elements
            for el in soup(["script", "style", "nav", "footer", "header", "aside"]):
                el.decompose()
                
            text = soup.get_text(separator="\n")
            
            # Clean up excessive whitespace
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            cleaned_text = "\n".join(lines)
            
            if len(cleaned_text) > 8000:
                cleaned_text = cleaned_text[:8000] + "\n...[TRUNCATED]"
                
            if self.engine.emit_callback:
                self.engine.emit_callback(f"\x1b[32m✔ Extraction complete ({len(cleaned_text)} chars).\x1b[0m\r\n")
                
            return cleaned_text
            
        except Exception as e:
            err = f"Failed to scrape {url}: {e}"
            if self.engine.emit_callback:
                self.engine.emit_callback(f"\x1b[31m✖ {err}\x1b[0m\r\n")
            return err

def scrape_url(engine, url: str) -> str:
    agent = WebScraperAgent(engine)
    return agent.fetch_and_extract(url)
