
import os
import sys
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from execution.weex_adapter import WeexExecutionAdapter

def main():
    load_dotenv()
    adapter = WeexExecutionAdapter(
        api_key=os.getenv("WEEX_API_KEY"),
        secret_key=os.getenv("WEEX_SECRET_KEY"),
        passphrase=os.getenv("WEEX_PASSPHRASE"),
        default_symbol="cmt_btcusdt"
    )

    pairs = [
        "cmt_btcusdt", "cmt_ethusdt", "cmt_solusdt", "cmt_dogeusdt", 
        "cmt_xrpusdt", "cmt_adausdt", "cmt_bnbusdt", "cmt_ltcusdt"
    ]

    print("🚫 STARTING REDUNDANT ORDER CLEANUP 🚫")
    for sym in pairs:
        print(f"Cleaning {sym}...")
        try:
            # Cancel Plan Orders (TP/SL)
            res = adapter.cancel_all_plan_orders(sym)
            print(f"  Result: {res}")
        except Exception as e:
            print(f"  Error: {e}")

    print("✅ Cleanup Complete.")

if __name__ == "__main__":
    main()
