#!/usr/bin/env python3
import os
import sys
import time
import json
import base64
import hmac
import hashlib
import requests
from dotenv import load_dotenv

load_dotenv('/root/sentinel-alpha/.env')

API_KEY = os.getenv('WEEX_API_KEY')
SECRET_KEY = os.getenv('WEEX_SECRET_KEY')
PASSPHRASE = os.getenv('WEEX_PASSPHRASE')
BASE_URL = 'https://api-contract.weex.com'

def sign_request(timestamp, method, path, query='', body=''):
    message = timestamp + method.upper() + path + query + body
    signature = hmac.new(SECRET_KEY.encode(), message.encode(), hashlib.sha256).digest()
    return base64.b64encode(signature).decode()

def get_headers(signature, timestamp):
    return {
        'ACCESS-KEY': API_KEY, 'ACCESS-SIGN': signature, 'ACCESS-TIMESTAMP': timestamp,
        'ACCESS-PASSPHRASE': PASSPHRASE, 'Content-Type': 'application/json', 'locale': 'en-US'
    }

def place_tp(symbol, price, size):
    timestamp = str(int(time.time() * 1000))
    path = '/capi/v2/order/placeTpSlOrder'
    
    # We need to find the correct size. 
    # But first, let's just try placing it for the full position or a specific size?
    # The user says "position margin reduced", so it's a runner.
    # We don't know the exact size.
    # We can try to fetch the position size first.
    
    # Fetch position
    pos_path = '/capi/v2/account/position/allPosition'
    pos_sig = sign_request(timestamp, 'GET', pos_path, '?productType=USDT-FUTURES', '')
    pos_headers = get_headers(pos_sig, timestamp)
    pos_resp = requests.get(f"{BASE_URL}{pos_path}?productType=USDT-FUTURES", headers=pos_headers)
    
    pos_size = 0
    if pos_resp.status_code == 200:
        raw_data = pos_resp.json()
        print(f"DEBUG: Raw data: {json.dumps(raw_data)[:500]}...") # Print first 500 chars
        if isinstance(raw_data, list):
            data = raw_data
        else:
            data = raw_data.get('data', [])
            
        for p in data:
            # Check both side and holdSide for compatibility
            side = p.get('side') or p.get('holdSide')
            if str(side).upper() == 'SHORT' and p.get('symbol') == symbol:
                pos_size = float(p.get('size') or p.get('total', 0)) # Use size or total
                break
    
    if pos_size <= 0:
        print("Could not find open DOGE SHORT position size.")
        return

    print(f"Found DOGE SHORT size: {pos_size}")
    
    # Place TP for full remaining size
    body = {
        "symbol": symbol,
        "clientOrderId": f"manual-tp-{int(time.time())}",
        "planType": "profit_plan",
        "triggerPrice": str(price),
        "executePrice": str(price), # Limit order at trigger price
        "size": str(pos_size),
        "positionSide": "short",
        "marginMode": 1
    }
    
    body_json = json.dumps(body)
    sig = sign_request(timestamp, 'POST', path, '', body_json)
    headers = get_headers(sig, timestamp)
    
    resp = requests.post(f"{BASE_URL}{path}", headers=headers, data=body_json)
    print(f"TP Placement: {resp.text}")

if __name__ == "__main__":
    place_tp("cmt_dogeusdt", 0.1215, 0)
