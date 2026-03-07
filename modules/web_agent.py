import urllib.request
import urllib.parse
import json
import re
from html.parser import HTMLParser

class TextParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text = []
        self.in_script = False
        
    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.in_script = True

    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self.in_script = False

    def handle_data(self, data):
        if not self.in_script:
            cleaned = data.strip()
            if cleaned:
                self.text.append(cleaned)

def extract_text(html):
    parser = TextParser()
    try:
        parser.feed(html)
        return " ".join(parser.text)
    except:
        return ""

def search_duckduckgo(query: str, max_results=3) -> str:
    """Lightweight scraper for html.duckduckgo.com"""
    try:
        url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(query)
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode('utf-8', errors='ignore')
            
        # Very simple regex to extract result snippets
        results = []
        pattern = r'<a class="result__snippet[^>]+>(.*?)</a>'
        snippets = re.findall(pattern, html, re.IGNORECASE | re.DOTALL)
        
        for s in snippets[:max_results]:
            # Clean HTML tags from the snippet
            text = extract_text(s)
            if text:
                results.append(text)
                
        if not results:
            return "No text results found."
            
        return "\n---\n".join(results)
    except Exception as e:
        return f"Web search failed: {e}"

def search_web(query: str, num_results=3) -> list:
    """Returns a list of dicts with 'href' and 'title' from DuckDuckGo HTML."""
    try:
        url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(query)
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode('utf-8', errors='ignore')
            
        results = []
        pattern = r'<a class="result__url" href="([^"]+)">(.*?)</a>'
        matches = re.findall(pattern, html, re.IGNORECASE)
        
        for m in matches[:num_results]:
            # DuckDuckGo sometimes prepends '/url?q='
            href = m[0]
            if href.startswith('//'): href = 'https:' + href
            if '/url?q=' in href: href = urllib.parse.unquote(href.split('/url?q=')[1].split('&')[0])
            title = extract_text(m[1])
            results.append({"href": href, "title": title})
            
        return results
    except Exception:
        return []

def search_github_repo(tool_name: str, limit: int = 6) -> list:
    """Search GitHub API for the most relevant repos and return Top 6."""
    try:
        url = f"https://api.github.com/search/repositories?q={urllib.parse.quote(tool_name)}&sort=stars&order=desc"
        req = urllib.request.Request(url, headers={'User-Agent': 'HexMind-Agent'})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
            items = data.get("items", [])
            if not items:
                return []
            return items[:limit]
    except Exception:
        return []

def fetch_github_readme(full_name: str, branch="master") -> str:
    """Fetch the raw README for a repo."""
    try:
        # Try main first, then master
        for b in ["main", "master"]:
            url = f"https://raw.githubusercontent.com/{full_name}/{b}/README.md"
            req = urllib.request.Request(url, headers={'User-Agent': 'HexMind-Agent'})
            try:
                with urllib.request.urlopen(req, timeout=10) as response:
                    return response.read().decode('utf-8', errors='ignore')
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    continue
                break
        return ""
    except Exception:
        return ""

def get_tool_installation_context(full_name: str) -> str:
    """Takes a specific full_name (e.g. 'sqlmapproject/sqlmap') and fetches its README for installation instructions."""
    try:
        url = f"https://api.github.com/repos/{full_name}"
        req = urllib.request.Request(url, headers={'User-Agent': 'HexMind-Agent'})
        with urllib.request.urlopen(req, timeout=10) as response:
            repo = json.loads(response.read().decode('utf-8'))
            desc = repo.get("description", "No description")
            
        readme = fetch_github_readme(full_name)
        if not readme:
            return f"Found repo {full_name} ({desc}), but could not fetch the README."
            
        # Truncate README if it's absurdly huge to save tokens
        if len(readme) > 15000:
            readme = readme[:15000] + "\n...[truncated]..."
            
        return f"Repository: {full_name}\nDescription: {desc}\n\nREADME:\n{readme}"
    except Exception as e:
        return f"Failed to fetch data for {full_name}: {e}"
