
import os
import time
import json
from datetime import datetime, timedelta, timezone
from execution.weex_adapter import WeexExecutionAdapter
from dotenv import load_dotenv

load_dotenv()

def analyze_24h():
    symbols = [
        "cmt_btcusdt", "cmt_ethusdt", "cmt_solusdt", "cmt_dogeusdt",
        "cmt_xrpusdt", "cmt_adausdt", "cmt_bnbusdt", "cmt_ltcusdt"
    ]
    
    adapter = WeexExecutionAdapter(
        api_key=os.getenv("WEEX_API_KEY"),
        secret_key=os.getenv("WEEX_SECRET_KEY"),
        passphrase=os.getenv("WEEX_PASSPHRASE"),
        default_symbol=symbols[0]
    )
    
    now = datetime.now(timezone.utc)
    one_day_ago = now - timedelta(hours=24)
    print(f"Analyzing trades from {one_day_ago} to {now}")
    
    all_fills = []
    for sym in symbols:
        try:
            print(f"Fetching fills for {sym}...")
            res = adapter.get_fills(sym)
            time.sleep(1.2) # Throttle to avoid 521/block
            if isinstance(res, dict) and 'data' in res:
                fills = res['data']
                if isinstance(fills, list):
                    for fill in fills:
                        # Convert ms timestamp to datetime
                        ts = int(fill.get('cTime', 0))
                        dt = datetime.fromtimestamp(ts / 1000, timezone.utc)
                        if dt >= one_day_ago:
                            fill['symbol'] = sym
                            fill['datetime'] = dt.isoformat()
                            all_fills.append(fill)
            elif isinstance(res, dict) and 'error' in res:
                print(f"  Warning: API returned error for {sym}: {res['error']}")
        except Exception as e:
            print(f"Error fetching fills for {sym}: {e}")

    if not all_fills:
        print("No fills found in the last 24 hours.")
        return

    # Sort by time
    all_fills.sort(key=lambda x: x['cTime'])
    
    # Weex fills might have side: 'buy'/'sell' and side_msg: 'Open Long', 'Close Long', etc.
    # We need to pair entries and exits to calculate PnL/WinRate
    
    print(f"Total Fill Events: {len(all_fills)}")
    
    wins = 0
    losses = 0
    total_pnl = 0.0
    
    # Simple heuristic: look for 'Close' side_msg
    for fill in all_fills:
        msg = str(fill.get('side_msg', '')).lower()
        if 'close' in msg:
            pnl = float(fill.get('pnl', 0))
            total_pnl += pnl
            if pnl > 0:
                wins += 1
            else:
                losses += 1
            
            print(f"[{fill['datetime']}] {fill['symbol']} {msg.upper()}: PnL=${pnl:.4f}")

    total_closed = wins + losses
    win_rate = (wins / total_closed * 100) if total_closed > 0 else 0
    
    print("\n" + "="*30)
    print(f"24H SUMMARY")
    print(f"Total Closed Trades: {total_closed}")
    print(f"Wins: {wins}")
    print(f"Losses: {losses}")
    print(f"Win Rate: {win_rate:.2f}%")
    print(f"Total PnL: ${total_pnl:.2f}")
    print("="*30)

if __name__ == "__main__":
    analyze_24h()
