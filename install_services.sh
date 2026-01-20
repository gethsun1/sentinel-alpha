#!/bin/bash
# Install Sentinel Alpha Systemd Service (Unified)
# 24/7 Single-Process Multi-Pair Bot

set -e

echo "=================================================================="
echo "SENTINEL ALPHA - UNIFIED SERVICE INSTALLATION"
echo "=================================================================="
echo ""

if [ "$EUID" -ne 0 ]; then
   echo "❌ Please run as root (sudo ./install_services.sh)"
   exit 1
fi

WORK_DIR="/root/sentinel-alpha"
cd "$WORK_DIR"

echo "Step 1: Stopping old template services..."
systemctl stop sentinel-alpha@* || true
systemctl disable sentinel-alpha@* || true
rm /etc/systemd/system/sentinel-alpha@.service || true
echo "✓ Old services removed"
echo ""

echo "Step 2: Installing new unified service..."
cp sentinel-alpha.service /etc/systemd/system/
cp sentinel-alpha-dashboard.service /etc/systemd/system/
echo "✓ Service files copied"
echo ""

echo "Step 3: Reloading & Starting..."
systemctl daemon-reload
systemctl enable sentinel-alpha.service
systemctl restart sentinel-alpha.service
systemctl restart sentinel-alpha-dashboard.service

echo "Step 4: Status Check"
systemctl status sentinel-alpha.service --no-pager
echo ""

echo "=================================================================="
echo "✓ UNIFIED BOT STARTED"
echo "=================================================================="
echo "Logs: tail -f /root/sentinel-alpha/logs/combined_bots.log"
echo "Dashboard: http://107.173.248.121:5000"
echo ""
