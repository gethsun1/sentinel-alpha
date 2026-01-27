#!/usr/bin/env python3
"""
Manual Hedge Consolidation Script
Closes opposing LONG+SHORT positions on the same symbol when net exposure < 5%.
This prevents double funding fees for near-zero net positions.
"""
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from execution.weex_adapter import WeexExecutionAdapter

# Load .env manually if needed
def load_env():
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    # Strip quotes from value
                    value = value.strip().strip('"').strip("'")
                    os.environ[key.strip()] = value

load_env()

def main():
    print("=" * 80)
    print("MANUAL HEDGE CONSOLIDATION")
    print("=" * 80)
    
    # Get API credentials
    api_key = os.getenv('WEEX_API_KEY')
    secret_key = os.getenv('WEEX_SECRET_KEY')
    passphrase = os.getenv('WEEX_PASSPHRASE')
    
    if not all([api_key, secret_key, passphrase]):
        print("❌ Missing API credentials in .env file")
        sys.exit(1)
    
    # Initialize adapter
    adapter = WeexExecutionAdapter(api_key, secret_key, passphrase)
    
    # Define symbols to check
    symbols = [
        "cmt_btcusdt", "cmt_ethusdt", "cmt_solusdt", "cmt_dogeusdt",
        "cmt_xrpusdt", "cmt_adausdt", "cmt_bnbusdt", "cmt_ltcusdt"
    ]
    
    # Fetch all positions once
    print("\n📡 Fetching all positions from WEEX...")
    all_positions_response = adapter.get_positions()
    
    if not all_positions_response or 'data' not in all_positions_response:
        print(f"❌ Failed to fetch positions: {all_positions_response}")
        return
    
    all_positions = all_positions_response['data']
    print(f"   ✓ Fetched {len(all_positions)} total positions")
    
    consolidation_count = 0
    
    for symbol in symbols:
        try:
            print(f"\n🔍 Checking {symbol}...")
            
            # Filter positions for this symbol
            positions = [p for p in all_positions if p.get('symbol') == symbol]
            
            if not positions or len(positions) == 0:
                print(f"   ✓ No positions on {symbol}")
                continue
            
            # Separate LONG and SHORT
            long_positions = [p for p in positions if p.get('side') == 'LONG']
            short_positions = [p for p in positions if p.get('side') == 'SHORT']
            
            # Check if hedged
            if not (long_positions and short_positions):
                print(f"   ✓ {symbol} not hedged (only {len(long_positions)} LONGs, {len(short_positions)} SHORTs)")
                continue
            
            # Calculate net exposure
            long_size = sum(float(p.get('size', 0)) for p in long_positions)
            short_size = sum(float(p.get('size', 0)) for p in short_positions)
            total_size = long_size + short_size
            net_size = long_size - short_size
            
            if total_size == 0:
                continue
            
            net_exposure_pct = abs(net_size) / total_size
            
            print(f"   📊 {symbol}:")
            print(f"      LONG: {long_size}")
            print(f"      SHORT: {short_size}")
            print(f"      Net: {net_size} ({net_exposure_pct*100:.2f}% of total)")
            
            # Consolidate if net exposure < 5%
            if net_exposure_pct < 0.05:
                print(f"   ⚠️  Net exposure < 5% - CONSOLIDATING...")
                
                # Close all positions on this symbol
                result = adapter.close_all_positions(symbol)
                
                if result and result.get('success'):
                    print(f"   ✅ Successfully closed all positions on {symbol}")
                    consolidation_count += 1
                else:
                    print(f"   ❌ Failed to close positions: {result}")
            else:
                print(f"   ✓ Net exposure > 5% - keeping positions")
        
        except Exception as e:
            print(f"   ❌ Error processing {symbol}: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 80)
    print(f"CONSOLIDATION COMPLETE: {consolidation_count} symbols consolidated")
    print("=" * 80)

if __name__ == "__main__":
    main()
