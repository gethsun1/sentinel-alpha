from execution.weex_adapter import WeexExecutionAdapter
import os
import json

adapter = WeexExecutionAdapter(
    api_key=os.getenv("WEEX_API_KEY"),
    secret_key=os.getenv("WEEX_SECRET_KEY"),
    passphrase=os.getenv("WEEX_PASSPHRASE"),
    default_symbol="cmt_btcusdt"
)

symbols = ["cmt_xrpusdt", "cmt_btcusdt", "cmt_ethusdt"]
print("--- FETCHING CONTRACT RULES ---")

for s in symbols:
    info = adapter.get_contract_info(s)
    data = info if isinstance(info, list) else info.get('data', [])
    
    found = False
    for c in data:
        if c.get('symbol') == s:
            print(f"\n--- {s} ---")
            print(f"minOrderSize: {c.get('minOrderSize')}")
            print(f"size_increment: {c.get('size_increment')}")
            print(f"price_increment: {c.get('price_increment')}")
            print(f"tick_size: {c.get('tick_size')}")
            found = True
            break
            
    if not found:
        print(f"\n--- {s} ---")
        print("❌ NOT FOUND in API response")
