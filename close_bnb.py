#!/usr/bin/env python3
import os
import sys

# Add path
sys.path.insert(0, '/root/sentinel-alpha')

from execution.weex_adapter import WeexExecutionAdapter

def load_env():
    env_path = '/root/sentinel-alpha/.env'
    env = {}
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env[key] = value.strip('"').strip("'")
    return env

def main():
    env = load_env()
    api_key = env.get("WEEX_API_KEY")
    secret = env.get("WEEX_SECRET_KEY")
    passphrase = env.get("WEEX_PASSPHRASE")
    
    if not all([api_key, secret, passphrase]):
        print("❌ Missing API credentials")
        return

    symbol = "cmt_bnbusdt"
    adapter = WeexExecutionAdapter(api_key, secret, passphrase, symbol)
    
    print(f"📡 Closing all positions for {symbol}...")
    result = adapter.close_all_positions(symbol)
    print(f"✅ Result: {result}")

if __name__ == "__main__":
    main()
