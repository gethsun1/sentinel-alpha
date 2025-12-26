#!/usr/bin/env python3
"""
SENTINEL ALPHA - FLASK MONITORING DASHBOARD
Real-time bot status monitoring via web UI
"""

from flask import Flask, render_template, jsonify
import json
import os
from datetime import datetime
from pathlib import Path

app = Flask(__name__)

# Paths
BASE_DIR = Path(__file__).parent
LOGS_DIR = BASE_DIR / "logs"
PERFORMANCE_LOG = LOGS_DIR / "performance.jsonl"
SIGNALS_LOG = LOGS_DIR / "live_signals.jsonl"
TRADES_LOG = LOGS_DIR / "live_trades.jsonl"

def read_last_line(filepath):
    """Read last line from JSONL file"""
    if not filepath.exists():
        return None
    
    try:
        with open(filepath, 'r') as f:
            lines = f.readlines()
            if lines:
                return json.loads(lines[-1].strip())
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
    return None

def count_lines(filepath):
    """Count lines in file"""
    if not filepath.exists():
        return 0
    try:
        with open(filepath, 'r') as f:
            return sum(1 for _ in f)
    except:
        return 0

def read_last_n_lines(filepath, n=10):
    """Read last N lines from JSONL file"""
    if not filepath.exists():
        return []
    
    try:
        with open(filepath, 'r') as f:
            lines = f.readlines()
            return [json.loads(line.strip()) for line in lines[-n:] if line.strip()]
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
    return []

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('dashboard.html')

@app.route('/api/status')
def api_status():
    """API endpoint for bot status"""
    
    # Read performance
    perf = read_last_line(PERFORMANCE_LOG)
    
    # Read recent signals
    recent_signals = read_last_n_lines(SIGNALS_LOG, 5)
    
    # Read recent trades
    recent_trades = read_last_n_lines(TRADES_LOG, 5)
    
    # Count totals
    total_signals = count_lines(SIGNALS_LOG)
    total_trades = count_lines(TRADES_LOG)
    
    # Calculate signal distribution
    all_signals = read_last_n_lines(SIGNALS_LOG, 100)
    signal_counts = {'LONG': 0, 'SHORT': 0, 'NO-TRADE': 0}
    for sig in all_signals:
        signal_type = sig.get('signal', 'NO-TRADE')
        signal_counts[signal_type] = signal_counts.get(signal_type, 0) + 1
    
    # Format timestamp
    if perf:
        perf['timestamp_formatted'] = datetime.fromtimestamp(
            perf['timestamp'] / 1000
        ).strftime('%Y-%m-%d %H:%M:%S UTC')
    
    # Format recent signals
    for sig in recent_signals:
        if 'timestamp' in sig:
            sig['timestamp_formatted'] = datetime.fromtimestamp(
                sig['timestamp'] / 1000
            ).strftime('%H:%M:%S')
    
    # Format recent trades
    for trade in recent_trades:
        if 'timestamp' in trade:
            trade['timestamp_formatted'] = datetime.fromtimestamp(
                trade['timestamp'] / 1000
            ).strftime('%H:%M:%S')
    
    return jsonify({
        'performance': perf or {},
        'recent_signals': recent_signals,
        'recent_trades': recent_trades,
        'total_signals': total_signals,
        'total_trades': total_trades,
        'signal_distribution': signal_counts,
        'bot_running': perf is not None,
        'last_update': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
    })

@app.route('/api/chart-data')
def chart_data():
    """API endpoint for chart data"""
    
    # Read last 50 performance entries
    perf_data = read_last_n_lines(PERFORMANCE_LOG, 50)
    
    # Extract data for charts
    timestamps = []
    equity_values = []
    drawdown_values = []
    pnl_values = []
    
    for entry in perf_data:
        ts = entry.get('timestamp', 0)
        if ts:
            timestamps.append(datetime.fromtimestamp(ts / 1000).strftime('%H:%M'))
            equity_values.append(entry.get('equity', 1000))
            drawdown_values.append(entry.get('drawdown', 0) * 100)  # Convert to %
            pnl_values.append(entry.get('total_pnl', 0))
    
    return jsonify({
        'timestamps': timestamps,
        'equity': equity_values,
        'drawdown': drawdown_values,
        'pnl': pnl_values
    })

if __name__ == '__main__':
    # Create logs directory if not exists
    LOGS_DIR.mkdir(exist_ok=True)
    
    # Run on all interfaces, port 5000
    print("=" * 70)
    print("SENTINEL ALPHA - MONITORING DASHBOARD")
    print("=" * 70)
    print(f"Starting Flask server...")
    print(f"Access dashboard at:")
    print(f"  - Local: http://localhost:5000")
    print(f"  - Network: http://107.173.192.240:5000")
    print(f"")
    print(f"Press Ctrl+C to stop")
    print("=" * 70)
    
    app.run(host='0.0.0.0', port=5000, debug=False)

