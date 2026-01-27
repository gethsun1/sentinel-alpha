#!/usr/bin/env python3
"""
Emergency Position Reset for Sentinel Alpha
Closes all stale positions to unblock trading
"""

import os
import sys
from dotenv import load_dotenv
from execution.weex_adapter import WeexExecutionAdapter

load_dotenv()

def reset_positions():
    """Close all active positions to reset bot state"""
    
    symbols = [
        "cmt_btcusdt", "cmt_ethusdt", "cmt_solusdt", "cmt_dogeusdt",
        "cmt_xrpusdt", "cmt_adausdt", "cmt_bnbusdt", "cmt_ltcusdt"
    ]
    
    print("="*80)
    print("EMERGENCY POSITION RESET")
    print("="*80)
    print()
    
    for symbol in symbols:
        print(f"Processing {symbol}...")
        adapter = WeexExecutionAdapter(
            api_key=os.getenv("WEEX_API_KEY"),
            secret_key=os.getenv("WEEX_SECRET_KEY"),
            passphrase=os.getenv("WEEX_PASSPHRASE"),
            default_symbol=symbol
        )
        
        try:
            result = adapter.close_all_positions(symbol)
            print(f"  ✓ Result: {result}")
        except Exception as e:
            print(f"  ⚠️  Error: {e}")
    
    print()
    print("="*80)
    print("POSITION RESET COMPLETE")
    print("Recommendation: Restart bot service to sync clean state")
    print("Command: sudo systemctl restart sentinel-alpha.service")
    print("="*80)

if __name__ == "__main__":
    confirm = input("This will close ALL open positions. Continue? (yes/no): ")
    if confirm.lower() == 'yes':
        reset_positions()
    else:
        print("Cancelled.")
