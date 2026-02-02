#!/bin/bash
# Restart Trading Bot with Fixed Signal Generation
# This script will restart the bot to pick up all the signal generation improvements

echo "======================================================================="
echo "SENTINEL ALPHA - BOT RESTART SCRIPT"
echo "======================================================================="
echo ""
echo "This will restart the trading bot with FIXED signal generation logic"
echo ""

# Find and kill existing bot processes
echo "Stopping existing bot processes..."
pkill -f "live_trading_bot.py"
pkill -f "live_trading_bot_aggressive.py"
sleep 2

# Verify processes are stopped
if pgrep -f "live_trading_bot" > /dev/null; then
    echo "⚠️  Warning: Bot processes still running, forcing kill..."
    pkill -9 -f "live_trading_bot"
    sleep 2
fi

echo "✓ Old bot processes stopped"
echo ""

# Navigate to project directory
cd /root/sentinel-alpha

# Activate virtual environment
source venv/bin/activate

echo "Starting bot with FIXED performance signal generation..."
echo "- Confidence threshold: 0.58 (Increased to reduce churn)"
echo "- Volatility detection: 0.6% ATR Floor"
echo "- Signal generation: Optimized for higher quality trades"
echo ""

# Start the bot
echo "Launching trading bot in background..."
nohup python -u live_trading_bot.py > logs/bot.log 2>&1 &

sleep 3

# Check if bot started
if pgrep -f "live_trading_bot.py" > /dev/null; then
    echo "✓ Bot started successfully!"
    echo ""
    echo "Monitor with:"
    echo "  tail -f logs/live_trades.jsonl"
    echo "  python monitor_dashboard.py"
else
    echo "✗ Failed to start bot. Check logs/bot.log for errors."
    exit 1
fi

echo "======================================================================="

