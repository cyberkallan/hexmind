// ═══════════════════════════════════════════════════════════════════════════
// HexMind V13 Frontend — Complete Dashboard Logic
// Features: Auto-scroll, Voice Control, WebSocket Reconnect, Typing Indicator
// ═══════════════════════════════════════════════════════════════════════════

const term = new Terminal({
    cursorBlink: true,
    fontFamily: '"JetBrains Mono", monospace',
    fontSize: 14,
    theme: {
        background: 'transparent',
        foreground: '#f0f6fc',
        cursor: '#00ff88',
        selection: 'rgba(0, 255, 136, 0.3)',
        black: '#1a1a2e',
        red: '#ff5555',
        green: '#50fa7b',
        yellow: '#f1fa8c',
        blue: '#6272a4',
        magenta: '#ff79c6',
        cyan: '#8be9fd',
        white: '#f8f8f2',
    },
    scrollback: 5000,
    convertEol: true
});

const fitAddon = new FitAddon.FitAddon();
term.loadAddon(fitAddon);

let socket = null;
let cpuChart = null;
let ramChart = null;
let reconnectAttempts = 0;
const MAX_RECONNECT = 10;

// ── Charts ──────────────────────────────────────────────────────────────
function initCharts() {
    const commonOptions = {
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 0 },
        scales: {
            x: { display: false },
            y: { min: 0, max: 100, display: true, grid: { color: 'rgba(255,255,255,0.08)' }, border: { dash: [4, 4] }, ticks: { font: { size: 9 }, color: '#8b949e' } }
        },
        plugins: { legend: { display: false }, tooltip: { enabled: false } },
        elements: { point: { radius: 0 } }
    };

    const ctxCpu = document.getElementById('cpuChart');
    if (ctxCpu) {
        cpuChart = new Chart(ctxCpu.getContext('2d'), {
            type: 'line',
            data: {
                labels: Array(30).fill(''),
                datasets: [{ label: 'CPU', data: Array(30).fill(0), borderColor: '#00ff88', backgroundColor: 'rgba(0,255,136,0.08)', borderWidth: 1.5, fill: true, tension: 0.4 }]
            },
            options: commonOptions
        });
    }

    const ctxRam = document.getElementById('ramChart');
    if (ctxRam) {
        ramChart = new Chart(ctxRam.getContext('2d'), {
            type: 'line',
            data: {
                labels: Array(30).fill(''),
                datasets: [{ label: 'RAM', data: Array(30).fill(0), borderColor: '#00ccff', backgroundColor: 'rgba(0,204,255,0.08)', borderWidth: 1.5, fill: true, tension: 0.4 }]
            },
            options: commonOptions
        });
    }
}

// ══════════════════════════════════════════════════════════════════════════
// VOICE CONTROL — Browser Web Speech API
// ══════════════════════════════════════════════════════════════════════════
class VoiceController {
    constructor() {
        this.recognition = null;
        this.isListening = false;
        this.btn = document.getElementById('voiceToggle');
        this.supported = ('webkitSpeechRecognition' in window) || ('SpeechRecognition' in window);

        if (this.btn) {
            this.btn.addEventListener('click', () => this.toggle());
        }
    }

    toggle() {
        if (!this.supported) {
            term.writeln('\r\n\x1b[1;31m[!] Voice not supported in this browser. Use Chrome or Edge.\x1b[0m');
            return;
        }
        if (this.isListening) {
            this.stop();
        } else {
            this.start();
        }
    }

