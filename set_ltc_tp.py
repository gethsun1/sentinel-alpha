#!/usr/bin/env python3
"""
Set TP for LTC Long position
Entry: 69.1
"""

import os
import sys
import json
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from execution.weex_adapter import WeexExecutionAdapter
from strategy.tpsl_calculator import TPSLCalculator
from dotenv import load_dotenv

# Load credentials
load_dotenv()


def round_price_to_step(price: float, price_step: float) -> float:
    """Round price to nearest step"""
    if price_step <= 0:
        return price
    rounded = round(round(price / price_step) * price_step, 8)
    if price_step >= 1:
        return int(rounded)
    return rounded


def main():
    print("=" * 70)
    print("SET TP FOR LTC LONG POSITION")
    print("=" * 70)
    print()
    
    # Initialize adapter
    adapter = WeexExecutionAdapter(
        api_key=os.getenv("WEEX_API_KEY"),
        secret_key=os.getenv("WEEX_SECRET_KEY"),
        passphrase=os.getenv("WEEX_PASSPHRASE"),
        default_symbol="cmt_ltcusdt"
    )
    
    # Initialize TP/SL calculator
    tpsl_calc = TPSLCalculator(
        min_rr_ratio=1.2,
        max_rr_ratio=3.0,
        base_sl_multiplier=1.0,
        base_tp_multiplier=2.0
    )
    
    symbol = "cmt_ltcusdt"
    adapter.symbol = symbol
    
    # Check existing TP/SL orders first
    print(f"🔍 Checking existing TP/SL orders for {symbol}...")
    try:
        # Try to get plan order history
        path = "/capi/v2/order/historyPlan"
        now = int(time.time() * 1000)
        params = {
            "symbol": symbol,
            "pageSize": 50,
            "startTime": now - (7 * 24 * 60 * 60 * 1000),  # Last 7 days
            "endTime": now
        }
        plan_orders = adapter._get(path, params)
        if plan_orders and isinstance(plan_orders, list):
            active_plans = [p for p in plan_orders if p.get('status') in ['NEW', 'PENDING']]
            if active_plans:
                print(f"  📋 Found {len(active_plans)} active TP/SL orders:")
                for plan in active_plans:
                    print(f"     - {plan.get('planType', 'unknown')}: {plan.get('triggerPrice')} (Status: {plan.get('status')})")
            else:
                print(f"  ⚠️  No active TP/SL orders found")
        else:
            print(f"  ℹ️  Could not fetch plan orders (may not be available)")
    except Exception as e:
        print(f"  ⚠️  Could not check existing orders: {e}")
    
    print()
    
    # Fetch positions
    print(f"📋 Fetching positions for {symbol}...")
    try:
        pos_res = adapter.get_positions()
        positions = pos_res if isinstance(pos_res, list) else pos_res.get('data', [])
        
        # Find LTC position
        ltc_position = None
        for pos in positions:
            if pos.get('symbol') == symbol:
                size = abs(float(pos.get('size', pos.get('holdAmount', 0))))
                if size > 0:
                    ltc_position = pos
                    break
        
        if not ltc_position:
            print(f"  ❌ No active LTC position found")
            return
        
        side_str = ltc_position.get('side', '').upper()
        size = abs(float(ltc_position.get('size', ltc_position.get('holdAmount', 0))))
        entry_price = float(ltc_position.get('avgPrice', 0))
        
        if entry_price <= 0:
            entry_price = 69.1  # Use provided entry price
            print(f"  ⚠️  Using provided entry price: {entry_price}")
        else:
            print(f"  ✓ Found LTC position: {side_str} {size} @ ${entry_price}")
        
        if side_str not in ['LONG', '1']:
            print(f"  ❌ Position is not LONG, it's {side_str}")
            return
        
    except Exception as e:
        print(f"  ❌ Error fetching positions: {e}")
        return
    
    # Get current price
    try:
        ticker = adapter.get_ticker(symbol)
        current_price = float(ticker.get('last', 0))
        print(f"  📊 Current price: ${current_price:.2f}")
    except Exception as e:
        print(f"  ❌ Error getting current price: {e}")
        return
    
    # Get price step
    try:
        rules = adapter.get_symbol_rules(symbol)
        price_step = rules.get('price_step', 0.01)
        print(f"  📏 Price step: {price_step}")
    except Exception as e:
        print(f"  ⚠️  Could not get price rules: {e}, using default 0.01")
        price_step = 0.01
    
    # Calculate ATR estimate (conservative: ~2% of price for LTC)
    atr_estimate = current_price * 0.02
    print(f"  📊 Estimated ATR: ${atr_estimate:.4f} ({atr_estimate/current_price*100:.2f}% of price)")
    
    # Calculate TP using TPSLCalculator
    # Use moderate confidence and RANGE regime for conservative approach
    confidence = 0.60
    regime = 'RANGE'
    
    try:
        tpsl_result = tpsl_calc.calculate_dynamic_tpsl(
            entry_price=entry_price,
            direction='LONG',
            volatility_atr=atr_estimate,
            regime=regime,
            confidence=confidence
        )
        
        if not tpsl_result.get('valid'):
            error_msg = tpsl_result.get('error', 'Unknown error')
            print(f"  ❌ TP/SL calculation invalid: {error_msg}")
            return
        
        tp_price = tpsl_result['take_profit']
        risk_reward = tpsl_result.get('risk_reward', 0)
        
        # Round to price step
        tp_price = round_price_to_step(tp_price, price_step)
        
        # For LTC at entry 69.1, let's also calculate a conservative TP
        # Using 1.5% to 2% profit target (conservative)
        conservative_tp = entry_price * 1.015  # 1.5% profit
        moderate_tp = entry_price * 1.02   # 2.0% profit
        aggressive_tp = entry_price * 1.03  # 3.0% profit
        
        conservative_tp = round_price_to_step(conservative_tp, price_step)
        moderate_tp = round_price_to_step(moderate_tp, price_step)
        aggressive_tp = round_price_to_step(aggressive_tp, price_step)
        
        print(f"\n  📈 Entry Price: ${entry_price:.2f}")
        print(f"  📊 Current Price: ${current_price:.2f}")
        print(f"  🎯 Calculated TP (ATR-based): ${tp_price:.2f} (R:R = {risk_reward:.2f}:1)")
        print(f"\n  💡 Alternative TP levels:")
        print(f"     Conservative (1.5%): ${conservative_tp:.2f}")
        print(f"     Moderate (2.0%): ${moderate_tp:.2f}")
        print(f"     Aggressive (3.0%): ${aggressive_tp:.2f}")
        
        # Use the ATR-based TP, but ensure it's reasonable
        # If calculated TP is too close or too far, use moderate
        if tp_price <= entry_price * 1.01:  # Less than 1% profit
            print(f"  ⚠️  Calculated TP too close, using moderate TP")
            tp_price = moderate_tp
        elif tp_price > entry_price * 1.05:  # More than 5% profit
            print(f"  ⚠️  Calculated TP too far, using moderate TP")
            tp_price = moderate_tp
        
        print(f"\n  ✅ Final TP to set: ${tp_price:.2f}")
        print(f"     Profit target: {(tp_price/entry_price - 1)*100:.2f}%")
        
    except Exception as e:
        print(f"  ❌ Error calculating TP: {e}")
        # Fallback to moderate TP
        tp_price = round_price_to_step(entry_price * 1.02, price_step)
        print(f"  ⚠️  Using fallback TP: ${tp_price:.2f}")
    
    # Place TP order
    print(f"\n  🟢 Placing TP order @ ${tp_price:.2f} for size {size}...")
    try:
        tp_result = adapter.place_tp_sl_order(
            plan_type='profit_plan',
            trigger_price=tp_price,
            size=size,
            position_side='long',
            execute_price=0,  # Market order
            margin_mode=1  # Cross margin
        )
        
        # Handle response
        if isinstance(tp_result, list) and len(tp_result) > 0:
            tp_result = tp_result[0]
        
        print(f"  📋 Response: {json.dumps(tp_result, indent=2)}")
        
        if tp_result.get('success') or tp_result.get('orderId', 0) > 0:
            order_id = tp_result.get('orderId')
            print(f"\n  ✅ TP order placed successfully!")
            print(f"     Order ID: {order_id}")
            print(f"     Trigger Price: ${tp_price:.2f}")
            print(f"     Size: {size}")
        else:
            print(f"\n  ❌ TP order failed")
            print(f"     Response: {json.dumps(tp_result)}")
            return
        
    except Exception as e:
        print(f"  ❌ Error placing TP order: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print("\n" + "=" * 70)
    print("✅ TP SET SUCCESSFULLY")
    print("=" * 70)
    print()


if __name__ == "__main__":
    main()
