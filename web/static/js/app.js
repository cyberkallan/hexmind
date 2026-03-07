// HexMind V7 Frontend Application Logic

const term = new Terminal({
    cursorBlink: true,
    fontFamily: '"JetBrains Mono", monospace',
    fontSize: 14,
    theme: {
        background: 'transparent',
        foreground: '#f0f6fc',
        cursor: '#00ff88',
        selection: 'rgba(0, 255, 136, 0.3)'
    },
    convertEol: true // Automatically normalize PTY newlines
});

const fitAddon = new FitAddon.FitAddon();
term.loadAddon(fitAddon);

let socket = null;
let currentTab = 'tab-cmd';

// Chart.js Instances
let cpuChart = null;
let ramChart = null;

// Helper to init charts
function initCharts() {
    const commonOptions = {
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 0 },
        scales: {
            x: { display: false },
            y: { min: 0, max: 100, display: true, grid: { color: 'rgba(255,255,255,0.1)' }, border: { dash: [4, 4] } }
        },
        plugins: { legend: { display: false }, tooltip: { enabled: false } },
        elements: { point: { radius: 0 } }
    };

    const ctxCpu = document.getElementById('cpuChart').getContext('2d');
    cpuChart = new Chart(ctxCpu, {
        type: 'line',
        data: {
            labels: Array(30).fill(''),
            datasets: [{
                label: 'CPU',
                data: Array(30).fill(0),
                borderColor: '#00ff88',
                backgroundColor: 'rgba(0, 255, 136, 0.1)',
                borderWidth: 2,
                fill: true,
                tension: 0.4
            }]
        },
        options: commonOptions
    });

    const ctxRam = document.getElementById('ramChart').getContext('2d');
    ramChart = new Chart(ctxRam, {
        type: 'line',
        data: {
            labels: Array(30).fill(''),
            datasets: [{
                label: 'RAM',
                data: Array(30).fill(0),
                borderColor: '#00ccff',
                backgroundColor: 'rgba(0, 204, 255, 0.1)',
                borderWidth: 2,
                fill: true,
                tension: 0.4
            }]
        },
        options: commonOptions
    });
}

