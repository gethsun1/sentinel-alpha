#!/bin/bash
# Script to safely stop and restart the Sentinel Alpha bot

echo "=== Stopping Sentinel Alpha Bot ==="

# Stop systemd service
systemctl stop sentinel-alpha.service
sleep 2

# Check for any remaining processes
echo "Checking for remaining bot processes..."
REMAINING=$(ps aux | grep -E "live_trading_bot.py" | grep -v grep | wc -l)

if [ "$REMAINING" -gt 0 ]; then
    echo "Found $REMAINING remaining process(es), killing them..."
    pkill -f "live_trading_bot.py"
    sleep 2
    
    # Force kill if still running
    pkill -9 -f "live_trading_bot.py" 2>/dev/null
    sleep 1
fi

# Final check
FINAL_CHECK=$(ps aux | grep -E "live_trading_bot.py" | grep -v grep | wc -l)
if [ "$FINAL_CHECK" -eq 0 ]; then
    echo "✓ All bot processes stopped"
else
    echo "⚠ Warning: $FINAL_CHECK process(es) still running"
    ps aux | grep -E "live_trading_bot.py" | grep -v grep
fi

echo ""
echo "=== Starting Sentinel Alpha Bot ==="
systemctl start sentinel-alpha.service
sleep 3

# Verify it started
if systemctl is-active --quiet sentinel-alpha.service; then
    echo "✓ Bot service started successfully"
    systemctl status sentinel-alpha.service --no-pager | head -10
else
    echo "✗ Failed to start bot service"
    systemctl status sentinel-alpha.service --no-pager
    exit 1
fi

echo ""
echo "=== Process Check ==="
ps aux | grep -E "live_trading_bot" | grep -v grep || echo "No bot processes found (this is unexpected)"

echo ""
echo "=== Restart Complete ==="
