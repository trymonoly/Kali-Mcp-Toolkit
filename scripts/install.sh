#!/usr/bin/env bash
set -euo pipefail

# KaliMcp Installation Script
# Run as root on Kali Linux

INSTALL_DIR="/opt/KaliMcp"
WORKSPACE_DIR="/opt/kalimcp/workspace"
LOG_DIR="/var/log/kalimcp"
SERVICE_FILE="/etc/systemd/system/kalimcp.service"

echo "=== KaliMcp Installer ==="

# Check root
if [ "$EUID" -ne 0 ]; then
    echo "Error: Please run as root (sudo ./install.sh)"
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)
if [ "$MAJOR" -lt 3 ] || ([ "$MAJOR" -eq 3 ] && [ "$MINOR" -lt 11 ]); then
    echo "Error: Python 3.11+ required (found $PYTHON_VERSION)"
    exit 1
fi
echo "[+] Python $PYTHON_VERSION OK"

# Create directories
echo "[+] Creating directories..."
mkdir -p "$WORKSPACE_DIR"
mkdir -p "$LOG_DIR"

# Clone or update
if [ -d "$INSTALL_DIR" ]; then
    echo "[+] Updating existing installation..."
    cd "$INSTALL_DIR"
    git pull || true
else
    echo "[+] Cloning KaliMcp..."
    git clone https://github.com/yourname/KaliMcp.git "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# Virtual environment
echo "[+] Setting up virtual environment..."
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e ".[dev]"

# Generate API key if config has default
CONFIG="$INSTALL_DIR/config/default.yaml"
if grep -q "CHANGE_ME" "$CONFIG" 2>/dev/null; then
    NEW_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
    sed -i "s/CHANGE_ME_GENERATE_WITH_secrets_token_urlsafe_32/$NEW_KEY/" "$CONFIG"
    echo "[+] Generated API Key: $NEW_KEY"
    echo "    ⚠️  Save this key! It will not be shown again."
fi

# Install systemd service
echo "[+] Installing systemd service..."
cp "$INSTALL_DIR/deploy/kalimcp.service" "$SERVICE_FILE"
systemctl daemon-reload
systemctl enable kalimcp

echo ""
echo "=== Installation Complete ==="
echo ""
echo "Start the service:  systemctl start kalimcp"
echo "Check status:       systemctl status kalimcp"
echo "View logs:          journalctl -u kalimcp -f"
echo "Test with Inspector: npx @modelcontextprotocol/inspector http://localhost:8443/mcp"
echo ""
