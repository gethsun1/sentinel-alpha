
import os
import sys
import json
import time
from dotenv import load_dotenv

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from execution.weex_adapter import WeexExecutionAdapter

def main():
    load_dotenv()
    adapter = WeexExecutionAdapter(
        api_key=os.getenv("WEEX_API_KEY"),
        secret_key=os.getenv("WEEX_SECRET_KEY"),
        passphrase=os.getenv("WEEX_PASSPHRASE"),
        default_symbol="cmt_btcusdt"
    )

    print("Fetching positions...")
    positions = adapter.get_positions()
    data_list = positions if isinstance(positions, list) else positions.get('data', [])
    
    active_symbols = []
    for pos in data_list:
        sym = pos.get('symbol')
        size = float(pos.get('holdAmount', pos.get('size', 0)))
        if abs(size) > 0:
            print(f"Active Position: {sym} Size: {size}")
            active_symbols.append(sym)

    print("\nFetching Current Plan Orders (TP/SL)...")
    total_orders = 0
    
    for sym in active_symbols:
        print(f"\n--- {sym} ---")
        try:
            # Fetch current plans
            plans = adapter._get("/capi/v2/order/currentPlan", {"symbol": sym})
            p_list = plans if isinstance(plans, list) else plans.get('data', [])
            
            print(f"Found {len(p_list)} active plan orders.")
            total_orders += len(p_list)
            
            sl_count = 0
            tp_count = 0
            for p in p_list:
                print(f"DEBUG: First Plan Object Keys: {list(p.keys())}")
                print(f"DEBUG: First Plan Object: {p}")
                ptype = p.get('planType')

                status = p.get('status')
                trigger = p.get('triggerPrice')
                oid = p.get('orderId')
                
                print(f"  [{oid}] {ptype} Status: {status} Trigger: {trigger}")
                
                if ptype == 'loss_plan':
                    sl_count += 1
                elif ptype == 'profit_plan':
                    tp_count += 1
            
            if sl_count > 1:
                print(f"  Created {sl_count} SL orders! (REDUNDANT)")
                
        except Exception as e:
            print(f"Error fetching plans for {sym}: {e}")

    print(f"\nTotal Active Plan Orders found: {total_orders}")

if __name__ == "__main__":
    main()
