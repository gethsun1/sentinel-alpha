#!/usr/bin/env python3
"""
Fix missing TP for positions that had TP2 executed
Specifically for XRP and BNB short positions
"""
import os
import sys
import time
from dotenv import load_dotenv

load_dotenv()

from execution.weex_adapter import WeexExecutionAdapter
from strategy.tpsl_calculator import TPSLCalculator

def round_price_to_step(price: float, step: float) -> float:
    """Round price to nearest step"""
    if step <= 0:
        return price
    return round(price / step) * step

def main():
    print("=" * 70)
    print("FIX MISSING TP FOR POSITIONS (After TP2 Execution)")
    print("=" * 70)
    print()
    
    # User-provided entry prices
    entry_prices = {
        'cmt_bnbusdt': 886.58,
        'cmt_xrpusdt': 1.9316,
        'cmt_ethusdt': None  # Will try to get from API
    }
    
    # Initialize adapter
    adapter = WeexExecutionAdapter(
        api_key=os.getenv("WEEX_API_KEY"),
        secret_key=os.getenv("WEEX_SECRET_KEY"),
        passphrase=os.getenv("WEEX_PASSPHRASE"),
        default_symbol="cmt_btcusdt"
    )
    
    # Initialize TP/SL calculator
    tpsl_calc = TPSLCalculator(
        min_rr_ratio=1.2,
        max_rr_ratio=3.0,
        base_sl_multiplier=1.0,
        base_tp_multiplier=2.0
    )
    
    # Fetch positions
    print("📋 Fetching positions...")
    try:
        pos_res = adapter.get_positions()
        positions = pos_res if isinstance(pos_res, list) else pos_res.get('data', [])
        
        active_positions = [
            p for p in positions 
            if abs(float(p.get('size', p.get('holdAmount', 0)))) > 0
            and p.get('symbol') in entry_prices.keys()
        ]
        
        if not active_positions:
            print("  ℹ️  No matching positions found")
            return
        
        print(f"  ✓ Found {len(active_positions)} position(s) to fix\n")
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return
    
    # Process each position
    for pos in active_positions:
        symbol = pos.get('symbol', '')
        side_str = pos.get('side', '').upper()
        size = abs(float(pos.get('size', pos.get('holdAmount', 0))))
        
        if side_str not in ['SHORT', '2']:
            print(f"  ⚠️  Skipping {symbol} - not a SHORT position")
            continue
        
        direction = 'SHORT'
        position_side = 'short'
        
        # Get entry price
        entry_price = entry_prices.get(symbol)
        if not entry_price:
            entry_price = float(pos.get('avgPrice', 0))
            if entry_price <= 0:
                print(f"  ⚠️  {symbol}: Could not determine entry price, skipping")
                continue
        
        print(f"\n[{symbol}] SHORT {size} @ ${entry_price:.4f}")
        print("-" * 70)
        
        adapter.symbol = symbol
        
        # Get current price
        try:
            ticker = adapter.get_ticker(symbol)
            current_price = float(ticker.get('last', 0))
            print(f"  Current Price: ${current_price:.4f}")
        except Exception as e:
            print(f"  ❌ Could not get current price: {e}")
            continue
        
        # Get price step
        rules = adapter.get_symbol_rules(symbol)
        price_step = float(rules.get('price_step', 0.1))
        
        # Calculate ATR (estimate from price movement)
        # Use 2% of price as ATR estimate for conservative approach
        atr_estimate = current_price * 0.02
        print(f"  Estimated ATR: ${atr_estimate:.4f}")
        
        # Calculate TP for runner (4.5× ATR from entry, as per fixed code)
        # For SHORT: TP = entry - 4.5×ATR
        runner_tp = entry_price - (atr_estimate * 4.5)
        runner_tp = round_price_to_step(runner_tp, price_step)
        
        # Ensure TP is below current price for SHORT
        if runner_tp >= current_price:
            # If calculated TP is above current, use 2% below current as conservative TP
            runner_tp = round_price_to_step(current_price * 0.98, price_step)
            print(f"  ⚠️  Adjusted TP to be below current price")
        
        # Calculate SL (trailing stop: current + 1×ATR for SHORT)
        trailing_sl = current_price + atr_estimate
        trailing_sl = round_price_to_step(trailing_sl, price_step)
        
        print(f"  🎯 Runner TP: ${runner_tp:.4f}")
        print(f"  🛑 Trailing SL: ${trailing_sl:.4f}")
        print()
        
        # Place TP order
        print(f"  🟢 Placing TP order @ ${runner_tp:.4f}...")
        try:
            tp_result = adapter.place_tp_sl_order(
                plan_type='profit_plan',
                trigger_price=runner_tp,
                size=size,
                position_side=position_side,
                execute_price=0,
                margin_mode=1
            )
            
            if isinstance(tp_result, list) and len(tp_result) > 0:
                tp_result = tp_result[0]
            
            if tp_result.get('success') or tp_result.get('orderId', 0) > 0:
                print(f"  ✓ TP order placed successfully (ID: {tp_result.get('orderId', 'N/A')})")
            else:
                print(f"  ⚠️  TP order response: {tp_result}")
        except Exception as e:
            print(f"  ❌ Error placing TP: {e}")
        
        # Small delay
        time.sleep(0.5)
        
        # Place SL order (trailing stop)
        print(f"  🔴 Placing trailing SL @ ${trailing_sl:.4f}...")
        try:
            sl_result = adapter.place_tp_sl_order(
                plan_type='loss_plan',
                trigger_price=trailing_sl,
                size=size,
                position_side=position_side,
                execute_price=0,
                margin_mode=1
            )
            
            if isinstance(sl_result, list) and len(sl_result) > 0:
                sl_result = sl_result[0]
            
            if sl_result.get('success') or sl_result.get('orderId', 0) > 0:
                print(f"  ✓ SL order placed successfully (ID: {sl_result.get('orderId', 'N/A')})")
            else:
                print(f"  ⚠️  SL order response: {sl_result}")
        except Exception as e:
            print(f"  ❌ Error placing SL: {e}")
        
        print()
    
    print("=" * 70)
    print("✅ Done! Please verify TP/SL orders were placed correctly.")
    print("=" * 70)

if __name__ == "__main__":
    main()
