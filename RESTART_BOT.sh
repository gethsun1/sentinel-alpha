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
pkill -f "live_trading_bot_aggressive.py"
pkill -f "live_trading_bot.py"
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

echo "Starting bot with improved signal generation..."
echo "- Confidence threshold: 0.45 (was 0.65-0.70)"
echo "- Volatility detection: More sensitive"
echo "- Range market trading: ENABLED"
echo "- Signal generation: Optimized for low-volatility markets"
echo ""

# Start the aggressive bot (it's already configured for multiple pairs)
echo "Launching aggressive trading bot in background..."
nohup python live_trading_bot_aggressive.py > logs/bot.log 2>&1 &

sleep 3

# Check if bot started
if pgrep -f "live_trading_bot_aggressive.py" > /dev/null; then
    echo "✓ Bot started successfully!"
    echo ""
    echo "Monitor with:"
    echo "  tail -f logs/live_signals.jsonl"
    echo "  python monitor_dashboard.py"
    echo ""
    echo "Expected improvements:"
    echo "  - Signal generation increased from 0% to 60-80%"
    echo "  - Bot should start trading within 5-10 minutes"
    echo "  - Dashboard should show LONG/SHORT signals, not just NO-TRADE"
else
    echo "✗ Failed to start bot. Check logs for errors."
    exit 1
fi

echo "======================================================================="