    start() {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        this.recognition = new SpeechRecognition();
        this.recognition.continuous = true;
        this.recognition.interimResults = false;
        this.recognition.lang = 'en-IN'; // English + Indian accent support

        this.recognition.onstart = () => {
            this.isListening = true;
            if (this.btn) {
                this.btn.classList.add('listening');
                this.btn.innerHTML = '🔴 LISTENING';
            }
            // Update Voice protocol indicator
            const voiceProto = document.getElementById('protoVoice');
            if (voiceProto) voiceProto.classList.add('active');
            term.writeln('\r\n\x1b[1;32m[+] 🎙️ Voice Control Active — speak now...\x1b[0m');
        };

        this.recognition.onresult = (event) => {
            const last = event.results[event.results.length - 1];
            if (last.isFinal) {
                const transcript = last[0].transcript.trim();
                if (transcript) {
                    term.writeln(`\r\n\x1b[1;36m🎙️ Voice:\x1b[0m ${transcript}`);
                    // Send to backend via WebSocket
                    if (socket && socket.connected) {
                        socket.emit('term_input', { text: transcript + '\r' });
                    }
                }
            }
        };

        this.recognition.onerror = (event) => {
            if (event.error === 'not-allowed') {
                term.writeln('\r\n\x1b[1;31m[!] Microphone permission denied. Allow mic access in browser settings.\x1b[0m');
                this.stop();
            } else if (event.error !== 'no-speech' && event.error !== 'aborted') {
                term.writeln(`\r\n\x1b[1;33m[!] Voice error: ${event.error}\x1b[0m`);
            }
        };

        this.recognition.onend = () => {
            // Auto-restart if still supposed to be listening
            if (this.isListening) {
                try {
                    this.recognition.start();
                } catch (e) {
                    // Ignore — may already be running
                }
            }
        };

        try {
            this.recognition.start();
        } catch (e) {
            term.writeln('\r\n\x1b[1;31m[!] Failed to start voice recognition.\x1b[0m');
        }
    }

    stop() {
        this.isListening = false;
        if (this.recognition) {
            this.recognition.abort();
            this.recognition = null;
        }
        if (this.btn) {
            this.btn.classList.remove('listening');
            this.btn.innerHTML = '🎙️ VOICE';
        }
        const voiceProto = document.getElementById('protoVoice');
        if (voiceProto) voiceProto.classList.remove('active');
        term.writeln('\r\n\x1b[1;31m[-] 🎙️ Voice Control Deactivated.\x1b[0m');
    }
}

let voiceController = null;

