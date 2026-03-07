#!/usr/bin/env bash
# ╔══════════════════════════════════════════════════════════╗
# ║         HexMind v2.0 — Install Script                   ║
# ║         by Arjun T M (cyberkallan)                      ║
# ╚══════════════════════════════════════════════════════════╝
set -e

CYAN='\033[0;36m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
RED='\033[0;31m'; BOLD='\033[1m'; NC='\033[0m'

echo -e "${CYAN}"
echo "  ██╗  ██╗███████╗██╗  ██╗███╗   ███╗██╗███╗   ██╗██████╗ "
echo "  ██║  ██║██╔════╝╚██╗██╔╝████╗ ████║██║████╗  ██║██╔══██╗"
echo "  ███████║█████╗   ╚███╔╝ ██╔████╔██║██║██╔██╗ ██║██║  ██║"
echo "  ██╔══██║██╔══╝   ██╔██╗ ██║╚██╔╝██║██║██║╚██╗██║██║  ██║"
echo "  ██║  ██║███████╗██╔╝ ██╗██║ ╚═╝ ██║██║██║ ╚████║██████╔╝"
echo "  ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝╚═╝╚═╝  ╚═══╝╚═════╝"
echo -e "${NC}"
echo -e "${BOLD}     AI-Powered Hacker Terminal Assistant v2.0${NC}"
echo -e "     by Arjun T M  ·  github.com/cyberkallan"
echo ""

# Detect platform
TERMUX=false
if [ -d "/data/data/com.termux" ]; then
    TERMUX=true
    echo -e "${YELLOW}  Platform: Termux (Android)${NC}"
else
    echo -e "${CYAN}  Platform: $(uname -s) $(uname -m)${NC}"
fi
echo ""

step() { echo -e "${CYAN}  [*] $1${NC}"; }
ok()   { echo -e "${GREEN}  [+] $1${NC}"; }
warn() { echo -e "${YELLOW}  [!] $1${NC}"; }
err()  { echo -e "${RED}  [-] $1${NC}"; }

# ── Step 1: Python check ─────────────────────────────────────────────────────
step "Checking Python 3..."
if ! command -v python3 &>/dev/null; then
    err "Python 3 not found!"
    if $TERMUX; then echo "  Run: pkg install python"; else echo "  Run: sudo apt install python3 python3-pip"; fi
    exit 1
fi
PYVER=$(python3 --version)
ok "$PYVER found"

# ── Step 2: pip ──────────────────────────────────────────────────────────────
step "Checking pip..."
if ! python3 -m pip --version &>/dev/null; then
    if $TERMUX; then pkg install python; else sudo apt install python3-pip -y 2>/dev/null; fi
fi
ok "pip ready"

# ── Step 3: Core dependencies ────────────────────────────────────────────────
step "Installing core dependencies (requests, rich, prompt-toolkit)..."
if $TERMUX; then
    pip install requests rich prompt-toolkit --quiet
else
    pip install requests rich prompt-toolkit --quiet --break-system-packages 2>/dev/null || \
    pip install requests rich prompt-toolkit --quiet
fi
ok "Core dependencies installed"

# ── Step 4: Install hexmind ──────────────────────────────────────────────────
step "Installing HexMind..."
INSTALL_DIR="$HOME/.local/share/hexmind"
mkdir -p "$INSTALL_DIR"
# Copy everything from current directory
cp -r . "$INSTALL_DIR/"

# Create launcher script
mkdir -p "$HOME/.local/bin"
cat > "$HOME/.local/bin/hexmind" << LAUNCHER
#!/usr/bin/env bash
cd "$INSTALL_DIR" && python3 hexmind.py "\$@"
LAUNCHER
chmod +x "$HOME/.local/bin/hexmind"

# Add to PATH if needed
SHELL_RC=""
if [ -f "$HOME/.bashrc" ]; then SHELL_RC="$HOME/.bashrc"
elif [ -f "$HOME/.zshrc" ]; then SHELL_RC="$HOME/.zshrc"
elif [ -f "$HOME/.profile" ]; then SHELL_RC="$HOME/.profile"; fi

if [ -n "$SHELL_RC" ]; then
    if ! grep -q ".local/bin" "$SHELL_RC" 2>/dev/null; then
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$SHELL_RC"
    fi
fi

# Also create a direct alias in current dir
echo "#!/usr/bin/env bash" > /usr/local/bin/hexmind 2>/dev/null && \
echo "cd $INSTALL_DIR && python3 hexmind.py \"\$@\"" >> /usr/local/bin/hexmind 2>/dev/null && \
chmod +x /usr/local/bin/hexmind 2>/dev/null && ok "Installed to /usr/local/bin/hexmind" || \
warn "Could not install to /usr/local/bin (no root) — using ~/.local/bin/hexmind"

ok "HexMind installed!"

# ── Step 5: Optional AI providers ────────────────────────────────────────────
echo ""
step "Optional: install AI provider libraries"
echo "  (Required only if you use non-OpenRouter providers)"
echo ""

if $TERMUX; then
    pip install "anthropic==0.18.1" --quiet 2>/dev/null && ok "anthropic installed (Termux)" || warn "anthropic install skipped"
    pip install "openai==0.28.1" --quiet 2>/dev/null && ok "openai installed (Termux)" || warn "openai install skipped"
else
    pip install anthropic --quiet --break-system-packages 2>/dev/null || pip install anthropic --quiet 2>/dev/null || warn "anthropic skipped"
    pip install openai --quiet --break-system-packages 2>/dev/null || pip install openai --quiet 2>/dev/null || warn "openai skipped"
fi

# ── Done ─────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}${BOLD}  ╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}${BOLD}  ║   HexMind installed successfully! 🎉  ║${NC}"
echo -e "${GREEN}${BOLD}  ╚════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${BOLD}Run:${NC} ${CYAN}hexmind${NC}   or   ${CYAN}python3 hexmind.py${NC}"
echo ""
echo -e "  ${BOLD}First time:${NC} HexMind will guide you through setup"
echo -e "  ${BOLD}Free AI API:${NC} Get key at ${CYAN}https://openrouter.ai/keys${NC}"
echo -e "  ${BOLD}Local AI:${NC} After setup, type ${CYAN}brain${NC} to install offline AI (~90MB)"
echo ""
if [ -n "$SHELL_RC" ]; then
    echo -e "  ${YELLOW}Reload shell: source $SHELL_RC${NC}"
fi
echo ""
