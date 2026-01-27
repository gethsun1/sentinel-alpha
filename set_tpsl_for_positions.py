#!/usr/bin/env python3
"""
Set TP/SL for all open positions

This script:
1. Fetches all open positions from WEEX
2. Calculates prudent TP/SL levels using TPSLCalculator
3. Places both TP and SL orders for each position
"""

import os
import sys
import json
import time
import pandas as pd
from typing import Dict, List, Optional
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
    # If step is >= 1, return as int
    if price_step >= 1:
        return int(rounded)
    return rounded


def estimate_atr_from_price(price: float, symbol: str) -> float:
    """
    Estimate ATR when historical data is not available.
    Uses conservative percentage-based estimates per asset class.
    """
    # Conservative ATR estimates as percentage of price
    atr_percentages = {
        'btc': 0.015,  # 1.5% for BTC
        'eth': 0.020,  # 2.0% for ETH
        'sol': 0.025,  # 2.5% for SOL
        'doge': 0.030,  # 3.0% for DOGE
        'xrp': 0.020,  # 2.0% for XRP
        'ada': 0.025,
        'bnb': 0.020,
        'ltc': 0.020,
    }
    
    # Find matching asset
    symbol_lower = symbol.lower()
    for asset, pct in atr_percentages.items():
        if asset in symbol_lower:
            return price * pct
    
    # Default: 2% of price
    return price * 0.02


def collect_price_history(adapter: WeexExecutionAdapter, symbol: str, samples: int = 20) -> pd.DataFrame:
    """
    Collect recent price history by fetching ticker multiple times.
    Returns DataFrame with 'price' column for ATR calculation.
    """
    prices = []
    for i in range(samples):
        try:
            ticker = adapter.get_ticker(symbol)
            price = float(ticker.get('last', 0))
            if price > 0:
                prices.append({
                    'timestamp': int(time.time() * 1000) - (samples - i) * 1000,
                    'price': price
                })
            time.sleep(0.1)  # Small delay between fetches
        except Exception as e:
            print(f"  ⚠️  Error fetching ticker {i+1}/{samples}: {e}")
            continue
    
    if len(prices) < 5:
        # If we don't have enough data, pad with last price
        last_price = prices[-1]['price'] if prices else 0
        while len(prices) < 15:
            prices.insert(0, {
                'timestamp': int(time.time() * 1000) - len(prices) * 1000,
                'price': last_price
            })
    
    df = pd.DataFrame(prices)
    return df


