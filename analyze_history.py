
import json
import pandas as pd
from datetime import datetime

def analyze():
    # Load historical data
    with open("logs/weex_historical_data.json", "r") as f:
        data = json.load(f)
    
    orders = pd.DataFrame(data["orders"])
    if orders.empty:
        print("No orders found to analyze.")
        return

    # Filter for filled closure orders (these contain PnL)
    closed_orders = orders[
        ((orders['type'] == 'close_long') | (orders['type'] == 'close_short')) & 
        (orders['status'] == 'filled')
    ].copy()
    
    if closed_orders.empty:
        print("No filled closure orders found.")
        return

    closed_orders['totalProfits'] = pd.to_numeric(closed_orders['totalProfits'], errors='coerce').fillna(0)
    
    # Win rate metrics
    winning_trades = closed_orders[closed_orders['totalProfits'] > 0]
    losing_trades = closed_orders[closed_orders['totalProfits'] <= 0]
    
    total_trades = len(closed_orders)
    win_rate = (len(winning_trades) / total_trades) * 100 if total_trades > 0 else 0
    total_pnl = closed_orders['totalProfits'].sum()
    
    print(f"\n{'='*40}")
    print(f"OVERALL PERFORMANCE")
    print(f"{'='*40}")
    print(f"Total Closure Orders: {total_trades}")
    print(f"Winning Trades:       {len(winning_trades)}")
    print(f"Losing Trades:        {len(losing_trades)}")
    print(f"Win Rate:             {win_rate:.2f}%")
    print(f"Total PnL:            ${total_pnl:.4f}")
    print(f"Avg PnL per Trade:    ${total_pnl/total_trades:.4f}")

    # Analyze by Symbol
    print(f"\n{'='*40}")
    print(f"PERFORMANCE BY SYMBOL")
    print(f"{'='*40}")
    symbol_stats = closed_orders.groupby('symbol').agg({
        'totalProfits': ['count', 'sum', 'mean'],
        'order_id': 'count'
    })
    
    for symbol, row in symbol_stats.iterrows():
        sym_trades = closed_orders[closed_orders['symbol'] == symbol]
        sym_wins = len(sym_trades[sym_trades['totalProfits'] > 0])
        sym_total = len(sym_trades)
        sym_wr = (sym_wins / sym_total) * 100 if sym_total > 0 else 0
        sym_pnl = sym_trades['totalProfits'].sum()
        print(f"{symbol:15} | Trades: {sym_total:3} | Win Rate: {sym_wr:6.2f}% | PnL: ${sym_pnl:8.4f}")

    # Analyze Exit Type (TP vs SL)
    print(f"\n{'='*40}")
    print(f"EXIT TYPE ANALYSIS")
    print(f"{'='*40}")
    
    # sentinel-alpha prefixes: tpsl-pr (TP), tpsl-lo (SL)
    closed_orders['exit_type'] = 'UNKNOWN'
    closed_orders.loc[closed_orders['client_oid'].str.contains('tpsl-pr', na=False), 'exit_type'] = 'TAKE_PROFIT'
    closed_orders.loc[closed_orders['client_oid'].str.contains('tpsl-lo', na=False), 'exit_type'] = 'STOP_LOSS'
    closed_orders.loc[closed_orders['client_oid'].str.contains('manual', na=False), 'exit_type'] = 'MANUAL'
    
    exit_stats = closed_orders.groupby('exit_type').size()
    for etype, count in exit_stats.items():
        print(f"{etype:15} | Count: {count:3}")

    # Correlate with AI Logs
    print(f"\n{'='*40}")
    print(f"AI LOG CORRELATION (Sample)")
    print(f"{'='*40}")
    
    ai_logs = []
    try:
        with open("logs/ai_logs_submitted.jsonl", "r") as f:
            for line in f:
                try:
                    ai_logs.append(json.loads(line))
                except: pass
    except FileNotFoundError:
        print("AI logs not found.")
        return

    ai_df = pd.DataFrame(ai_logs)
    if ai_df.empty:
        print("AI logs empty.")
        return

    # Match by order_id (AI log entry order ID)
    # This is tricky because one Entry can have multiple partial Exits.
    # We can try to look at the 'reasoning' in AI logs vs outcomes.
    
    # Let's just look at the last 5 AI log decisions and their corresponding outcomes if possible
    for idx, log in ai_df.tail(10).iterrows():
        entry_oid = log.get('order_id')
        symbol = log.get('payload', {}).get('input', {}).get('symbol')
        signal = log.get('payload', {}).get('output', {}).get('signal')
        regime = log.get('payload', {}).get('output', {}).get('regime')
        confidence = log.get('payload', {}).get('output', {}).get('confidence')
        
        # In WEEX, PnL is often on the closing order. The entry order ID isn't directly linked in the close order record
        # unless we track the chain. 
        # But we can look at orders for the same symbol around the same time.
        
        print(f"AI Signal: {signal} {symbol} | Regime: {regime} | Conf: {confidence:.2f}")
        # Find orders for this symbol after the log timestamp
        log_ts = log.get('timestamp')
        # ... logic to match could be complex, skipping for now ...

if __name__ == "__main__":
    analyze()
