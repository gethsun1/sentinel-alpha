#!/usr/bin/env python3
import os, sys, time, json, base64, hmac, hashlib, requests
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

def place_tp_sl(symbol, plan_type, trigger_price, size, side):
    """
    plan_type: 'profit_plan' or 'loss_plan'
    side: 'long' or 'short'
    """
    timestamp = str(int(time.time() * 1000))
    path = '/capi/v2/order/placeTpSlOrder'
    
    body = {
        "symbol": symbol,
        "clientOrderId": f"manual-{plan_type[:2]}-{int(time.time())}",
        "planType": plan_type,
        "triggerPrice": str(trigger_price),
        "executePrice": "0", # Market price execution
        "size": str(size),
        "positionSide": side,
        "marginMode": 1 # Cross
    }
    
    body_json = json.dumps(body)
    sig = sign_request(timestamp, 'POST', path, '', body_json)
    headers = get_headers(sig, timestamp)
    
    resp = requests.post(f"{BASE_URL}{path}", headers=headers, data=body_json)
    return resp.json()

# 1. SOL Short TP
print("\nSetting SOL Short TP...")
sol_res = place_tp_sl("cmt_solusdt", "profit_plan", 126.70, 0.5, "short")
print(f"SOL Result: {json.dumps(sol_res, indent=2)}")

# 2. LTC Short SL
# print("\nSetting LTC Short SL...")
# ltc_res = place_tp_sl("cmt_ltcusdt", "loss_plan", 69.75, 0.1, "short")
# print(f"LTC Result: {json.dumps(ltc_res, indent=2)}")
