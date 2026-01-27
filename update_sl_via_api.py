#!/usr/bin/env python3
"""
Update Stop-Loss orders for active positions via WEEX API.
Uses the new wider SL parameters (3.0% vs old 0.33-0.45%).
"""

import os
import sys
import time
import json
import base64
import hmac
import hashlib
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/root/sentinel-alpha/.env')

API_KEY = os.getenv('WEEX_API_KEY')
SECRET_KEY = os.getenv('WEEX_SECRET_KEY')
PASSPHRASE = os.getenv('WEEX_PASSPHRASE')
BASE_URL = 'https://api-contract.weex.com'

def sign_request(timestamp, method, path, query='', body=''):
    """Generate signature for WEEX API request - using base64 like weex_adapter.py"""
    message = timestamp + method.upper() + path + query + body
    signature = hmac.new(
        SECRET_KEY.encode(),
        message.encode(),
        hashlib.sha256
    ).digest()
    return base64.b64encode(signature).decode()

def get_headers(signature, timestamp):
    """Generate request headers"""
    return {
        'ACCESS-KEY': API_KEY,
        'ACCESS-SIGN': signature,
        'ACCESS-TIMESTAMP': timestamp,
        'ACCESS-PASSPHRASE': PASSPHRASE,
        'Content-Type': 'application/json',
        'locale': 'en-US'
    }

def get_plan_orders(symbol=None):
    """Get all plan orders (TP/SL orders) - using the currentPlan endpoint"""
    timestamp = str(int(time.time() * 1000))
    path = '/capi/v2/order/currentPlan'
    query = ''
    
    if symbol:
        query = f'?symbol={symbol}'
    
    signature = sign_request(timestamp, 'GET', path, query, '')
    headers = get_headers(signature, timestamp)
    
    response = requests.get(f"{BASE_URL}{path}{query}", headers=headers)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error getting plan orders: {response.status_code} - {response.text}")
        return None

def modify_tpsl_order(order_id, new_trigger_price, execute_price='0', trigger_price_type=1):
    """Modify a TP/SL plan order's trigger price"""
    timestamp = str(int(time.time() * 1000))
    path = '/capi/v2/order/modifyTpSlOrder'
    
    body_data = {
        'orderId': int(order_id),
        'triggerPrice': str(new_trigger_price),
        'executePrice': str(execute_price),
        'triggerPriceType': trigger_price_type
    }
    
    body = json.dumps(body_data)
    signature = sign_request(timestamp, 'POST', path, '', body)
    headers = get_headers(signature, timestamp)
    
    response = requests.post(f"{BASE_URL}{path}", headers=headers, data=body)
    
    return response.json()

