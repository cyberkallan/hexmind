<div align="center">

  <img src="HexMindLogo.png">

  # ⚡ HexMind v2.5.0 — God-Mode Edition

  **The Ultimate AI-Powered Autonomous Hacking & Security Companion**

  <br/>

  <!-- Premium CTA Buttons - Official Website & Documentation -->
  <a href="https://hexmind.space/">
    <img src="https://img.shields.io/badge/🌐_Official_Website-HexMind_Space-00d4ff?style=for-the-badge&logo=link&logoColor=white&labelColor=0a0a0f" alt="Official Website" />
  </a>
  <a href="https://hexmind.space/docs.html">
    <img src="https://img.shields.io/badge/📚_Documentation-Read_Docs-7c3aed?style=for-the-badge&logo=readthedocs&logoColor=white&labelColor=0a0a0f" alt="Documentation" />
  </a>

  <br/>
  <br/>

  <p>
    <strong>Download HexMind & Skills · Official Docs · One-Click Access</strong>
  </p>

  <br/>

  [![OS - Windows](https://img.shields.io/badge/OS-Windows-0078d6?style=flat-square&logo=windows&logoColor=white)](https://hexmind.space/)
  [![OS - Linux](https://img.shields.io/badge/OS-Linux-fcc624?style=flat-square&logo=linux&logoColor=black)](https://hexmind.space/)
  [![OS - Termux](https://img.shields.io/badge/OS-Termux-3ddc84?style=flat-square&logo=android&logoColor=white)](https://hexmind.space/)
  [![Python - 3.10+](https://img.shields.io/badge/Python-3.10+-3776ab?style=flat-square&logo=python&logoColor=white)](https://hexmind.space/)
  [![License - MIT](https://img.shields.io/badge/License-MIT-8b5cf6?style=flat-square)](https://hexmind.space/)

  <br/>

  <p align="center">
    <i>Built for Pentesters, Bug Bounty Hunters, and Cybersecurity Professionals.</i>
  </p>

</div>

---

<table>
<tr>
<td width="50%">

## 🔮 What is HexMind?

**HexMind** is a terminal-based and web-integrated AI agent designed for advanced cybersecurity operations. It goes beyond a standard chat wrapper—featuring a **ReAct Autonomous Engine**, premium Local/Cloud hybrid intelligence, and the **V7 God-Mode Web Command Center**.

Whether you're fuzzing endpoints, analyzing WAFs, exploiting binaries, or need an autonomous assistant to run scripts, HexMind delivers instant, high-fidelity security intelligence.

</td>
<td width="50%">

## 🔗 Official Links

| Resource | Link |
|----------|------|
| **Official Website** | [hexmind.space](https://hexmind.space/) |
| **Documentation** | [docs.html](https://hexmind.space/docs.html) |
| **Download HexMind** | [Get from Official Site](https://hexmind.space/) |
| **Skills & Modules** | [Browse on HexMind Space](https://hexmind.space/) |

</td>
</tr>
</table>

---

## 🚀 Key Capabilities

| Feature | Description |
|--------|-------------|
| **🧠 V9 AGI Core** | Type `agent` to activate the ReAct loop. HexMind breaks down objectives, generates scripts, executes them, and iteratively solves challenges autonomously. |
| **🌐 V7 God-Mode Command Center** | Premium glassmorphic UI in your browser with live reverse-streamed terminal and real-time CPU/RAM telemetry. |
| **📚 V8 Omniscience (RAG)** | Auto-clones PayloadsAllTheThings & HackTricks to local cache, injecting verified payloads to eliminate AI hallucination. |
| **🎭 Global Personas** | `persona <name>` overrides core programming with thousands of styles from awesome-chatgpt-prompts. |
| **💸 API Guard** | Connects to OpenRouter, Anthropic, Gemini, or OpenAI; routes token-heavy workloads to Local Offline Brain to save costs. |
| **📡 Zero-Day Sentinel** | Tails server logs and scans streams for anomalous activity and zero-day signatures. |
| **🛡️ Ghost Mode** | Deploys localized honeypots to confuse automated scanners on your target network. |

---

## 🛠️ Installation

### 💻 Windows & Linux

```bash
git clone https://github.com/cyberkallan/hexmind.git
cd hexmind
pip install -r requirements.txt
python hexmind.py
```

### 📱 Termux (Android)

HexMind is optimized for Termux with Android-compatible payloads.

```bash
pkg install python git
git clone https://github.com/cyberkallan/hexmind.git
cd hexmind
pip install rich prompt-toolkit requests flask flask-socketio psutil
python hexmind.py
```

> **Tip:** For Speech-To-Text (`voice`), install Termux API: `pkg install termux-api`

### 🌐 Download from Official Website

For the latest builds and skill packs, visit the official hub:

**[→ https://hexmind.space/](https://hexmind.space/)** · **[→ Documentation](https://hexmind.space/docs.html)**

---

## 💻 Command Reference

| Command | Action |
|---------|--------|
| `dashboard` / `portal` | Launch V7 Web Command Center (localhost:8888). |
| `agent` | Toggle ReAct Autonomous Execution Framework. |
| `persona <name>` | Adopt a personality (e.g. `persona Dan`). |
| `brain` | Install/load Offline Local LLM (Ollama/Llama). |
| `settings` | Cloud provider API key configuration. |
| `skills` / `skill` | Install custom skill modules and scripts. |
| `target <IP>` | Set active workspace and target. |
| `watch <file.log>` | Start Zero-Day Sentinel anomaly monitor. |
| `ghost` | Start honeypot & evasion server. |
| `voice` | Toggle Speech-To-Text / Text-To-Speech. |
| `!<cmd>` | Execute raw system command. |

---

## 🌐 V7 God-Mode Command Center

Entering `dashboard` spins up a **Premium Flask SPA**:

- **Glassmorphic UI** — Dark theme with cyberpunk aesthetics.
- **Live Terminal Sync** — Commands in the web UI stream to the backend via WebSockets and xterm.js.
- **System Telemetry** — Real-time hardware progress bars for operations.

---

## 🛡️ Local AI Brain (Free & Private)

Run HexMind fully offline for sensitive environments:

1. Type `brain` in the terminal.
2. Use local models from `smollm2:135m` (speed) to `llama3:8b` (reasoning).
3. Interpret pentesting, CTF, PrivEsc, and web vulns with no internet required.

---

<div align="center">

  **HexMind is continually evolving. Build your intelligence. Rule the terminal.**

  <br/>

  <a href="https://hexmind.space/">
    <img src="https://img.shields.io/badge/Official_Website-HexMind.Space-00d4ff?style=for-the-badge" alt="Official Website" />
  </a>
  <a href="https://hexmind.space/docs.html">
    <img src="https://img.shields.io/badge/Documentation-Read_Here-7c3aed?style=for-the-badge" alt="Documentation" />
  </a>

  <br/><br/>

  <sub><i>Use responsibly. You are solely responsible for your actions.</i></sub>

</div>
