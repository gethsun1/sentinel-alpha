#!/usr/bin/env python3
"""
Manual Hedge Consolidation for ETH and SOL
Closes all positions on both symbols to eliminate hedging
"""

import os
import sys
sys.path.insert(0, '/root/sentinel-alpha')

from execution.weex_adapter import WeexExecutionAdapter

def consolidate_eth_sol():
    """Close all ETH and SOL positions"""
    
    # Load credentials
    env_path = '/root/sentinel-alpha/.env'
    env = {}
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env[key] = value.strip('"')
    
    api_key = env.get("WEEX_API_KEY")
    secret = env.get("WEEX_SECRET_KEY")
    passphrase = env.get("WEEX_PASSPHRASE")
    
    symbols = ["cmt_ethusdt", "cmt_solusdt"]
    
    print("="*80)
    print("MANUAL HEDGE CONSOLIDATION - ETH & SOL")
    print("="*80)
    print()
    
    for symbol in symbols:
        print(f"Closing all positions on {symbol}...")
        adapter = WeexExecutionAdapter(
            api_key=api_key,
            secret_key=secret,
            passphrase=passphrase,
            default_symbol=symbol
        )
        
        try:
            result = adapter.close_all_positions(symbol)
            print(f"  ✓ Result: {result}")
            
            if result and isinstance(result, list):
                success_count = sum(1 for r in result if r.get('success'))
                print(f"  ✓ Successfully closed {success_count} position(s)")
        except Exception as e:
            print(f"  ⚠️  Error: {e}")
    
    print()
    print("="*80)
    print("CONSOLIDATION COMPLETE")
    print("Both ETH and SOL hedged positions should now be closed.")
    print("="*80)

if __name__ == "__main__":
    consolidate_eth_sol()
