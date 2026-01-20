#!/bin/bash
# Quick Start Script for Sentinel Alpha
# Starts bot in screen session for easy monitoring

echo "======================================================================"
echo "SENTINEL ALPHA - QUICK START"
echo "======================================================================"

cd /root/sentinel-alpha

# Check .env exists
if [ ! -f .env ]; then
    echo "❌ ERROR: .env file not found!"
    echo "Please create .env with WEEX credentials first"
    exit 1
fi

# Check competition mode
MODE=$(grep "^mode:" competition.yaml | awk '{print $2}')
echo "Competition Mode: $MODE"

# Kill any existing screen session
screen -X -S sentinel quit 2>/dev/null

# Start in new screen session
echo ""
echo "Starting bot in screen session 'sentinel'..."
echo ""
echo "To view bot output:"
echo "  screen -r sentinel"
echo ""
echo "To detach from screen:"
echo "  Press Ctrl+A, then D"
echo ""

screen -dmS sentinel bash -c "cd /root/sentinel-alpha && python3 live_trading_bot_aggressive.py 2>&1 | tee logs/bot_console.log"

sleep 3

# Check if started
if screen -list | grep -q sentinel; then
    echo "✅ Bot started successfully!"
    echo ""
    echo "Monitor with:"
    echo "  screen -r sentinel                    # View console"
    echo "  tail -f logs/aggressive_signals.jsonl | jq '.pair,.signal,.confidence'  # Watch signals"
    echo "  tail -f logs/aggressive_trades.jsonl | jq '.'   # Watch trades"
    echo ""
    echo "To reconnect: screen -r sentinel"
else
    echo "❌ Failed to start bot"
    exit 1
fi
