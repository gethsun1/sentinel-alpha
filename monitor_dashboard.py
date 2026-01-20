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

# Paths - Support both regular and aggressive bot logs
BASE_DIR = Path(__file__).parent
LOGS_DIR = BASE_DIR / "logs"

# Try aggressive bot logs first, fallback to regular logs
PERFORMANCE_LOG = LOGS_DIR / "aggressive_performance.jsonl"
SIGNALS_LOG = LOGS_DIR / "aggressive_signals.jsonl"
TRADES_LOG = LOGS_DIR / "aggressive_trades.jsonl"

# Fallback to regular logs if aggressive don't exist
if not PERFORMANCE_LOG.exists():
    PERFORMANCE_LOG = LOGS_DIR / "performance.jsonl"
if not SIGNALS_LOG.exists():
    SIGNALS_LOG = LOGS_DIR / "live_signals.jsonl"
if not TRADES_LOG.exists():
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

def get_log_files(pattern):
    """Get all log files matching pattern"""
    return list(LOGS_DIR.glob(pattern))

def read_last_line_all_files(pattern):
    """Read last line from all matching files and return list"""
    results = []
    for filepath in get_log_files(pattern):
        line = read_last_line(filepath)
        if line:
            # Inject symbol if missing (from filename)
            if 'symbol' not in line:
                try:
                    # Extract symbol from filename: live_trades_cmt_btcusdt.jsonl
                    symbol = filepath.stem.split('_', 2)[2]
                    line['symbol'] = symbol
                except:
                    pass
            results.append(line)
    return results

def parse_timestamp(ts_value):
    """
    Normalize timestamps to milliseconds since epoch.
    Accepts epoch ms, epoch seconds, or ISO 8601 strings.
    """
    if ts_value is None:
        return None
    if isinstance(ts_value, (int, float)):
        # Heuristic: treat large numbers as ms
        if ts_value > 1e12:
            return int(ts_value)
        return int(ts_value * 1000)
    try:
        return int(datetime.fromisoformat(ts_value.replace("Z", "+00:00")).timestamp() * 1000)
    except Exception:
        return None

def collect_entries(primary_path: Path, pattern: str):
    """
    Combine entries from a primary log file and pattern-based files.
    """
    entries = []
    base_entry = read_last_line(primary_path)
    if base_entry:
        entries.append(base_entry)
    entries.extend(read_last_line_all_files(pattern))
    return entries

def read_all_trades(n=50):
    """Read last N trades from all files combined"""
    all_trades = read_last_n_lines(TRADES_LOG, n)
    for filepath in get_log_files("live_trades_*.jsonl"):
        trades = read_last_n_lines(filepath, n)
        for trade in trades:
            # Inject symbol
            if 'symbol' not in trade:
                try:
                     symbol = filepath.stem.split('_', 2)[2]
                     trade['symbol'] = symbol
                except:
                    pass
            all_trades.append(trade)
    
    # Sort by timestamp descending
    all_trades.sort(key=lambda x: parse_timestamp(x.get('timestamp')) or 0, reverse=True)
    return all_trades[:n]