def set_tpsl_for_position(
    adapter: WeexExecutionAdapter,
    tpsl_calc: TPSLCalculator,
    position: Dict,
    use_price_history: bool = True
) -> Dict:
    """
    Set TP/SL for a single position.
    
    Returns dict with success status and details.
    """
    symbol = position.get('symbol', '')
    side_str = position.get('side', '').upper()
    size = abs(float(position.get('size', position.get('holdAmount', 0))))
    
    # Convert side to LONG/SHORT
    if side_str in ['SHORT', '2']:
        direction = 'SHORT'
        position_side = 'short'
    else:
        direction = 'LONG'
        position_side = 'long'
    
    # Get entry price (avgPrice)
    entry_price = float(position.get('avgPrice', 0))
    if entry_price <= 0:
        # Fallback: use current price
        try:
            ticker = adapter.get_ticker(symbol)
            entry_price = float(ticker.get('last', 0))
        except Exception as e:
            print(f"  ⚠️  Could not get entry price for {symbol}: {e}")
            return {'success': False, 'error': 'Could not determine entry price'}
    
    if entry_price <= 0:
        return {'success': False, 'error': 'Invalid entry price'}
    
    # Get current price
    try:
        ticker = adapter.get_ticker(symbol)
        current_price = float(ticker.get('last', 0))
    except Exception as e:
        print(f"  ⚠️  Could not get current price for {symbol}: {e}")
        return {'success': False, 'error': 'Could not get current price'}
    
    # Calculate ATR
    if use_price_history:
        print(f"  📊 Collecting price history for {symbol}...")
        try:
            price_df = collect_price_history(adapter, symbol, samples=20)
            atr = tpsl_calc.calculate_atr(price_df, period=14)
            if atr <= 0:
                atr = estimate_atr_from_price(current_price, symbol)
                print(f"  ⚠️  ATR calculation failed, using estimate: ${atr:.4f}")
            else:
                print(f"  ✓ ATR calculated: ${atr:.4f}")
        except Exception as e:
            print(f"  ⚠️  Error calculating ATR: {e}, using estimate")
            atr = estimate_atr_from_price(current_price, symbol)
    else:
        atr = estimate_atr_from_price(current_price, symbol)
        print(f"  📊 Using estimated ATR: ${atr:.4f} ({atr/current_price*100:.2f}% of price)")
    
    # Get price step for rounding
    try:
        rules = adapter.get_symbol_rules(symbol)
        price_step = rules.get('price_step', 0.1)
    except Exception as e:
        print(f"  ⚠️  Could not get price rules: {e}, using default")
        price_step = 0.1
    
    # Calculate TP/SL using TPSLCalculator
    # Use moderate confidence and default regime
    confidence = 0.60  # Moderate confidence
    regime = 'RANGE'  # Conservative default regime
    
    try:
        tpsl_result = tpsl_calc.calculate_dynamic_tpsl(
            entry_price=entry_price,
            direction=direction,
            volatility_atr=atr,
            regime=regime,
            confidence=confidence
        )
        
        if not tpsl_result.get('valid'):
            error_msg = tpsl_result.get('error', 'Unknown error')
            print(f"  ❌ TP/SL calculation invalid: {error_msg}")
            return {'success': False, 'error': error_msg}
        
        tp_price = tpsl_result['take_profit']
        sl_price = tpsl_result['stop_loss']
        risk_reward = tpsl_result.get('risk_reward', 0)
        
        # Round to price step
        tp_price = round_price_to_step(tp_price, price_step)
        sl_price = round_price_to_step(sl_price, price_step)
        
        print(f"  📈 Entry: ${entry_price:.4f}, Current: ${current_price:.4f}")
        print(f"  🎯 TP: ${tp_price:.4f}, SL: ${sl_price:.4f}, R:R = {risk_reward:.2f}:1")
        
    except Exception as e:
        print(f"  ❌ Error calculating TP/SL: {e}")
        return {'success': False, 'error': str(e)}
    
    # Set adapter symbol
    adapter.symbol = symbol
    
    results = {
        'symbol': symbol,
        'direction': direction,
        'size': size,
        'entry_price': entry_price,
        'current_price': current_price,
        'tp_price': tp_price,
        'sl_price': sl_price,
        'tp_success': False,
        'sl_success': False,
        'tp_order_id': None,
        'sl_order_id': None
    }
    
    # Place TP order
    print(f"  🟢 Placing TP order @ ${tp_price:.4f}...")
    try:
        tp_result = adapter.place_tp_sl_order(
            plan_type='profit_plan',
            trigger_price=tp_price,
            size=size,
            position_side=position_side,
            execute_price=0,  # Market order
            margin_mode=1  # Cross margin
        )
        
        # Handle response (can be list or dict)
        if isinstance(tp_result, list) and len(tp_result) > 0:
            tp_result = tp_result[0]
        
        if tp_result.get('success') or tp_result.get('orderId', 0) > 0:
            results['tp_success'] = True
            results['tp_order_id'] = tp_result.get('orderId')
            print(f"  ✓ TP order placed successfully (ID: {results['tp_order_id']})")
        else:
            print(f"  ⚠️  TP order failed: {json.dumps(tp_result)}")
            results['tp_error'] = str(tp_result)
    except Exception as e:
        print(f"  ❌ Error placing TP order: {e}")
        results['tp_error'] = str(e)
    
    # Small delay between orders
    time.sleep(0.5)
    
    # Place SL order
    print(f"  🔴 Placing SL order @ ${sl_price:.4f}...")
    try:
        sl_result = adapter.place_tp_sl_order(
            plan_type='loss_plan',
            trigger_price=sl_price,
            size=size,
            position_side=position_side,
            execute_price=0,  # Market order
            margin_mode=1  # Cross margin
        )
        
        # Handle response (can be list or dict)
        if isinstance(sl_result, list) and len(sl_result) > 0:
            sl_result = sl_result[0]
        
        if sl_result.get('success') or sl_result.get('orderId', 0) > 0:
            results['sl_success'] = True
            results['sl_order_id'] = sl_result.get('orderId')
            print(f"  ✓ SL order placed successfully (ID: {results['sl_order_id']})")
        else:
            print(f"  ⚠️  SL order failed: {json.dumps(sl_result)}")
            results['sl_error'] = str(sl_result)
    except Exception as e:
        print(f"  ❌ Error placing SL order: {e}")
        results['sl_error'] = str(e)
    
    results['success'] = results['tp_success'] and results['sl_success']
    return results


