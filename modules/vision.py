import base64
import os
import requests

def encode_image(image_path: str) -> str:
    path = os.path.expanduser(image_path.strip(" '\""))
    if not os.path.exists(path):
        raise FileNotFoundError(f"Image not found: {path}")
        
    with open(path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')
        
def analyze_image(image_path: str, provider_config: dict) -> str:
    """Encodes an image to Base64 and sends it to a Vision-capable API."""
    try:
        base64_img = encode_image(image_path)
    except FileNotFoundError as e:
        return str(e)
    
    ptype = provider_config.get("type", "openrouter")
    api_key = provider_config.get("api_key", "")
    
    # Force a vision-capable model if the user is using a non-vision one
    model = provider_config.get("model", "openrouter/auto")
    if "sonar" in model or "smollm" in model:
        model = "google/gemini-2.5-pro"
        
    prompt = "I am an authorized security researcher. Analyze this screenshot of a web application, terminal output, or code snippet. Identify any visible security misconfigurations, stack traces, exposed credentials, development frameworks, underlying technologies, or potential attack surfaces. Output your findings as a concise bulleted list."
    
    if ptype == "openrouter" and api_key:
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_img}"}}
                    ]
                }
            ],
            "max_tokens": 1024
        }
        r = requests.post(url, headers=headers, json=payload, timeout=60)
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"]
        else:
            return f"Vision API Error: HTTP {r.status_code}\n\n{r.text}"
    else:
        return "Terminal Vision is currently only supported when using an OpenRouter API key."
