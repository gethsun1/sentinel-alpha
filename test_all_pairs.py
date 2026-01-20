#!/usr/bin/env python3
"""
Test WEEX API for all 8 pairs
Identifies which pairs work and which don't
"""

import os
from dotenv import load_dotenv
from execution.weex_adapter import WeexExecutionAdapter

load_dotenv()

PAIRS = [
    'cmt_btcusdt',
    'cmt_ethusdt',
    'cmt_solusdt',
    'cmt_dogeusdt',
    'cmt_xrpusdt',
    'cmt_adausdt',
    'cmt_bnbusdt',
    'cmt_ltcusdt'
]

print("="*70)
print("TESTING ALL 8 WEEX PAIRS")
print("="*70)
print()

working_pairs = []
failed_pairs = []

for pair in PAIRS:
    print(f"Testing {pair}...")
    try:
        adapter = WeexExecutionAdapter(
            api_key=os.getenv('WEEX_API_KEY'),
            secret_key=os.getenv('WEEX_SECRET_KEY'),
            passphrase=os.getenv('WEEX_PASSPHRASE'),
            default_symbol=pair,  # FIXED: Use default_symbol not symbol
            dry_run=False
        )
        
        # Try to get ticker
        ticker = adapter.get_ticker()
        price = ticker['last']
        
        print(f"  ✓ {pair}: ${price}")
        working_pairs.append(pair)
        
    except Exception as e:
        print(f"  ✗ {pair}: {e}")
        failed_pairs.append((pair, str(e)))

print()
print("="*70)
print("SUMMARY")
print("="*70)
print(f"\nWorking pairs ({len(working_pairs)}):")
for pair in working_pairs:
    print(f"  ✓ {pair}")

print(f"\nFailed pairs ({len(failed_pairs)}):")
for pair, error in failed_pairs:
    print(f"  ✗ {pair}: {error}")

print()
print("="*70)

if len(working_pairs) >= 4:
    print(f"\n✅ {len(working_pairs)} pairs working - BOT CAN RUN!")
    print("\nRecommendation: Use only working pairs in bot")
else:
    print(f"\n⚠️  Only {len(working_pairs)} pairs working - need investigation")

