#!/usr/bin/env python3
"""
Comprehensive Bot Status Report - Read-only Analysis
Queries WEEX API for current orders/positions and analyzes logs
"""

import os
import sys
import json
from datetime import datetime, timezone
sys.path.insert(0, '/root/sentinel-alpha')

from execution.weex_adapter import WeexExecutionAdapter

def load_env():
    env_path = '/root/sentinel-alpha/.env'
    env = {}
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env[key] = value.strip('"')
    return env

def get_current_orders_and_positions():
    """Query WEEX for all current orders and positions"""
    env = load_env()
    
    symbols = ["cmt_btcusdt", "cmt_ethusdt", "cmt_solusdt", "cmt_dogeusdt", 
               "cmt_xrpusdt", "cmt_adausdt", "cmt_bnbusdt", "cmt_ltcusdt"]
    
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "positions": {},
        "open_orders": {},
        "account_summary": {}
    }
    
    for symbol in symbols:
        adapter = WeexExecutionAdapter(
            api_key=env["WEEX_API_KEY"],
            secret_key=env["WEEX_SECRET_KEY"],
            passphrase=env["WEEX_PASSPHRASE"],
            default_symbol=symbol
        )
        
        # Get current orders
        try:
            orders = adapter._get("/capi/v2/order/current", {"symbol": symbol})
            if orders and isinstance(orders, dict):
                orders_data = orders.get('data', [])
                if orders_data:
                    report["open_orders"][symbol] = orders_data
        except Exception as e:
            print(f"Error fetching orders for {symbol}: {e}")
        
        # Get positions
        try:
            positions = adapter.get_positions()
            if positions:
                report["positions"][symbol] = positions
        except Exception as e:
            print(f"Error fetching positions for {symbol}: {e}")
    
    # Get account info
    try:
        adapter = WeexExecutionAdapter(
            api_key=env["WEEX_API_KEY"],
            secret_key=env["WEEX_SECRET_KEY"],
            passphrase=env["WEEX_PASSPHRASE"],
            default_symbol=symbols[0]
        )
        account = adapter.get_account()
        if account:
            report["account_summary"] = account
    except Exception as e:
        print(f"Error fetching account: {e}")
    
    return report

def analyze_trade_logs():
    """Analyze live_trades.jsonl for performance metrics"""
    try:
        with open('/root/sentinel-alpha/logs/live_trades.jsonl', 'r') as f:
            trades = [json.loads(line) for line in f if line.strip()]
        
        # Filter last 24 hours
        cutoff = datetime.now(timezone.utc).timestamp() * 1000 - (24 * 3600 * 1000)
        recent_trades = [t for t in trades if t.get('timestamp_ms', 0) > cutoff]
        
        return {
            "total_trades": len(trades),
            "recent_24h_trades": len(recent_trades),
            "recent_trades": recent_trades[-20:] if recent_trades else []
        }
    except Exception as e:
        return {"error": str(e)}

def analyze_trailing_stops():
    """Check for trailing stop activations in logs"""
    try:
        with open('/root/sentinel-alpha/logs/combined_bots.log', 'r') as f:
            lines = f.readlines()
        
        # Look for trailing stop logs
        trailing_logs = [l for l in lines if '🔒' in l or 'Lock:' in l or 'profit_lock_tier' in l]
        
        return {
            "trailing_stop_activations": len(trailing_logs),
            "recent_activations": trailing_logs[-10:] if trailing_logs else []
        }
    except Exception as e:
        return {"error": str(e)}

def analyze_position_flips():
    """Check for position flip activations"""
    try:
        with open('/root/sentinel-alpha/logs/combined_bots.log', 'r') as f:
            lines = f.readlines()
        
        flip_logs = [l for l in lines if 'High-conviction flip' in l or 'flip allowed' in l]
        
        return {
            "position_flip_activations": len(flip_logs),
            "recent_flips": flip_logs[-10:] if flip_logs else []
        }
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    print("="*80)
    print("SENTINEL ALPHA - 20-HOUR STATUS REPORT")
    print("="*80)
    print()
    
    print("1. Fetching current orders and positions from WEEX...")
    status = get_current_orders_and_positions()
    
    print("2. Analyzing trade execution logs...")
    trade_analysis = analyze_trade_logs()
    
    print("3. Checking trailing stop activations...")
    trailing_analysis = analyze_trailing_stops()
    
    print("4. Checking position flip activations...")
    flip_analysis = analyze_position_flips()
    
    # Save full report
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "weex_status": status,
        "trade_analysis": trade_analysis,
        "trailing_stops": trailing_analysis,
        "position_flips": flip_analysis
    }
    
    with open('/root/sentinel-alpha/status_report_20h.json', 'w') as f:
        json.dump(report, f, indent=2)
    
    print()
    print("=" * 80)
    print("REPORT SAVED: /root/sentinel-alpha/status_report_20h.json")
    print("=" * 80)
    
    # Print summary
    print("\nQUICK SUMMARY:")
    print(f"  Active Positions: {len([k for k, v in status['positions'].items() if v])}")
    print(f"  Open Orders: {sum(len(v) for v in status['open_orders'].values())}")
    print(f"  Total Trades (All Time): {trade_analysis.get('total_trades', 0)}")
    print(f"  Recent Trades (24h): {trade_analysis.get('recent_24h_trades', 0)}")
    print(f"  Trailing Stop Activations: {trailing_analysis.get('trailing_stop_activations', 0)}")
    print(f"  Position Flip Activations: {flip_analysis.get('position_flip_activations', 0)}")
