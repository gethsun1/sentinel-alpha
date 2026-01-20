#!/usr/bin/env python3
"""
Close All Positions Script
Closes all open positions on WEEX to free up margin
"""

import os
import sys
import time
from dotenv import load_dotenv
from execution.weex_adapter import WeexExecutionAdapter

# Load environment variables
load_dotenv()

def close_all_positions():
    """Close all open positions on WEEX"""
    
    print("="*70)
    print("CLOSE ALL POSITIONS - WEEX")
    print("="*70)
    print("\n⚠️  This will close ALL open positions at MARKET PRICE!")
    print("⚠️  This action is IRREVERSIBLE!")
    
    # Confirm
    if sys.stdin.isatty():
        response = input("\nProceed with closing all positions? (yes/no): ").strip().lower()
        if response != 'yes':
            print("Aborted by user")
            return
    else:
        print("\n[Auto-confirmed: Running as script]")
    
    # Initialize adapter
    print("\nInitializing WEEX connection...")
    adapter = WeexExecutionAdapter(
        api_key=os.getenv('WEEX_API_KEY'),
        secret_key=os.getenv('WEEX_SECRET_KEY'),
        passphrase=os.getenv('WEEX_PASSPHRASE'),
        default_symbol='cmt_btcusdt',  # Default, but will close all symbols
        dry_run=False
    )
    
    print("✓ Connected to WEEX")
    print("\nClosing all positions...")
    
    try:
        # Close all positions (no symbol specified = close ALL)
        result = adapter.close_all_positions()
        
        print("\n" + "="*70)
        print("CLOSE POSITIONS RESULT")
        print("="*70)
        
        if isinstance(result, list):
            success_count = 0
            fail_count = 0
            
            for item in result:
                position_id = item.get('positionId', 'N/A')
                success = item.get('success', False)
                order_id = item.get('successOrderId', 0)
                error = item.get('errorMessage', '')
                
                if success:
                    print(f"✅ Position {position_id} closed successfully")
                    print(f"   Order ID: {order_id}")
                    success_count += 1
                else:
                    print(f"❌ Position {position_id} FAILED to close")
                    print(f"   Error: {error}")
                    fail_count += 1
            
            print("\n" + "="*70)
            print(f"SUMMARY: {success_count} closed, {fail_count} failed")
            print("="*70)
            
            if success_count > 0:
                print("\n✅ Positions closed successfully!")
                print("✅ Margin is now available for new trades")
                print("\nYou can now restart the bot to resume trading:")
                print("  cd /root/sentinel-alpha")
                print("  ./RESTART_BOT.sh")
        
        elif isinstance(result, dict) and 'error' in result:
            print(f"❌ API Error: {result.get('message', 'Unknown error')}")
            print(f"   Status Code: {result.get('status_code', 'N/A')}")
        
        else:
            print("Unexpected response format:")
            print(result)
    
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == '__main__':
    success = close_all_positions()
    sys.exit(0 if success else 1)

