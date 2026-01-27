#!/usr/bin/env python3
"""
Emergency Position Reset - Simplified (no dependencies)
"""

import os
import sys
sys.path.insert(0, '/root/sentinel-alpha')

from execution.weex_adapter import WeexExecutionAdapter

def reset_positions():
    symbols = ["cmt_adausdt", "cmt_xrpusdt", "cmt_bnbusdt"]  # Only symbols with active positions
    
    print("="*80)
    print("EMERGENCY POSITION RESET")
    print("="*80)
    
    # Load credentials from environment
    api_key = os.environ.get("WEEX_API_KEY")
    secret = os.environ.get("WEEX_SECRET_KEY")
    passphrase = os.environ.get("WEEX_PASSPHRASE")
    
    if not all([api_key, secret, passphrase]):
        print("ERROR: Missing API credentials in environment")
        return
    
    for symbol in symbols:
        print(f"\nClosing {symbol}...")
        adapter = WeexExecutionAdapter(
            api_key=api_key,
            secret_key=secret,
            passphrase=passphrase,
            default_symbol=symbol
        )
        
        try:
            result = adapter.close_all_positions(symbol)
            print(f"  ✓ Result: {result}")
        except Exception as e:
            print(f"  ⚠️  Error: {e}")
    
    print("\n" + "="*80)
    print("RESET COMPLETE - Restarting bot to sync clean state...")
    print("="*80)

if __name__ == "__main__":
    reset_positions()