document.addEventListener('DOMContentLoaded', () => {
    // 1. Setup Auth Checking
    checkAuth();

    // 2. Setup Auth Overlay Buttons
    const unlockBtn = document.getElementById('unlock-btn');
    if (unlockBtn) {
        unlockBtn.addEventListener('click', attemptUnlock);
    }
    const tokenInput = document.getElementById('token-input');
    if (tokenInput) {
        tokenInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') attemptUnlock();
        });
    }

    // 2. Tab Routing
    document.querySelectorAll('.nav-icon').forEach(icon => {
        icon.addEventListener('click', (e) => {
            const targetId = icon.getAttribute('data-target');
            if (!targetId) return;

            // Remove active classes
            document.querySelectorAll('.nav-icon').forEach(i => i.classList.remove('active'));
            document.querySelectorAll('.view-pane').forEach(v => v.classList.remove('active'));

            // Add active class to clicked tab and corresponding pane
            icon.classList.add('active');
            const targetPane = document.getElementById(targetId);
            if (targetPane) {
                targetPane.classList.add('active');
            }

            // Resize terminal if we switch back to it
            if (targetId === 'tab-cmd') {
                setTimeout(() => fitAddon.fit(), 50);
            }

            // Lazy load documentation
            if (targetId === 'tab-docs') {
                loadDocumentation();
            }
        });
    });

    // 4. Module Toggles Setup
    document.querySelectorAll('.toggle-btn').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            const skill = btn.getAttribute('data-skill');
            try {
                const res = await fetch(`/api/skills/toggle?token=${getToken()}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ skill: skill })
                });
                const data = await res.json();
                if (data.status === 'success') {
                    // Update button UI
                    btn.textContent = data.is_active ? 'ACTIVE' : 'TOGGLE';
                    btn.style.background = data.is_active ? 'var(--accent)' : 'var(--accent-dim)';
                    btn.style.color = data.is_active ? '#000' : 'var(--accent)';

                    // Update Right Rail Indicator
                    const indicator = document.getElementById('proto' + skill.charAt(0).toUpperCase() + skill.slice(1));
                    if (indicator) {
                        if (data.is_active) indicator.classList.add('active');
                        else indicator.classList.remove('active');
                    }
                }
            } catch (e) {
                console.error("Failed to toggle module", e);
            }
        });
    });

    // 5. Clickable Command Cards
    document.querySelectorAll('.module-card h3').forEach(title => {
        title.parentElement.style.cursor = 'pointer';
        title.parentElement.addEventListener('click', () => {
            const cmd = title.textContent.trim().toLowerCase().replace(/[^a-z]/g, '');
            if (socket) {
                term.writeln(`\x1b[36mExecuting:\x1b[0m ${cmd}`);
                socket.emit('term_input', { text: cmd + '\r' });
            }
        });
    });
});

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
            const overlay = document.getElementById('auth-overlay');
            if (overlay) overlay.style.display = 'none';
            const errorMsg = document.getElementById('auth-error');
            if (errorMsg) errorMsg.style.display = 'none';
            initDashboard();
        } else {
            const errorMsg = document.getElementById('auth-error');
            if (errorMsg) errorMsg.style.display = 'block';
        }
    } catch (e) {
        const errorMsg = document.getElementById('auth-error');
        if (errorMsg) errorMsg.style.display = 'block';
    }
}

function initDashboard() {
    // 1. Mount Terminal
    const termContainer = document.getElementById('terminal-container');
    if (termContainer && !termContainer.hasChildNodes()) {
        term.open(termContainer);
        fitAddon.fit();
        term.writeln('\x1b[1;36mHexMind V13 Ultimate Gateway Validated.\x1b[0m');
        term.writeln('\x1b[2mEstablishing secure WebSocket connection...\x1b[0m');
    }

    // 2. Connect WebSocket
    if (!socket) connectSocket();

    // 3. Init Charts
    if (!cpuChart) initCharts();

    // 4. Start Telemetry
    if (!window.telemetryInterval) {
        window.telemetryInterval = setInterval(fetchTelemetry, 1000);
    }

    // 5. Config Loading
    loadConfig();

    // Resize listener
    window.addEventListener('resize', () => {
        if (document.getElementById('tab-cmd').classList.contains('active')) {
            fitAddon.fit();
        }
    });
}

function connectSocket() {
    socket = io.connect('http://' + document.domain + ':' + location.port, {
        query: { token: getToken() }
    });

    socket.on('connect', () => {
        document.querySelector('.sys-status span:last-child').textContent = 'CORE ONLINE';
        document.querySelector('.sys-status .dot').classList.add('blink');
        document.querySelector('.sys-status .dot').style.background = 'var(--accent)';
        term.writeln('\x1b[1;32m[+] Connection established.\x1b[0m');
    });

    socket.on('disconnect', () => {
        document.querySelector('.sys-status span:last-child').textContent = 'DISCONNECTED';
        document.querySelector('.sys-status .dot').style.background = 'var(--danger)';
        document.querySelector('.sys-status .dot').classList.remove('blink');
        term.writeln('\r\n\x1b[1;31m[-] WebSockets context lost. Reconnecting...\x1b[0m');
    });

    socket.on('term_output', (data) => {
        term.write(data.text);
    });

    // Send keystrokes directly (byte streams)
    term.onData(data => {
        socket.emit('term_input', { text: data });
    });
}

async function fetchTelemetry() {
    try {
        const res = await fetch(`/api/status?token=${getToken()}`);
        const data = await res.json();

        // Update Charts
        if (cpuChart) {
            const arr = cpuChart.data.datasets[0].data;
            arr.shift();
            arr.push(data.telemetry.cpu);
            cpuChart.update();
        }
        if (ramChart) {
            const arr = ramChart.data.datasets[0].data;
            arr.shift();
            arr.push(data.telemetry.ram);
            ramChart.update();
        }

        document.getElementById('osLabel').textContent = data.os;
        if (data.active_model) {
            document.getElementById('activeModelLabel').textContent = data.active_model;
        }

        // Update Analytics
        if (data.analytics) {
            document.getElementById('latencyLabel').textContent = (data.analytics.latency * 1000).toFixed(0) + 'ms';
            document.getElementById('speedLabel').textContent = data.analytics.tokens_sec.toFixed(1);
        }

        // Sync statuses
        for (const [skill, isActive] of Object.entries(data.skills)) {
            const btn = document.querySelector(`.toggle-btn[data-skill="${skill}"]`);
            if (btn) {
                btn.textContent = isActive ? 'ACTIVE' : 'TOGGLE';
                btn.style.background = isActive ? 'var(--accent)' : 'var(--accent-dim)';
                btn.style.color = isActive ? '#000' : 'var(--accent)';
            }
            const indicator = document.getElementById('proto' + skill.charAt(0).toUpperCase() + skill.slice(1));
            if (indicator) {
                if (isActive) indicator.classList.add('active');
                else indicator.classList.remove('active');
            }
        }
    } catch (error) {
        // Silent fail on polling
    }
}

async function loadConfig() {
    try {
        const res = await fetch(`/api/config?token=${getToken()}`);
        const data = await res.json();
        if (data.provider && data.provider.key) {
            document.getElementById('cfgProviderKey').value = '********'; // Obfuscate
        }
        if (data.telegram_token) {
            document.getElementById('cfgTelegramToken').value = data.telegram_token;
        }
    } catch (e) {
        console.error("Could not load config", e);
    }
}

async function saveConfig() {
    const key = document.getElementById('cfgProviderKey').value;
    const tg = document.getElementById('cfgTelegramToken').value;

    const payload = {};
    if (key && key !== '********') payload.provider_key = key;
    if (tg) payload.telegram_token = tg;

    try {
        const res = await fetch(`/api/config?token=${getToken()}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.status === 'success') {
            alert("Configuration saved securely.");
        }
    } catch (e) {
        alert("Failed to save configuration.");
    }
}

async function hardReset() {
    const confirmation = prompt("DANGER: Type 'NUKE' to factory reset HexMind and delete all long-term memory.");
    if (confirmation === 'NUKE') {
        try {
            await fetch(`/api/reset?token=${getToken()}`, { method: 'POST' });
            alert("System nuked. HexMind shutting down...");
            window.location.reload();
        } catch (e) {
            // Backend probably died immediately, which means success
            window.location.reload();
        }
    }
}

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
            document.getElementById('markdown-content').innerHTML = "<p style='color: var(--danger)'>Failed to load documentation.</p>";
        }
    } catch (e) {
        document.getElementById('markdown-content').innerHTML = "<p style='color: var(--danger)'>Error loading documentation.</p>";
    }
}
