import urllib.request
import urllib.parse
from html.parser import HTMLParser

class FormParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.forms = []
        self.current_form = None

    def handle_starttag(self, tag, attrs):
        attr_dict = dict(attrs)
        if tag == "form":
            self.current_form = {
                "action": attr_dict.get("action", ""),
                "method": attr_dict.get("method", "get").upper(),
                "inputs": []
            }
            self.forms.append(self.current_form)
        elif tag in ("input", "textarea", "select") and self.current_form is not None:
            name = attr_dict.get("name")
            if name:
                self.current_form["inputs"].append({
                    "tag": tag,
                    "name": name,
                    "type": attr_dict.get("type", "text"),
                    "value": attr_dict.get("value", "")
                })

    def handle_endtag(self, tag):
        if tag == "form":
            self.current_form = None

def extract_forms(url: str):
    if not url.startswith("http"):
        url = "http://" + url
        
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode('utf-8', errors='ignore')
            
        parser = FormParser()
        parser.feed(html)
        return parser.forms
    except Exception as e:
        return f"Error fetching {url}: {e}"

def generate_exploit_payloads(url: str, engine, console):
    console.print(f"  [dim cyan]🕷️ Crawling {url} for attack surfaces...[/dim cyan]")
    forms = extract_forms(url)
    
    if isinstance(forms, str):
        console.print(f"  [red]{forms}[/red]")
        return
        
    if not forms:
        console.print("  [yellow]No HTML forms found on the target page.[/yellow]")
        return
        
    console.print(f"  [green]✓ Found {len(forms)} HTML form(s). Generating custom exploit payloads...[/green]\n")
    
    import json
    form_str = json.dumps(forms, indent=2)
    
    prompt = f"""I am conducting an authorized web application pentest on {url}. My crawler has identified the following HTML forms and parameters:

```json
{form_str}
```

Generate 3-4 specific, actionable exploitation commands (using curl, sqlmap, or ffuf) targeting EXACTLY these inputs. Focus on SQLi, XSS, or command injection payloads perfectly structured for these specific form 'name' fields and 'method' (GET/POST).

Return the exact bash commands in a ```bash block so I can execute them immediately."""
    
    res = engine.chat(prompt)
    from rich.markdown import Markdown
    console.print("\n[bold magenta]🕷️ Automated Web Exploitation Vectors:[/bold magenta]")
    console.print(Markdown(res, code_theme="monokai"))
