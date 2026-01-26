#!/usr/bin/env python3
"""
Emergency Position Reset - Reads from .env file
"""

import os
import sys
sys.path.insert(0, '/root/sentinel-alpha')

from execution.weex_adapter import WeexExecutionAdapter

def load_env():
    """Load credentials from .env file"""
    env_path = '/root/sentinel-alpha/.env'
    env = {}
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env[key] = value.strip('"')
    return env

def reset_positions():
    symbols = ["cmt_adausdt", "cmt_xrpusdt", "cmt_bnbusdt"]
    
    print("="*80)
    print("EMERGENCY POSITION RESET")
    print("="*80)
    
    # Load from .env
    env = load_env()
    api_key = env.get("WEEX_API_KEY")
    secret = env.get("WEEX_SECRET_KEY")
    passphrase = env.get("WEEX_PASSPHRASE")
    
    if not all([api_key, secret, passphrase]):
        print("ERROR: Missing credentials in .env file")
        return
    
    print(f"✓ Loaded credentials from .env")
    print(f"✓ Targeting symbols: {', '.join(symbols)}\n")
    
    for symbol in symbols:
        print(f"Closing {symbol}...")
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
    print("RESET COMPLETE")
    print("="*80)

if __name__ == "__main__":
    reset_positions()
