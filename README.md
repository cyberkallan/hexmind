<div align="center">
  <img src="https://raw.githubusercontent.com/cyberkallan/hexmind/main/web/static/img/hexmind-logo.png" alt="HexMind Logo" width="200"/>
  
  # ⚡ HexMind v3.0 (God-Mode Edition)
  
  **The Ultimate AI-Powered Autonomous Hacking & Security Companion**

  [![OS - Windows](https://img.shields.io/badge/OS-Windows-blue?logo=windows&logoColor=white)](https://)
  [![OS - Linux](https://img.shields.io/badge/OS-Linux-black?logo=linux&logoColor=white)](https://)
  [![OS - Termux](https://img.shields.io/badge/OS-Termux-green?logo=android&logoColor=white)](https://)
  [![Python - 3.10+](https://img.shields.io/badge/Python-3.10+-yellow?logo=python&logoColor=white)](https://)
  [![License - MIT](https://img.shields.io/badge/License-MIT-blueviolet)](https://)
  
  <p align="center">
    Built for Pentesters, Bug Bounty Hunters, and Cybersecurity Professionals.
  </p>

</div>

---

## 🔮 What is HexMind?

**HexMind** is a terminal-based and web-integrated AI agent designed specifically for advanced cybersecurity operations. It goes far beyond a standard chat wrapper—HexMind features a **ReAct Autonomous Engine**, a premium Local/Cloud hybrid intelligence system, and a **V7 "God-Mode" Web Command Center**.

Whether you are fuzzing endpoints, analyzing WAFs, exploiting binaries, or looking for an autonomous assistant to run scripts for you, HexMind provides instant, high-fidelity security intelligence.

## 🚀 Key Capabilities

- **🧠 V9 AGI Core (Autonomous Agent):** Type `agent` to activate the ReAct loop. HexMind will break down your objective, generate scripts, execute them, read the output, and iteratively solve challenges entirely on its own.
- **🌐 V7 God-Mode Command Center:** A premium, glassmorphic UI accessible via your browser. Features a live reverse-streamed terminal and real-time CPU/RAM hardware telemetry.
- **📚 V8 Omniscience (RAG Intelligence):** Automatically clones `PayloadsAllTheThings` and `HackTricks` to the local cache, injecting verified payloads into its prompt context to completely eliminate AI hallucination.
- **🎭 Global Personas:** Type `persona <name>` to override HexMind's core programming with thousands of communication styles from `awesome-chatgpt-prompts`.
- **💸 API Guard:** HexMind connects to OpenRouter, Anthropic, Gemini, or OpenAI. It automatically detects token-heavy workloads and safely routes you to the **Local Offline Brain** to save costs.
- **📡 Zero-Day Sentinel:** Actively tail and monitor server logs. HexMind's brain scans incoming streams for anomalous activity and zero-day signatures automatically.
- **🛡️ Ghost Mode**: Deploys localized honeypots to confuse automated scanners on your target network.

---

## 🛠️ Installation

### 💻 Windows & Linux
```bash
git clone https://github.com/cyberkallan/hexmind.git
cd hexmind
pip install -r requirements.txt
python hexmind.py
```

### 📱 Termux (Android Mobile Hacking)
HexMind is fully optimized for Termux, detecting the environment and delivering Android-compatible payloads.
```bash
pkg install python git
git clone https://github.com/cyberkallan/hexmind.git
cd hexmind
pip install rich prompt-toolkit requests flask flask-socketio psutil
python hexmind.py
```
*Note: Some premium features like Speech-To-Text (`voice`) may require additional Termux API packages (`pkg install termux-api`).*

---

## 💻 Full Feature Command List

Inside the HexMind terminal, type any of these triggers:

| Command | Action / Module |
|---------|-----------------|
| `dashboard` / `portal` | Launches the V7 Web Command Center (Localhost:8888). |
| `agent` | Toggles the ReAct Autonomous Execution Framework. |
| `persona <name>` | Adopts a specific personality (e.g., `persona Dan`). |
| `brain` | Installs/Loads the Offline Local LLM (Ollama/Llama). |
| `settings` | Cloud Provider API Key configuration menu. |
| `skills` / `skill` | Install custom skill modules and scripts. |
| `target <IP>` | Set the active workspace and target for operations. |
| `watch <file.log>` | Start the Zero-Day Sentinel anomaly monitor. |
| `ghost` | Start the active honeypot & evasion server. |
| `voice` | Toggle hands-free Speech-To-Text / Text-To-Speech. |
| `!<cmd>` | Execute a raw system command directly. |

---

## 🌐 The God-Mode Command Center (V7 UI)

Forget basic CLI tools. Entering `dashboard` spins up a **Premium Flask SPA**:
- **Glassmorphic Design:** A sleek, dark-themed UI with cyberpunk aesthetics.
- **Live Terminal Sync:** Every command typed in the web UI streams flawlessly to the terminal backend using `WebSockets` and `xterm.js`.
- **System Telemetry:** Real-time hardware progress bars monitor the intense workloads HexMind handles during operations.

---

## 🛡️ The Local AI Brain (Free & Private)

HexMind operates powerfully offline. If the Cloud API drops or you are dealing with highly sensitive data:
1. Type `brain` in the terminal.
2. HexMind will utilize local models ranging from `smollm2:135m` (extreme speed) to `llama3:8b` (deep reasoning).
3. The Local Brain seamlessly interprets pentesting, CTF methodology, PrivEsc, and web vulnerabilities completely detached from the internet.

---

<div align="center">
  <b>HexMind is continually evolving. Build your intelligence. Rule the terminal.</b><br>
  <i>Use responsibly. You are solely responsible for your actions.</i>
</div>
