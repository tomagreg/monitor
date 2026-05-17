#!/bin/bash
# ── Deploy monitor dashboard on PI-TOMA ──────────────────────────────────────
# Run once after cloning the repo on the Pi
# Usage: bash setup.sh
# ─────────────────────────────────────────────────────────────────────────────
set -e

REPO_DIR="/home/tomagreg/repos/monitor"

echo "==> Creating venv..."
python3 -m venv "$REPO_DIR/venv"

echo "==> Installing deps..."
"$REPO_DIR/venv/bin/pip" install -q -r "$REPO_DIR/requirements.txt"

echo "==> Installing systemd service..."
sudo cp "$REPO_DIR/monitor.service" /etc/systemd/system/monitor.service
sudo systemctl daemon-reload
sudo systemctl enable monitor
sudo systemctl start monitor

echo "==> Opening UFW port 5001..."
sudo ufw allow 5001/tcp

echo "==> Configuring local hostname 'dashboard'..."
# Add to /etc/hosts so that 'dashboard' resolves locally on the Pi
grep -q "dashboard" /etc/hosts || echo "127.0.0.1  dashboard" | sudo tee -a /etc/hosts

echo ""
echo "✓ Done! Dashboard running at:"
echo "  http://dashboard:5001   (on the Pi itself)"
echo "  http://PI-TOMA:5001     (Tailscale from PC)"
echo "  http://100.113.125.27:5001 (Tailscale IP direct)"
