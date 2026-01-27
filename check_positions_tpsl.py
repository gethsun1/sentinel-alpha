#!/usr/bin/env python3
"""
Check current positions and their TP/SL status
"""
import os
import sys
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from execution.weex_adapter import WeexExecutionAdapter

def main():
    print("=" * 70)
    print("CHECK CURRENT POSITIONS & TP/SL STATUS")
    print("=" * 70)
    print()
    
    # Check environment variables
    api_key = os.getenv("WEEX_API_KEY")
    secret_key = os.getenv("WEEX_SECRET_KEY")
    passphrase = os.getenv("WEEX_PASSPHRASE")
    
    if not api_key or not secret_key or not passphrase:
        print("❌ Missing required environment variables:")
        if not api_key:
            print("   - WEEX_API_KEY")
        if not secret_key:
            print("   - WEEX_SECRET_KEY")
        if not passphrase:
            print("   - WEEX_PASSPHRASE")
        print("\nPlease set these in your .env file or environment.")
        return
    
    # Initialize adapter
    try:
        adapter = WeexExecutionAdapter(
            api_key=api_key,
            secret_key=secret_key,
            passphrase=passphrase,
            default_symbol="cmt_btcusdt"
        )
    except Exception as e:
        print(f"❌ Error initializing adapter: {e}")
        return
    
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
        
        print(f"  ✓ Found {len(active_positions)} active position(s)\n")
        
    except Exception as e:
        print(f"  ❌ Error fetching positions: {e}")
        return
    
    # Check TP/SL orders for each position
    print("🔍 Checking TP/SL orders...")
    print()
    
    for i, pos in enumerate(active_positions, 1):
        symbol = pos.get('symbol', '')
        side = pos.get('side', '').upper()
        size = abs(float(pos.get('size', pos.get('holdAmount', 0))))
        entry_price = float(pos.get('avgPrice', 0)) if pos.get('avgPrice') else 0.0
        
        print(f"[{i}] {symbol} - {side} {size} @ ${entry_price:.4f}")
        print("-" * 70)
        
        adapter.symbol = symbol
        
        # Try to get plan orders (TP/SL)
        try:
            path = "/capi/v2/order/historyPlan"
            import time
            now = int(time.time() * 1000)
            params = {
                "symbol": symbol,
                "pageSize": 50,
                "startTime": now - (7 * 24 * 60 * 60 * 1000),  # Last 7 days
                "endTime": now
            }
            plan_orders = adapter._get(path, params)
            
            if plan_orders:
                # Handle list or dict response
                orders_list = plan_orders if isinstance(plan_orders, list) else plan_orders.get('data', [])
                
                # Filter active orders
                active_plans = [
                    p for p in orders_list 
                    if p.get('status') in ['NEW', 'PENDING', 'ACTIVE', 'TRIGGERED']
                ]
                
                if active_plans:
                    print(f"  📋 Found {len(active_plans)} active TP/SL order(s):")
                    for plan in active_plans:
                        plan_type = plan.get('planType', 'unknown')
                        trigger_price = plan.get('triggerPrice', 0)
                        plan_size = plan.get('size', 0)
                        status = plan.get('status', 'unknown')
                        order_id = plan.get('orderId', plan.get('id', 'N/A'))
                        
                        tp_sl_label = "TP" if plan_type == 'profit_plan' else "SL"
                        print(f"     • {tp_sl_label}: ${float(trigger_price):.4f} (Size: {plan_size}, Status: {status}, ID: {order_id})")
                else:
                    print(f"  ⚠️  No active TP/SL orders found for {symbol}")
                    print(f"     → Position has NO TP/SL protection!")
            else:
                print(f"  ⚠️  Could not fetch plan orders (API may not support this endpoint)")
        except Exception as e:
            print(f"  ⚠️  Error checking TP/SL orders: {e}")
        
        # Get current price
        try:
            ticker = adapter.get_ticker(symbol)
            current_price = float(ticker.get('last', 0))
            print(f"  💰 Current Price: ${current_price:.4f}")
            
            if entry_price > 0:
                if side == 'LONG':
                    pnl_pct = ((current_price - entry_price) / entry_price) * 100
                else:
                    pnl_pct = ((entry_price - current_price) / entry_price) * 100
                print(f"  📊 P&L: {pnl_pct:+.2f}%")
        except Exception as e:
            print(f"  ⚠️  Could not get current price: {e}")
        
        print()
    
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total active positions: {len(active_positions)}")
    print()
    print("⚠️  If positions show no TP orders, they need TP protection!")

if __name__ == "__main__":
    main()