def read_all_signals(n=50):
    """Read last N signals from all files"""
    all_signals = read_last_n_lines(SIGNALS_LOG, n)
    for filepath in get_log_files("live_signals_*.jsonl"):
        signals = read_last_n_lines(filepath, n)
        for sig in signals:
            if 'symbol' not in sig:
                try:
                    symbol = filepath.stem.split('_', 2)[2]
                    sig['symbol'] = symbol
                except:
                    pass
            all_signals.append(sig)
    
    all_signals.sort(key=lambda x: parse_timestamp(x.get('timestamp')) or 0, reverse=True)
    return all_signals[:n]

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
    
    # Read performance from all bots
    perf_list = collect_entries(PERFORMANCE_LOG, "performance_*.jsonl")
    
    # Aggregate performance
    total_equity = 0.0
    total_pnl = 0.0
    total_trades = 0
    total_initial = 0.0
    peak_equity_sum = 0.0
    
    active_pairs = len(perf_list)
    
    for p in perf_list:
        # Equity is shared (same account), so we shouldn't sum it. 
        # But locally each bot might track slightly different PnL updates.
        # We take the AVERAGE equity reported by active bots to represent the account state.
        # Total PnL *is* the sum of individual bot PnLs if they track session PnL.
        
        ts = parse_timestamp(p.get('timestamp'))
        if ts is not None:
            p['timestamp'] = ts
        
        eq = p.get('equity', 1000.0)
        total_equity += eq
        peak_equity_sum += p.get('peak_equity', 1000.0)
        
        total_pnl += p.get('total_pnl', 0.0)
        total_trades += p.get('trades', 0)
        
    # Correct Equity Calculation: 
    # Since all bots share the SAME account, their 'current_equity' should be roughly identical 
    # (synced from API). Summing them is wrong ($1000*8=$8000).
    # We should take the MAX equity reported (most recent update) or Average.
    if active_pairs > 0:
        actual_account_equity = total_equity / active_pairs  # Average them
        actual_peak_equity = peak_equity_sum / active_pairs
    else:
        actual_account_equity = 1000.0
        actual_peak_equity = 1000.0
        
    # Use the corrected values for display
    total_equity = actual_account_equity
    peak_equity_sum = actual_peak_equity
        
    # Initial is now just the account start (approx 1000)
    total_initial = 1000.0
    
    # If no bots running, show defaults
    if total_equity == 0: 
        total_equity = 1000.0
        total_initial = 1000.0
        
    roi = (total_equity - total_initial) / total_initial
    drawdown = (peak_equity_sum - total_equity) / peak_equity_sum if peak_equity_sum > 0 else 0.0
    
    perf = {
        'equity': total_equity,
        'peak_equity': peak_equity_sum,
        'drawdown': drawdown,
        'roi': roi,
        'total_pnl': total_pnl,
        'trades': total_trades,
        'win_rate': 0.0, # Complex to average
        'active_pairs': active_pairs,
        'timestamp': int(datetime.now().timestamp() * 1000)
    }
    
    # Read recent signals (aggregated)
    recent_signals = read_all_signals(10)
    
    # Read recent trades (aggregated)
    recent_trades = read_all_trades(10)
    
    # Count totals (approximate)
    total_signals = len(read_all_signals(1000))

    
    
    # Calculate signal distribution
    all_signals = read_all_signals(200)
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
            ts_val = parse_timestamp(sig.get('timestamp'))
            if ts_val:
                sig['timestamp'] = ts_val
                sig['timestamp_formatted'] = datetime.fromtimestamp(
                    ts_val / 1000
                ).strftime('%H:%M:%S')
    
    # Format recent trades
    for trade in recent_trades:
        if 'timestamp' in trade:
            ts_val = parse_timestamp(trade.get('timestamp'))
            if ts_val:
                trade['timestamp'] = ts_val
                trade['timestamp_formatted'] = datetime.fromtimestamp(
                    ts_val / 1000
                ).strftime('%H:%M:%S')
    
    # Calculate improvement metrics
    total_trade_signals = signal_counts.get('LONG', 0) + signal_counts.get('SHORT', 0)
    total_all = sum(signal_counts.values()) or 1
    trade_signal_pct = (total_trade_signals / total_all) * 100
    
    # Status message
    status_message = "🟢 ACTIVE - Signal Generation Fixed!"
    if trade_signal_pct > 10:
        status_message = "🚀 EXCELLENT - High Quality Signals!"
    elif trade_signal_pct > 3:
        status_message = "✅ GOOD - Signal Generation Improved!"
    elif trade_signal_pct == 0:
        status_message = "⚠️ WARNING - No Trade Signals"
    
    return jsonify({
        'performance': perf or {},
        'recent_signals': recent_signals,
        'recent_trades': recent_trades,
        'total_signals': total_signals,
        'total_trades': total_trades,
        'signal_distribution': signal_counts,
        'bot_running': perf is not None,
        'last_update': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'),
        'trade_signal_percentage': round(trade_signal_pct, 1),
        'status_message': status_message,
        'improvement_note': f"Before: 0% | Now: {trade_signal_pct:.1f}%"
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

