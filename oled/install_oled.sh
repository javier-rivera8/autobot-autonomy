#!/usr/bin/env bash
# install_oled.sh — Install the OLED stats service on the Raspberry Pi
# Run as root: sudo bash oled/install_oled.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "==> Installing Python dependencies..."
pip3 install --break-system-packages luma.oled psutil

echo "==> Copying script to /opt/autobot/..."
mkdir -p /opt/autobot
cp "$SCRIPT_DIR/oled_stats.py" /opt/autobot/oled_stats.py
chmod +x /opt/autobot/oled_stats.py

echo "==> Installing systemd service..."
cp "$SCRIPT_DIR/autobot-oled.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable autobot-oled.service
systemctl start autobot-oled.service

echo ""
echo "Done! OLED service is running."
echo "  Status:  sudo systemctl status autobot-oled"
echo "  Logs:    sudo journalctl -u autobot-oled -f"
echo "  Stop:    sudo systemctl stop autobot-oled"
echo "  Disable: sudo systemctl disable autobot-oled"