// ══════════════════════════════════════════════════════════════════════════
// MAIN INIT
// ══════════════════════════════════════════════════════════════════════════
document.addEventListener('DOMContentLoaded', () => {
    checkAuth();

    // Auth buttons
    const unlockBtn = document.getElementById('unlock-btn');
    if (unlockBtn) unlockBtn.addEventListener('click', attemptUnlock);
    const tokenInput = document.getElementById('token-input');
    if (tokenInput) {
        tokenInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') attemptUnlock();
        });
    }

    // Tab routing
    document.querySelectorAll('.nav-icon').forEach(icon => {
        icon.addEventListener('click', () => {
            const targetId = icon.getAttribute('data-target');
            if (!targetId) return;
            document.querySelectorAll('.nav-icon').forEach(i => i.classList.remove('active'));
            document.querySelectorAll('.view-pane').forEach(v => v.classList.remove('active'));
            icon.classList.add('active');
            const pane = document.getElementById(targetId);
            if (pane) pane.classList.add('active');
            if (targetId === 'tab-cmd') setTimeout(() => fitAddon.fit(), 50);
            if (targetId === 'tab-docs') loadDocumentation();
        });
    });

    // Module toggles
    document.querySelectorAll('.toggle-btn').forEach(btn => {
        btn.addEventListener('click', async () => {
            const skill = btn.getAttribute('data-skill');
            try {
                const res = await fetch(`/api/skills/toggle?token=${getToken()}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ skill })
                });
                const data = await res.json();
                if (data.status === 'success') {
                    btn.textContent = data.is_active ? 'ACTIVE' : 'TOGGLE';
                    btn.style.background = data.is_active ? 'var(--accent)' : 'var(--accent-dim)';
                    btn.style.color = data.is_active ? '#000' : 'var(--accent)';
                    const indicator = document.getElementById('proto' + skill.charAt(0).toUpperCase() + skill.slice(1));
                    if (indicator) {
                        indicator.classList.toggle('active', data.is_active);
                    }
                }
            } catch (e) {
                console.error("Toggle failed", e);
            }
        });
    });

    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        if (e.ctrlKey && e.key >= '1' && e.key <= '5') {
            e.preventDefault();
            const tabs = ['tab-cmd', 'tab-modules', 'tab-commands', 'tab-docs', 'tab-settings'];
            const idx = parseInt(e.key) - 1;
            if (tabs[idx]) {
                const icon = document.querySelector(`.nav-icon[data-target="${tabs[idx]}"]`);
                if (icon) icon.click();
            }
        }
    });
});

// ── Auth ─────────────────────────────────────────────────────────────────
function getToken() {
    return localStorage.getItem('hexm_token') || '';
}

async function checkAuth() {
    const token = getToken();
    const overlay = document.getElementById('auth-overlay');
    if (!token) {
        if (overlay) overlay.style.display = 'flex';
        return;
    }
    try {
        const res = await fetch(`/api/verify?token=${token}`);
        if (res.ok) {
            if (overlay) overlay.style.display = 'none';
            initDashboard();
        } else {
            if (overlay) overlay.style.display = 'flex';
        }
    } catch (e) {
        if (overlay) overlay.style.display = 'flex';
    }
}

async function attemptUnlock() {
    const tokenInput = document.getElementById('token-input');
    const token = tokenInput ? tokenInput.value.trim() : '';
    if (!token) return;
    try {
        const res = await fetch(`/api/verify?token=${token}`);
        if (res.ok) {
            localStorage.setItem('hexm_token', token);
            document.getElementById('auth-overlay').style.display = 'none';
            const err = document.getElementById('auth-error');
            if (err) err.style.display = 'none';
            initDashboard();
        } else {
            const err = document.getElementById('auth-error');
            if (err) err.style.display = 'block';
        }
    } catch (e) {
        const err = document.getElementById('auth-error');
        if (err) err.style.display = 'block';
    }
}

// ── Dashboard Init ──────────────────────────────────────────────────────
function initDashboard() {
    // Mount terminal
    const termContainer = document.getElementById('terminal-container');
    if (termContainer && !termContainer.hasChildNodes()) {
        term.open(termContainer);
        fitAddon.fit();
        term.writeln('\x1b[1;36mHexMind V13 Ultimate — Gateway Validated.\x1b[0m');
        term.writeln('\x1b[2mConnecting to secure channel...\x1b[0m');
    }

    // Connect WebSocket
    if (!socket) connectSocket();

    // Init Charts
    if (!cpuChart) initCharts();

    // Telemetry polling (3 second interval for performance)
    if (!window.telemetryInterval) {
        window.telemetryInterval = setInterval(fetchTelemetry, 3000);
    }

    // Config loading
    loadConfig();

    // Init voice controller
    if (!voiceController) voiceController = new VoiceController();

    // Window resize → refit terminal
    window.addEventListener('resize', () => {
        if (document.getElementById('tab-cmd')?.classList.contains('active')) {
            fitAddon.fit();
        }
    });
}

// ══════════════════════════════════════════════════════════════════════════
// WEBSOCKET — with auto-reconnect & exponential backoff
// ══════════════════════════════════════════════════════════════════════════
function connectSocket() {
    socket = io.connect('http://' + document.domain + ':' + location.port, {
        query: { token: getToken() },
        reconnection: true,
        reconnectionDelay: 1000,
        reconnectionDelayMax: 10000,
        reconnectionAttempts: MAX_RECONNECT
    });

    socket.on('connect', () => {
        reconnectAttempts = 0;
        const statusEl = document.querySelector('.sys-status span:last-child');
        if (statusEl) statusEl.textContent = 'CORE ONLINE';
        const dotEl = document.querySelector('.sys-status .dot');
        if (dotEl) {
            dotEl.classList.add('blink');
            dotEl.style.background = 'var(--accent)';
        }
        term.writeln('\x1b[1;32m[+] Connection established.\x1b[0m');
    });

    socket.on('disconnect', (reason) => {
        const statusEl = document.querySelector('.sys-status span:last-child');
        if (statusEl) statusEl.textContent = 'DISCONNECTED';
        const dotEl = document.querySelector('.sys-status .dot');
        if (dotEl) {
            dotEl.style.background = 'var(--danger)';
            dotEl.classList.remove('blink');
        }
        term.writeln('\r\n\x1b[1;31m[-] Connection lost. Reconnecting...\x1b[0m');
    });

    socket.on('reconnect_attempt', (attempt) => {
        reconnectAttempts = attempt;
        term.writeln(`\x1b[2m[~] Reconnection attempt ${attempt}/${MAX_RECONNECT}...\x1b[0m`);
    });

    socket.on('reconnect_failed', () => {
        term.writeln('\x1b[1;31m[!] Max reconnection attempts reached. Refresh to retry.\x1b[0m');
    });

    // ── TERMINAL OUTPUT — with auto-scroll fix ──
    socket.on('term_output', (data) => {
        term.write(data.text);
        // AUTO-SCROLL: always scroll to latest output
        term.scrollToBottom();
    });

    // ── TYPING INDICATOR ──
    socket.on('typing_start', () => {
        const indicator = document.getElementById('typingIndicator');
        if (indicator) indicator.classList.add('active');
    });

    socket.on('typing_end', () => {
        const indicator = document.getElementById('typingIndicator');
        if (indicator) indicator.classList.remove('active');
    });

    // Send keystrokes
    term.onData(data => {
        if (socket && socket.connected) {
            socket.emit('term_input', { text: data });
        }
    });
}

// ── Telemetry ───────────────────────────────────────────────────────────
async function fetchTelemetry() {
    try {
        const res = await fetch(`/api/status?token=${getToken()}`);
        const data = await res.json();

        if (cpuChart) {
            const arr = cpuChart.data.datasets[0].data;
            arr.shift();
            arr.push(data.telemetry?.cpu || 0);
            cpuChart.update();
        }
        if (ramChart) {
            const arr = ramChart.data.datasets[0].data;
            arr.shift();
            arr.push(data.telemetry?.ram || 0);
            ramChart.update();
        }

        const osLbl = document.getElementById('osLabel');
        if (osLbl && data.os) osLbl.textContent = data.os;

        const modelLbl = document.getElementById('activeModelLabel');
        if (modelLbl && data.active_model) modelLbl.textContent = data.active_model;

        if (data.analytics) {
            const latLbl = document.getElementById('latencyLabel');
            if (latLbl) latLbl.textContent = (data.analytics.latency * 1000).toFixed(0) + 'ms';
            const spdLbl = document.getElementById('speedLabel');
            if (spdLbl) spdLbl.textContent = data.analytics.tokens_sec.toFixed(1);
        }

        // Sync skill toggles
        if (data.skills) {
            for (const [skill, isActive] of Object.entries(data.skills)) {
                const btn = document.querySelector(`.toggle-btn[data-skill="${skill}"]`);
                if (btn) {
                    btn.textContent = isActive ? 'ACTIVE' : 'TOGGLE';
                    btn.style.background = isActive ? 'var(--accent)' : 'var(--accent-dim)';
                    btn.style.color = isActive ? '#000' : 'var(--accent)';
                }
                const indicator = document.getElementById('proto' + skill.charAt(0).toUpperCase() + skill.slice(1));
                if (indicator) indicator.classList.toggle('active', isActive);
            }
        }
    } catch (e) {
        // Silent fail on polling
    }
}

// ── Config ──────────────────────────────────────────────────────────────
async function loadConfig() {
    try {
        const res = await fetch(`/api/config?token=${getToken()}`);
        const data = await res.json();
        if (data.provider?.key) {
            document.getElementById('cfgProviderKey').value = '********';
        }
        if (data.telegram_token) {
            document.getElementById('cfgTelegramToken').value = data.telegram_token;
        }
        if (data.rapidapi_key) {
            document.getElementById('cfgRapidKey').value = data.rapidapi_key;
        }
    } catch (e) { /* silent */ }
}

async function saveConfig() {
    const key = document.getElementById('cfgProviderKey').value;
    const tg = document.getElementById('cfgTelegramToken').value;
    const rpd = document.getElementById('cfgRapidKey').value;
    const payload = {};
    if (key && key !== '********') payload.provider_key = key;
    if (tg) payload.telegram_token = tg;
    if (rpd) payload.rapidapi_key = rpd;

    try {
        const res = await fetch(`/api/config?token=${getToken()}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.status === 'success') {
            term.writeln('\r\n\x1b[1;32m[+] Configuration saved.\x1b[0m');
        }
    } catch (e) {
        term.writeln('\r\n\x1b[1;31m[!] Failed to save config.\x1b[0m');
    }
}

async function hardReset() {
    const confirmation = prompt("DANGER: Type 'NUKE' to factory reset.");
    if (confirmation === 'NUKE') {
        try {
            await fetch(`/api/reset?token=${getToken()}`, { method: 'POST' });
            window.location.reload();
        } catch (e) {
            window.location.reload();
        }
    }
}

// ── Documentation ───────────────────────────────────────────────────────
let isDocLoaded = false;
async function loadDocumentation() {
    if (isDocLoaded) return;
    try {
        const res = await fetch(`/api/readme?token=${getToken()}`);
        const data = await res.json();
        if (data.status === 'success') {
            document.getElementById('markdown-content').innerHTML = marked.parse(data.content);
            isDocLoaded = true;
        } else {
            document.getElementById('markdown-content').innerHTML = "<p style='color: var(--danger)'>Failed to load docs.</p>";
        }
    } catch (e) {
        document.getElementById('markdown-content').innerHTML = "<p style='color: var(--danger)'>Error loading docs.</p>";
    }
}
