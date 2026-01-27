#!/usr/bin/env python3
"""
Adjust Stop-Loss levels for active positions to match new wider parameters.
Run this script to update SL on existing positions from old tight levels (0.3-0.5%)
to new wider levels (1.8-3.0%).
"""

import os, sys
sys.path.insert(0, '/root/sentinel-alpha')

from strategy.tpsl_calculator import TPSLCalculator
from execution.weex_adapter import WeexExecutionAdapter

def main():
    print("\n" + "="*80)
    print("STOP-LOSS ADJUSTMENT FOR ACTIVE POSITIONS")
    print("="*80)
    
    # Known active positions from user
    positions = [
        {'symbol': 'cmt_dogeusdt', 'side': 'short', 'entry': 0.12407},
        {'symbol': 'cmt_solusdt', 'side': 'short', 'entry': 127.15},
        {'symbol': 'cmt_xrpusdt', 'side': 'long', 'entry': 1.9196},
        {'symbol': 'cmt_solusdt', 'side': 'long', 'entry':  126.98},
    ]
    
    calc = TPSLCalculator()
    adapter = WeexExecutionAdapter(dry_run=False)
    
    print("\nCalculating new stop-loss levels with updated parameters...")
    print("-"*80)
    
    for pos in positions:
        symbol = pos['symbol']
        side = pos['side']
        entry = pos['entry']
        
        # Calculate ATR (minimum 1.2% of price with new parameters)
        atr = entry * 0.012
        
        # Determine regime
        regime = 'TREND_UP' if side == 'long' else 'TREND_DOWN'
        signal = 'LONG' if side == 'long' else 'SHORT'
        
        # Calculate new SL/TP
        new_tp, new_sl, reasoning, rr = calc.calculate_tp_sl(
            entry_price=entry,
            signal=signal,
            confidence=0.66,
            regime=regime,
            volatility_atr=atr
        )
        
        # Calculate distance
        if signal == 'LONG':
            sl_dist_pct = abs((entry - new_sl) / entry) * 100
        else:
            sl_dist_pct = abs((new_sl - entry) / entry) * 100
        
        print(f"\n{symbol} {side.upper()}:")
        print(f"  Entry: {entry:.4f}")
        print(f"  NEW SL: {new_sl:.4f} ({sl_dist_pct:.2f}% away)")
        print(f"  NEW TP: {new_tp:.4f}")
        
        # Update position on exchange
        print(f"  Updating position...")
        try:
            result = adapter.modify_plan_order(
                symbol=symbol,
                order_type='stop_loss',
                new_price=new_sl
            )
            if result:
                print(f"  ✅ Stop-loss updated successfully!")
            else:
                print(f"  ⚠️  Failed to update - may need manual adjustment")
        except Exception as e:
            print(f"  ❌ Error: {e}")
            print(f"  📝 Manual adjustment needed: Set SL to {new_sl:.4f}")
    
    print("\n" + "="*80)
    print("Adjustment Complete!")
    print("="*80 + "\n")

if __name__ == "__main__":
    main()