def main():
    """Main function to set TP/SL for all open positions"""
    
    print("=" * 70)
    print("SET TP/SL FOR ALL OPEN POSITIONS")
    print("=" * 70)
    print()
    
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
    print("📋 Fetching open positions...")
    try:
        pos_res = adapter.get_positions()
        positions = pos_res if isinstance(pos_res, list) else pos_res.get('data', [])
        
        if not positions:
            print("  ℹ️  No open positions found")
            return
        
        # Filter to only positions with size > 0
        active_positions = [
            p for p in positions 
            if abs(float(p.get('size', p.get('holdAmount', 0)))) > 0
        ]
        
        if not active_positions:
            print("  ℹ️  No active positions found")
            return
        
        print(f"  ✓ Found {len(active_positions)} active position(s)")
        print()
        
    except Exception as e:
        print(f"  ❌ Error fetching positions: {e}")
        return
    
    # Process each position
    all_results = []
    for i, pos in enumerate(active_positions, 1):
        symbol = pos.get('symbol', '')
        side = pos.get('side', '').upper()
        size = abs(float(pos.get('size', pos.get('holdAmount', 0))))
        
        print(f"\n[{i}/{len(active_positions)}] Processing {symbol} ({side}, size={size})")
        print("-" * 70)
        
        try:
            result = set_tpsl_for_position(adapter, tpsl_calc, pos, use_price_history=True)
            all_results.append(result)
            
            if result.get('success'):
                print(f"  ✅ Successfully set TP/SL for {symbol}")
            else:
                print(f"  ⚠️  Partial success for {symbol}")
                if result.get('tp_success') and not result.get('sl_success'):
                    print(f"     → TP set, but SL failed")
                elif result.get('sl_success') and not result.get('tp_success'):
                    print(f"     → SL set, but TP failed")
                else:
                    print(f"     → Both TP and SL failed")
        
        except Exception as e:
            print(f"  ❌ Error processing {symbol}: {e}")
            all_results.append({
                'symbol': symbol,
                'success': False,
                'error': str(e)
            })
        
        # Delay between positions
        if i < len(active_positions):
            time.sleep(1)
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    successful = sum(1 for r in all_results if r.get('success'))
    partial = sum(1 for r in all_results if r.get('tp_success') or r.get('sl_success'))
    failed = len(all_results) - successful - partial
    
    print(f"Total positions processed: {len(all_results)}")
    print(f"  ✅ Fully successful (TP + SL): {successful}")
    print(f"  ⚠️  Partially successful: {partial}")
    print(f"  ❌ Failed: {failed}")
    print()
    
    # Detailed results
    for result in all_results:
        symbol = result.get('symbol', 'unknown')
        if result.get('success'):
            print(f"  ✅ {symbol}: TP @ ${result.get('tp_price', 0):.4f}, SL @ ${result.get('sl_price', 0):.4f}")
        elif result.get('tp_success') or result.get('sl_success'):
            status = []
            if result.get('tp_success'):
                status.append(f"TP @ ${result.get('tp_price', 0):.4f}")
            if result.get('sl_success'):
                status.append(f"SL @ ${result.get('sl_price', 0):.4f}")
            print(f"  ⚠️  {symbol}: {' + '.join(status)}")
        else:
            error = result.get('error', 'Unknown error')
            print(f"  ❌ {symbol}: {error}")
    
    print()


if __name__ == "__main__":
    main()
