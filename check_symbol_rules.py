#!/usr/bin/env python3
import time
import requests
import json

BASE_URL = "https://api-contract.weex.com"

def get_contract_info(symbol):
    path = "/capi/v2/market/contracts"
    params = {"symbol": symbol} if symbol else {}
    resp = requests.get(BASE_URL + path, params=params)
    return resp.json()

def main():
    print("Fetching contract info for cmt_solusdt and others...")
    
    symbols = ['cmt_solusdt', 'cmt_dogeusdt', 'cmt_xrpusdt']
    
    for sym in symbols:
        info = get_contract_info(sym)
        # Handle list response directly or list inside 'data'
        if isinstance(info, list):
            data = info
        else:
            data = info.get('data', [])
            
        if isinstance(data, list) and len(data) > 0:
            contract = data[0]
            print(f"\nSymbol: {contract.get('symbol')}")
            print(f"  Price Step (tick_size): {contract.get('tick_size')}")
            print(f"  Size Step (size_increment): {contract.get('size_increment')}")
            print(f"  Min Size: {contract.get('minOrderSize')}")
        else:
            print(f"Could not get info for {sym}")

if __name__ == "__main__":
    main()