def main():
    print("\n" + "="*80)
    print("UPDATING STOP-LOSS ORDERS VIA WEEX API")
    print("="*80)
    
    # New stop-loss levels calculated with updated parameters
    new_sl_levels = {
        'cmt_dogeusdt': {
            'short': 0.1278,  # was ~0.1245
            'long': None
        },
        'cmt_solusdt': {
            'short': 130.9645,  # was ~127.57
            'long': 123.1706    # was ~126.41
        },
        'cmt_xrpusdt': {
            'short': None,
            'long': 1.8620      # was ~1.911
        }
    }
    
    symbols = ['cmt_dogeusdt', 'cmt_solusdt', 'cmt_xrpusdt']
    
    print("\nStep 1: Fetching TP/SL plan orders...")
    print("-"*80)
    
    all_orders = []
    all_orders = []
    for symbol in symbols:
        print(f"Checking {symbol}...")
        resp = get_plan_orders(symbol)
        
        # Handle different response structures
        if isinstance(resp, list):
            orders = resp
        elif isinstance(resp, dict):
            if resp.get('code') == '00000':
                orders = resp.get('data', [])
            elif 'data' in resp:
                orders = resp.get('data', [])
            else:
                orders = []
                print(f"  Unexpected response format: {str(resp)[:100]}")
        else:
            orders = []
            
        if orders:
            print(f"  Found {len(orders)} orders")
            all_orders.extend(orders)
        else:
            print("  No orders found")
            
        time.sleep(0.5)  # Rate limiting
    
    print(f"Found {len(all_orders)} total plan orders")
    
    # Filter for stop-loss orders based on CLOSE type and price logic
    sl_orders = []
    print(f"\nFiltering {len(all_orders)} total plan orders...")
    
    # Define entry prices to help distinguish SL vs TP
    entry_prices = {
        'cmt_dogeusdt': {'short': 0.12407},
        'cmt_solusdt': {'short': 127.15, 'long': 126.98},
        'cmt_xrpusdt': {'long': 1.9196}
    }
    
    for order in all_orders:
        o_type = str(order.get('type', '')).upper()
        symbol = order.get('symbol')
        trigger_price = float(order.get('triggerPrice', 0))
        
        # Determine side from order type (CLOSE_SHORT -> belongs to SHORT pos)
        side = None
        if 'CLOSE_SHORT' in o_type:
            side = 'short'
        elif 'CLOSE_LONG' in o_type:
            side = 'long'
            
        if side and symbol in entry_prices and side in entry_prices[symbol]:
            entry = entry_prices[symbol][side]
            
            # Logic to determine if SL or TP
            is_sl = False
            if side == 'short':
                # For SHORT, SL is ABOVE entry
                if trigger_price > entry:
                    is_sl = True
            else: # long
                # For LONG, SL is BELOW entry
                if trigger_price < entry:
                    is_sl = True
            
            if is_sl:
                sl_orders.append(order)
                print(f"  Found SL order: {symbol} {side.upper()} @ {trigger_price} (Entry: {entry}) | ID: {order.get('order_id')}")
            
    print(f"Found {len(sl_orders)} stop-loss related orders")
    
    print("\nStep 2: Identifiying orders to modify...")
    print("-"*80)
    
    modifications = []
    
    # Define price precision for symbols (based on checking check_symbol_rules.py output)
    # Default to 4 decimals, but override for specific symbols
    price_decimals = {
        'cmt_dogeusdt': 5, 
        'cmt_xrpusdt': 4,
        'cmt_solusdt': 2, # SOL usually 2 decimals
        'cmt_btcusdt': 1,
        'cmt_ethusdt': 2
    }
    
    for order in sl_orders:
        symbol = order.get('symbol')
        order_id = order.get('orderId') 
        if not order_id: order_id = order.get('order_id')
        
        current_sl = float(order.get('triggerPrice', 0))
        
        # Determine side again
        o_type = str(order.get('type', '')).upper()
        side = 'short' if 'CLOSE_SHORT' in o_type else 'long'
        
        if symbol in new_sl_levels and side:
            raw_new_sl = new_sl_levels[symbol].get(side)
            
            if raw_new_sl:
                # Round to correct precision
                decimals = price_decimals.get(symbol, 4)
                new_sl = round(raw_new_sl, decimals)
                
                # Check if update is needed (compare with current)
                if abs(current_sl - new_sl) > (10 ** -decimals):
                    print(f"\n{symbol} {side.upper()}")
                    print(f"  Order ID: {order_id}")
                    print(f"  Current SL: {current_sl}")
                    print(f"  New SL: {new_sl} (Rounded from {raw_new_sl})")
                    
                    modifications.append({
                        'order_id': order_id,
                        'symbol': symbol,
                        'side': side,
                        'old_sl': current_sl,
                        'new_sl': new_sl
                    })
                else:
                    print(f"\n{symbol} {side.upper()} already at target SL {new_sl}")
                    
    print(f"\nStep 3: Modifying {len(modifications)} stop-loss orders...")
    print("-"*80)
    
    for mod in modifications:
        print(f"\nModifying {mod['symbol']} {mod['side'].upper()} SL...")
        print(f"  Order ID: {mod['order_id']}")
        print(f"  Old SL: {mod['old_sl']} → New SL: {mod['new_sl']}")
        
        try:
            result = modify_tpsl_order(
                order_id=mod['order_id'],
                new_trigger_price=mod['new_sl'],
                execute_price='0',  # Market order execution
                trigger_price_type=1  # Last price trigger
            )
            
            if result.get('code') == '00000':
                print(f"  ✅ Successfully updated!")
            else:
                print(f"  ❌ Failed: {result.get('msg', 'Unknown error')}")
                print(f"  Response: {json.dumps(result, indent=2)}")
        
        except Exception as e:
            print(f"  ❌ Error: {str(e)}")
        
        time.sleep(0.5)  # Rate limiting
    
    print("\n" + "="*80)
    print("MODIFICATION COMPLETE")
    print("="*80)
    print("\nPlease verify the updates in your WEEX dashboard/positions")
    print("\n")

if __name__ == "__main__":
    if not all([API_KEY, SECRET_KEY, PASSPHRASE]):
        print("❌ Error: WEEX API credentials not found in .env file")
        sys.exit(1)
    
    main()
