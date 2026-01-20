from execution.ai_log_adapter import AILogAdapter
import os
import json
import time

# 1. Setup Adapter
adapter = AILogAdapter(
    api_key=os.getenv("WEEX_API_KEY"),
    secret_key=os.getenv("WEEX_SECRET_KEY"),
    passphrase=os.getenv("WEEX_PASSPHRASE"),
    log_file="logs/test_ai_log.jsonl"
)

# 2. Simulate Payload (Dictionary Format) - Same as in live_trading_bot.py
payload = {
    "stage": "Signal Generation",
    "model": "LLaMA-2-7B",
    "order_id": None, # Optional, must be Long if provided. Using None for generic test.
    "input_data": {
        "symbol": "cmt_btcusdt",
        "price": 95000.0,
        "regime": "TRENDING",
        "parameters": {"atr": 100.0, "confidence": 0.88}
    },
    "output_data": {
        "signal": "LONG",
        "confidence": 0.88,
        "tpsl": {"tp": 96000.0, "sl": 94000.0}
    },
    "explanation": "Test submission to verify compliance with WEEX requirements."
}

print("--- SUBMITTING TEST LOG ---")
response = adapter.submit_log(
    stage=payload['stage'],
    model=payload['model'],
    input_data=payload['input_data'],
    output_data=payload['output_data'],
    explanation=payload['explanation'],
    order_id=payload['order_id']
)

print(f"Response: {json.dumps(response, indent=2)}")

# 3. Verify File Write
if os.path.exists("logs/test_ai_log.jsonl"):
    print("\n✅ Log file written successfully:")
    with open("logs/test_ai_log.jsonl", 'r') as f:
        print(f.read())
else:
    print("\n❌ Log file NOT created!")
