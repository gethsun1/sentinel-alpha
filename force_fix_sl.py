
import os
import sys
import time
import math
from dotenv import load_dotenv

# Load env from .env file explicitly
load_dotenv()

# Add parent dir to path to import adapter
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from execution.weex_adapter import WeexExecutionAdapter

def round_price_to_step(value, price_step):
    rounded = round(round(value / price_step) * price_step, 4)
    if price_step >= 1:
        rounded = int(rounded)
    return rounded

def main():
    print("FORCE FIXING MISSING SLs...")
    
    api_key = os.getenv("WEEX_API_KEY")
    secret_key = os.getenv("WEEX_SECRET_KEY")
    passphrase = os.getenv("WEEX_PASSPHRASE")
    
    adapter = WeexExecutionAdapter(
        api_key=api_key,
        secret_key=secret_key,
        passphrase=passphrase,
        default_symbol="cmt_btcusdt"
    )
    
    # Get Positions
    try:
        positions = adapter.get_positions()
        data_list = positions if isinstance(positions, list) else positions.get('data', [])
        
        active_positions = [
            p for p in data_list 
            if abs(float(p.get('holdAmount', p.get('size', 0)))) > 0
        ]
        
        if not active_positions:
            print("No active positions found.")
            return

        print(f"Found {len(active_positions)} active positions.")
        
        for pos in active_positions:
            symbol = pos.get('symbol')
            size = float(pos.get('holdAmount', pos.get('size', 0)))
            side = str(pos.get('side', '')).upper()
            avg_price = float(pos.get('avgPrice', 0))
            
            print(f"Checking {symbol} ({side} {size})...")
            
            # Check for existing SL (Plan)
            adapter.symbol = symbol
            has_sl = False
            try:
                # Quick check - just assume missing if we are forced to fix.
                # Or check deeply. Let's check 'currentPlan'
                plans = adapter._get("/capi/v2/order/currentPlan", {"symbol": symbol})
                p_list = plans if isinstance(plans, list) else plans.get('data', [])
                for p in p_list:
                    if p.get('planType') == 'loss_plan' and p.get('status') == 'active':
                        has_sl = True
                        print(f"  [OK] Found active SL at {p.get('triggerPrice')}")
                        break
            except Exception as e:
                print(f"  Error checking plans: {e}")
            
            if not has_sl:
                print(f"  [WARNING] Missing SL! Fixing...")
                
                # Get Price (Entry or Current)
                reference_price = avg_price
                if reference_price <= 0:
                    print(f"  [INFO] Entry price 0.0, fetching market price...")
                    ticker = adapter.get_ticker(symbol)
                    reference_price = float(ticker['last'])
                    print(f"  [INFO] Market Price: {reference_price}")
                
                if reference_price <= 0:
                    print("  [ERROR] Could not determine price. Skipping.")
                    continue
                    
                # Calculate SL
                sl_pct = 0.02
                if side == 'LONG' or (side == '' and size > 0): # Assuming Long
                     sl_price = reference_price * (1 - sl_pct)
                     sl_side = 'long'
                else:
                     sl_price = reference_price * (1 + sl_pct)
                     sl_side = 'short'
                
                # Rounding (Roughly, hardcoded step for now or fetch)
                # Fetch rules quickly
                rules = adapter.get_symbol_rules(symbol)
                price_step = float(rules.get('price_step', 0.1))
                sl_price = round_price_to_step(sl_price, price_step)
                
                print(f"  [ACTION] Placing SL at {sl_price}...")
                res = adapter.place_tp_sl_order('loss_plan', sl_price, abs(size), sl_side)
                print(f"  [RESULT] {res}")
                
    except Exception as e:
        print(f"Global error: {e}")

if __name__ == "__main__":
    main()
