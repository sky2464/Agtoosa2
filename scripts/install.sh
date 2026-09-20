#!/usr/bin/env bash
# ==============================================================================
# Agtoosa2 Universal Installer
# Installs Agtoosa2 cleanly on macOS and Linux with zero dependency conflicts.
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/sky2464/Agtoosa2/main/install.sh | bash
#   OR inside repo: ./install.sh
# ==============================================================================

set -euo pipefail

REPO_URL="git+https://github.com/sky2464/Agtoosa2.git"
INSTALL_DIR="$HOME/.local/bin"
mkdir -p "$INSTALL_DIR"

BOLD="\033[1m"
GREEN="\033[32m"
YELLOW="\033[33m"
BLUE="\033[34m"
RED="\033[31m"
RESET="\033[0m"

echo -e "${BOLD}${BLUE}🚀 Agtoosa2 Universal Installer${RESET}"
echo -e "   Checking environment...\n"

# 1. Check Python runtime (>= 3.11 required)
PYTHON_BIN=""
for cmd in python3 python python3.13 python3.12 python3.11; do
    if command -v "$cmd" >/dev/null 2>&1; then
        VER=$("$cmd" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || true)
        MAJOR=$(echo "$VER" | cut -d. -f1)
        MINOR=$(echo "$VER" | cut -d. -f2)
        if [ "${MAJOR:-0}" -ge 3 ] && [ "${MINOR:-0}" -ge 11 ]; then
            PYTHON_BIN="$cmd"
            break
        fi
    fi
done

if [ -z "$PYTHON_BIN" ]; then
    echo -e "${RED}❌ Python 3.11 or higher is required.${RESET}"
    echo "   Please install Python 3.11+ via:"
    echo "     macOS: brew install python@3.12"
    echo "     Linux: sudo apt install python3 python3-venv"
    exit 1
fi

echo -e "   • Found Python: ${GREEN}$PYTHON_BIN ($VER)${RESET}"

# Determine package target (local repo or GitHub)
PKG_SPEC="$REPO_URL"
if [ -f "pyproject.toml" ] && grep -q 'name = "agtoosa"' pyproject.toml 2>/dev/null; then
    PKG_SPEC="$(pwd)"
    echo -e "   • Detected local repository: ${GREEN}$PKG_SPEC${RESET}"
else
    echo -e "   • Package source: ${GREEN}$PKG_SPEC${RESET}"
fi

# Clean up any existing broken symlinks or conflicting files safely
if [ -e "$INSTALL_DIR/agtoosa" ] || [ -L "$INSTALL_DIR/agtoosa" ]; then
    echo -e "   • Refreshing existing binary at $INSTALL_DIR/agtoosa"
    rm -f "$INSTALL_DIR/agtoosa"
fi

# 2. Preferred installation tool order: uv -> pipx -> isolated venv
INSTALLED_VIA=""

if command -v uv >/dev/null 2>&1; then
    echo -e "   • Installing via ${BOLD}uv tool${RESET} (fastest)..."
    uv tool install --force "$PKG_SPEC"
    INSTALLED_VIA="uv"
elif command -v pipx >/dev/null 2>&1; then
    echo -e "   • Installing via ${BOLD}pipx${RESET}..."
    pipx install --force "$PKG_SPEC"
    INSTALLED_VIA="pipx"
else
    echo -e "   • Installing into isolated user environment (~/.agtoosa/venv)..."
    VENV_DIR="$HOME/.agtoosa/venv"
    mkdir -p "$HOME/.agtoosa"
    "$PYTHON_BIN" -m venv "$VENV_DIR"
    "$VENV_DIR/bin/python" -m pip install --quiet --upgrade pip
    "$VENV_DIR/bin/pip" install --quiet --upgrade "$PKG_SPEC"
    ln -sf "$VENV_DIR/bin/agtoosa" "$INSTALL_DIR/agtoosa"
    INSTALLED_VIA="venv"
fi

# 3. Verify PATH availability
echo ""
IN_PATH=false
if command -v agtoosa >/dev/null 2>&1; then
    IN_PATH=true
elif echo "$PATH" | tr ':' '\n' | grep -qx "$INSTALL_DIR"; then
    IN_PATH=true
fi

if [ "$IN_PATH" = false ]; then
    echo -e "${YELLOW}⚠️  Note: $INSTALL_DIR is not yet in your PATH.${RESET}"
    echo "   Add it to your shell configuration file (~/.zshrc or ~/.bashrc):"
    echo -e "     ${BOLD}export PATH=\"\$HOME/.local/bin:\$PATH\"${RESET}\n"
fi

# 4. Verify installation
AGTOOSA_CMD="$INSTALL_DIR/agtoosa"
if [ "$IN_PATH" = true ] && command -v agtoosa >/dev/null 2>&1; then
    AGTOOSA_CMD="agtoosa"
fi

echo -e "${BOLD}${GREEN}✅ Agtoosa2 installed successfully!${RESET}"
"$AGTOOSA_CMD" version 2>/dev/null || true

echo -e "\n${BOLD}Quick Start:${RESET}"
echo "  1. Navigate to your project:  cd /path/to/project"
echo "  2. Build knowledge graph:     agtoosa graph build"
echo "  3. Launch visual studio:      agtoosa graph view --serve --open"
echo "  4. Review architecture:       agtoosa review"
echo ""
