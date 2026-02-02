import os
import sys

def load_env_manual():
    try:
        with open('.env', 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()
    except Exception as e:
        print(f"Error loading .env: {e}")

load_env_manual()

# Now import the original script's logic by reading it and exec-ing it, 
# or just copying the relevant parts. 
# Simplest is to just modify the path or copy-paste the adapter usage.

from execution.weex_adapter import WeexExecutionAdapter

def main():
    print("Checking Positions & SL (No DotEnv)...")
    adapter = WeexExecutionAdapter(
        api_key=os.getenv("WEEX_API_KEY"),
        secret_key=os.getenv("WEEX_SECRET_KEY"),
        passphrase=os.getenv("WEEX_PASSPHRASE"),
        default_symbol="cmt_btcusdt"
    )
    
    try:
        positions = adapter.get_positions()
        data_list = positions if isinstance(positions, list) else positions.get('data', [])
        active = [p for p in data_list if abs(float(p.get('holdAmount', p.get('size', 0)))) > 0]
        
        print(f"Found {len(active)} active positions.")
        
        for pos in active:
            symbol = pos['symbol']
            print(f"Checking {symbol}...")
            adapter.symbol = symbol
            
            # Check Plans
            try:
                # Weex API for plan orders
                import time
                params = {
                    "symbol": symbol,
                    "pageSize": 20,
                    "startTime": int(time.time()*1000) - 86400000 * 3, # 3 days
                    "endTime": int(time.time()*1000)
                }
                plans = adapter._get("/capi/v2/order/historyPlan", params)
                plans_list = plans if isinstance(plans, list) else plans.get('data', [])
                
                active_plans = [p for p in plans_list if p.get('status') in ['NEW', 'PENDING', 'ACTIVE', 'TRIGGERED']]
                
                if not active_plans:
                    print(f"  [CRITICAL] NO ACTIVE PLAN ORDERS (TP/SL) FOR {symbol}!")
                else:
                    for p in active_plans:
                        print(f"  Plan: {p.get('planType')} - Trigger: {p.get('triggerPrice')} - Status: {p.get('status')}")
                        
            except Exception as e:
                print(f"  Error checking plans: {e}")
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
