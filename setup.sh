#!/bin/bash
# ── Deploy monitor dashboard on the LXC "web" ────────────────────────────────
# Run once as root after cloning the repo into /root/monitor
# Usage: bash setup.sh
# ─────────────────────────────────────────────────────────────────────────────
set -e

REPO_DIR="/root/monitor"

echo "==> Creating venv..."
python3 -m venv "$REPO_DIR/venv"

echo "==> Installing deps..."
"$REPO_DIR/venv/bin/pip" install -q -r "$REPO_DIR/requirements.txt"

echo "==> Installing systemd service..."
cp "$REPO_DIR/monitor.service" /etc/systemd/system/monitor.service
systemctl daemon-reload
systemctl enable --now monitor

echo ""
echo "✓ Done! Dashboard running at http://192.168.1.68:5001"
