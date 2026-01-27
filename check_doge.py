#!/usr/bin/env python3
import requests

def get_ticker(symbol):
    resp = requests.get(f"https://api-contract.weex.com/capi/v2/market/ticker?symbol={symbol}")
    return resp.json().get('data', [])[0]

ticker = get_ticker("cmt_dogeusdt")
print(f"DOGE Ticker: Last={ticker['last']}, High={ticker['high_24h']}, Low={ticker['low_24h']}")
