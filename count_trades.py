
import json
from datetime import datetime, timedelta, timezone

def count_trades():
    log_file = "/root/sentinel-alpha/logs/live_trades.jsonl"
    now = datetime.now(timezone.utc)
    one_day_ago = now - timedelta(hours=24)
    
    total_trades = 0
    symbols_count = {}
    
    with open(log_file, 'r') as f:
        for line in f:
            try:
                trade = json.loads(line)
                ts_str = trade.get('timestamp')
                # Try parsing with and without ms
                try:
                    dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                except:
                    continue
                
                if dt >= one_day_ago:
                    total_trades += 1
                    sym = trade.get('symbol', 'unknown')
                    symbols_count[sym] = symbols_count.get(sym, 0) + 1
            except Exception as e:
                continue
    
    print(f"Total trades opened in last 24h: {total_trades}")
    print("Breakdown by symbol:")
    for sym, count in symbols_count.items():
        print(f"  {sym}: {count}")

if __name__ == "__main__":
    count_trades()
