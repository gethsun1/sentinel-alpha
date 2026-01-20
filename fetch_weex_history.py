
import os
import sys
import json
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from execution.weex_adapter import WeexExecutionAdapter
from dotenv import load_dotenv

# Load credentials from .env
load_dotenv()

class WeexHistoryFetcher:
    def __init__(self):
        self.adapter = WeexExecutionAdapter(
            api_key=os.getenv("WEEX_API_KEY"),
            secret_key=os.getenv("WEEX_SECRET_KEY"),
            passphrase=os.getenv("WEEX_PASSPHRASE"),
            default_symbol="cmt_btcusdt"
        )
        self.symbols = [
            "cmt_btcusdt", "cmt_ethusdt", "cmt_solusdt", 
            "cmt_dogeusdt", "cmt_xrpusdt", "cmt_adausdt", 
            "cmt_bnbusdt", "cmt_ltcusdt"
        ]

    def get_order_history(self, symbol, days=3):
        """Fetch historical normal orders"""
        now = int(time.time() * 1000)
        start_time = now - (days * 24 * 60 * 60 * 1000)
        
        path = "/capi/v2/order/history"
        params = {
            "symbol": symbol,
            "pageSize": 100,
            "createDate": start_time
        }
        return self.adapter._get(path, params)

    def get_plan_history(self, symbol, days=3):
        """Fetch historical conditional (TP/SL) orders"""
        now = int(time.time() * 1000)
        start_time = now - (days * 24 * 60 * 60 * 1000)
        
        path = "/capi/v2/order/historyPlan"
        params = {
            "symbol": symbol,
            "pageSize": 100,
            "startTime": start_time,
            "endTime": now
        }
        return self.adapter._get(path, params)

    def fetch_all(self, days=10):
        results = {
            "orders": [],
            "plan_orders": []
        }
        
        for sym in self.symbols:
            print(f"Fetching history for {sym}...")
            
            # Standard orders
            orders = self.get_order_history(sym, days=days)
            if isinstance(orders, list):
                results["orders"].extend(orders)
            elif isinstance(orders, dict) and "data" in orders:
                 results["orders"].extend(orders.get("data", []))
            elif isinstance(orders, dict) and "list" in orders:
                 results["orders"].extend(orders.get("list", []))
            
            # Plan orders (TP/SL)
            plans = self.get_plan_history(sym, days=days)
            if isinstance(plans, list):
                results["plan_orders"].extend(plans)
            elif isinstance(plans, dict) and "data" in plans:
                 results["plan_orders"].extend(plans.get("data", []))
            elif isinstance(plans, dict) and "list" in plans:
                 results["plan_orders"].extend(plans.get("list", []))
            
            time.sleep(0.5) # Rate limiting
            
        return results

if __name__ == "__main__":
    fetcher = WeexHistoryFetcher()
    data = fetcher.fetch_all()
    
    output_file = "logs/weex_historical_data.json"
    with open(output_file, "w") as f:
        json.dump(data, f, indent=2)
    
    print(f"\nFetched {len(data['orders'])} standard orders and {len(data['plan_orders'])} plan orders.")
    print(f"Data saved to {output_file}")
