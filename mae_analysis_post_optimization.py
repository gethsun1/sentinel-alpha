
import json
import pandas as pd
from datetime import datetime, timezone

RESTART_TS = 1768915800000 

def mae_analysis_cross_ref():
    # 1. Load AI Logs for entry details
    ai_entries = []
    try:
        with open("logs/ai_logs_submitted.jsonl", "r") as f:
            for line in f:
                try:
                    log = json.loads(line)
                    ts_str = log.get('timestamp')
                    dt = pd.to_datetime(ts_str)
                    ts_ms = int(dt.timestamp() * 1000)
                    if ts_ms >= RESTART_TS:
                        payload = log.get('payload', {})
                        input_data = payload.get('input', {})
                        output_data = payload.get('output', {})
                        ai_entries.append({
                            'order_id': log.get('order_id'),
                            'symbol': input_data.get('symbol'),
                            'direction': output_data.get('signal'),
                            'entry_price': output_data.get('entry_price'),
                            'entry_ts': ts_ms,
                            'atr': input_data.get('parameters', {}).get('atr', 0)
                        })
                except: pass
    except: pass

    if not ai_entries:
        print("No AI entries found since restart.")
        return

    # 2. Load high-res ticker data
    tickers = []
    try:
        with open("logs/live_signals.jsonl", "r") as f:
            for line in f:
                try:
                    t = json.loads(line)
                    if t.get('timestamp_ms', 0) >= RESTART_TS:
                        tickers.append(t)
                except: pass
    except: pass
    
    if not tickers:
        print("No high-res ticker data found.")
        return
    
    df_tickers = pd.DataFrame(tickers)
    df_tickers['price'] = df_tickers['price'].astype(float)
    
    results = []
    for entry in ai_entries:
        symbol = entry['symbol']
        entry_price = float(entry['entry_price'])
        direction = entry['direction']
        entry_ts = entry['entry_ts']
        atr = entry['atr']
        
        # Look for max/min price in the NEXT 4 HOURS or until now
        # (Assuming most trades close within 4h)
        window_end = entry_ts + (4 * 3600 * 1000)
        
        subset = df_tickers[
            (df_tickers['symbol'] == symbol) & 
            (df_tickers['timestamp_ms'] > entry_ts) &
            (df_tickers['timestamp_ms'] <= window_end)
        ]
        
        if subset.empty: continue
        
        prices = subset['price']
        
        if direction == 'LONG':
            min_p = prices.min()
            max_p = prices.max()
            mae = entry_price - min_p
            mfe = max_p - entry_price
        else:
            min_p = prices.min()
            max_p = prices.max()
            mae = max_p - entry_price
            mfe = entry_price - min_p
            
        results.append({
            'symbol': symbol,
            'mae_atr': mae / atr if atr > 0 else 0,
            'mfe_atr': mfe / atr if atr > 0 else 0
        })
        
    df_res = pd.DataFrame(results)
    if df_res.empty:
        print("No overlap found between trades and high-res ticker logs.")
        return
        
    print(f"\nMAE/ATR Analysis for {len(df_res)} trades since Jan 20:")
    print(df_res['mae_atr'].describe())
    
    premature_8 = len(df_res[df_res['mae_atr'] > 0.8])
    premature_11 = len(df_res[df_res['mae_atr'] >= 1.1])
    premature_12 = len(df_res[df_res['mae_atr'] >= 1.2]) # New range stop
    premature_15 = len(df_res[df_res['mae_atr'] >= 1.5]) # New trend stop
    
    print(f"\nFailure Analysis:")
    print(f"Trades hitting 0.8x ATR (Old baseline): {premature_8} ({premature_8/len(df_res)*100:.1f}%)")
    print(f"Trades hitting 1.1x ATR (Compression SL): {premature_11} ({premature_11/len(df_res)*100:.1f}%)")
    print(f"Trades hitting 1.2x ATR (Range SL):       {premature_12} ({premature_12/len(df_res)*100:.1f}%)")
    print(f"Trades hitting 1.5x ATR (Trend SL):       {premature_15} ({premature_15/len(df_res)*100:.1f}%)")

if __name__ == "__main__":
    mae_analysis_cross_ref()
