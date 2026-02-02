from execution.weex_adapter import WeexExecutionAdapter
import os
from dotenv import load_dotenv
import json

load_dotenv()

adapter = WeexExecutionAdapter(
    api_key=os.getenv("WEEX_API_KEY"),
    secret_key=os.getenv("WEEX_SECRET_KEY"),
    passphrase=os.getenv("WEEX_PASSPHRASE"),
    dry_run=False
)

print("Fetching assets...")
try:
    assets = adapter.get_account_assets()
    print("Raw Assets Response:")
    print(json.dumps(assets, indent=2))
except Exception as e:
    print(f"Error: {e}")
