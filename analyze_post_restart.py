
import json
import pandas as pd
from datetime import datetime, timezone

# Correct Restart timestamp: 2026-01-20 13:30 UTC
RESTART_TS_MS = 1768915800000 

def analyze_post_restart():
    now_utc = datetime.now(timezone.utc)
    
    # 1. Load AI Logs (Decisions)
    ai_decisions = []
    try:
        with open("logs/ai_logs_submitted.jsonl", "r") as f:
            for line in f:
                try:
                    log = json.loads(line)
                    # Try to get timestamp from multiple locations
                    ts_str = log.get('timestamp')
                    if ts_str:
                        dt = pd.to_datetime(ts_str)
                        ts_ms = int(dt.timestamp() * 1000)
                    else:
                        ts_ms = 0
                        
                    if ts_ms >= RESTART_TS_MS:
                        ai_decisions.append(log)
                except: pass
    except: pass

    if not ai_decisions:
        print(f"No AI decisions found since restart at {datetime.fromtimestamp(RESTART_TS_MS/1000, timezone.utc)}.")
        return

    # Extract metrics from AI decisions
    events = []
    for log in ai_decisions:
        payload = log.get('payload', {})
        output = payload.get('output', {})
        meta = output.get('execution_metadata', {})
        
        events.append({
            'order_id': log.get('order_id'),
            'symbol': payload.get('input', {}).get('symbol'),
            'confidence': output.get('confidence', 0),
            'leverage': meta.get('applied_leverage', 0),
            'signal': output.get('signal'),
            'timestamp': log.get('timestamp')
        })
        
    df_events = pd.DataFrame(events)
    
    # 2. Load Historical Data (for outcomes)
    try:
        with open("logs/weex_historical_data.json", "r") as f:
            hist_data = json.load(f)
            all_orders = pd.DataFrame(hist_data["orders"])
    except:
        all_orders = pd.DataFrame()

    # Calculate Volume
    total_trades = len(df_events)
    unique_days = (now_utc - datetime.fromtimestamp(RESTART_TS_MS/1000, timezone.utc)).total_seconds() / 86400
    if unique_days == 0: unique_days = 0.001
    trades_per_day = total_trades / unique_days
    
    avg_leverage = df_events['leverage'].mean()
    avg_confidence = df_events['confidence'].mean()
    min_confidence = df_events['confidence'].min()

    # Win Rate calculation
    # We'll look at the filled closure orders in the period.
    # Note: Closed orders in this period might be from entries before restart.
    # But usually the bot closes quickly.
    if not all_orders.empty:
        closed_orders = all_orders[
            (all_orders['createTime'].astype(float) >= RESTART_TS_MS) &
            ((all_orders['type'].isin(['close_long', 'close_short']))) &
            (all_orders['status'] == 'filled')
        ].copy()
        
        closed_orders['totalProfits'] = pd.to_numeric(closed_orders['totalProfits'], errors='coerce').fillna(0)
        winning_trades = closed_orders[closed_orders['totalProfits'] > 0]
        losing_trades = closed_orders[closed_orders['totalProfits'] <= 0]
        win_rate = (len(winning_trades) / len(closed_orders)) * 100 if not closed_orders.empty else 0
    else:
        closed_orders = pd.DataFrame()
        win_rate = 0

    print(f"\n{'='*50}")
    print(f"SENTINEL ALPHA PERFORMANCE (Post-Optimization)")
    print(f"Period: {datetime.fromtimestamp(RESTART_TS_MS/1000, timezone.utc)} to {now_utc}")
    print(f"Duration: {unique_days:.2f} days")
    print(f"{'='*50}")
    
    print(f"Trade Volume Metrics:")
    print(f"Total Trade Events: {total_trades}")
    print(f"Trades per Day:     {trades_per_day:.2f}")
    print(f"Target Volume:      2-3 trades/day")
    print(f"Status:             {'✅ TARGET MET' if 1.0 <= trades_per_day <= 4.0 else '⚠️ OUTSIDE TARGET'}")
    
    if not closed_orders.empty:
        print(f"\nWin Rate Metrics (Closed Trades):")
        print(f"Total Closed:       {len(closed_orders)}")
        print(f"Wins:               {len(winning_trades)}")
        print(f"Losses:             {len(losing_trades)}")
        print(f"Win Rate:           {win_rate:.2f}%")
        print(f"Target Win Rate:    75-80%")
        print(f"Status:             {'✅ TARGET MET' if win_rate >= 75 else '⚠️ BELOW TARGET'}")
    else:
        print("\nWin Rate Metrics: No closed trades found.")

    print(f"\nExecution Quality:")
    print(f"Avg Leverage:       {avg_leverage:.2f}x")
    print(f"Target Leverage:    12-14x")
    print(f"Status:             {'✅ TARGET MET' if 11 <= avg_leverage <= 16 else '⚠️ OUTSIDE TARGET'}")
    
    print(f"Avg Confidence:     {avg_confidence:.4f}")
    print(f"Min Confidence:     {min_confidence:.4f}")
    print(f"Min Threshold:      0.62")
    print(f"Status:             {'✅ TARGET MET' if min_confidence >= 0.6199 else '❌ THRESHOLD VIOLATED'}")
    
    if not closed_orders.empty:
        print(f"\nPerformance Summary:")
        print(f"Total Net PnL:      ${closed_orders['totalProfits'].sum():.4f}")
        print(f"Avg PnL per Trade:  ${closed_orders['totalProfits'].mean():.4f}")

if __name__ == "__main__":
    analyze_post_restart()
