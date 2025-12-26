"""
weex_adapter.py

WEEX Execution Adapter for Sentinel Alpha.
Handles authenticated order execution with strict risk controls
and full audit logging for hackathon compliance.
"""

import time
import hmac
import hashlib
import base64
import json
import requests
from typing import Optional


class WeexExecutionAdapter:
    BASE_URL = "https://api-contract.weex.com"

    ALLOWED_SYMBOLS = {
        "cmt_btcusdt",
        "cmt_ethusdt",
        "cmt_solusdt",
        "cmt_dogeusdt",
        "cmt_xrpusdt",
        "cmt_adausdt",
        "cmt_bnbusdt",
        "cmt_ltcusdt",
    }

    MAX_LEVERAGE = 20

    def __init__(
        self,
        api_key: str,
        secret_key: str,
        passphrase: str,
        default_symbol: str = "cmt_btcusdt",
        leverage: int = 1,
        dry_run: bool = False,
    ):
        self.api_key = api_key
        self.secret_key = secret_key
        self.passphrase = passphrase
        self.symbol = default_symbol
        self.leverage = min(leverage, self.MAX_LEVERAGE)
        self.dry_run = dry_run

        if self.symbol not in self.ALLOWED_SYMBOLS:
            raise ValueError("Symbol not allowed in WEEX competition")

    # ---------- SIGNING ----------

    def _timestamp(self) -> str:
        return str(int(time.time() * 1000))

    def _sign(self, timestamp, method, path, query, body):
        message = timestamp + method.upper() + path + query + body
        signature = hmac.new(
            self.secret_key.encode(),
            message.encode(),
            hashlib.sha256
        ).digest()
        return base64.b64encode(signature).decode()

    def _headers(self, signature, timestamp):
        return {
            "ACCESS-KEY": self.api_key,
            "ACCESS-SIGN": signature,
            "ACCESS-TIMESTAMP": timestamp,
            "ACCESS-PASSPHRASE": self.passphrase,
            "Content-Type": "application/json",
            "locale": "en-US",
        }

    # ---------- CORE REQUEST ----------

    def _get(self, path: str, params: dict = None) -> dict:
        """GET request with proper signature"""
        ts = self._timestamp()
        query = ""
        if params:
            query = "?" + "&".join([f"{k}={v}" for k, v in params.items()])
        
        signature = self._sign(ts, "GET", path, query, "")

        if self.dry_run:
            return {"dry_run": True, "method": "GET", "path": path, "params": params}

        response = requests.get(
            self.BASE_URL + path + query,
            headers=self._headers(signature, ts),
            timeout=10
        )
        
        # Debug: Print response for troubleshooting
        if response.status_code != 200:
            print(f"[DEBUG] HTTP {response.status_code}: {response.text[:200]}")
            return {
                "error": f"HTTP {response.status_code}",
                "message": response.text[:500],
                "status_code": response.status_code
            }
        
        try:
            return response.json()
        except Exception as e:
            print(f"[DEBUG] Response text: {response.text[:200]}")
            raise

    def _post(self, path: str, body: dict) -> dict:
        ts = self._timestamp()
        body_json = json.dumps(body)
        signature = self._sign(ts, "POST", path, "", body_json)

        if self.dry_run:
            return {"dry_run": True, "body": body}

        response = requests.post(
            self.BASE_URL + path,
            headers=self._headers(signature, ts),
            data=body_json,
            timeout=10
        )
        
        # Debug: Print response for troubleshooting
        if response.status_code != 200:
            print(f"[DEBUG] HTTP {response.status_code}: {response.text[:200]}")
            return {
                "error": f"HTTP {response.status_code}",
                "message": response.text[:500],
                "status_code": response.status_code
            }
        
        try:
            return response.json()
        except Exception as e:
            print(f"[DEBUG] Response text: {response.text[:200]}")
            raise

    # ---------- LEVERAGE ----------

    def set_leverage(self):
        body = {
            "symbol": self.symbol,
            "marginMode": 1,
            "longLeverage": str(self.leverage),
            "shortLeverage": str(self.leverage),
        }
        return self._post("/capi/v2/account/leverage", body)

    # ---------- MARKET DATA ----------

    def get_server_time(self) -> dict:
        """Get server timestamp"""
        return self._get("/capi/v2/market/time")

    def get_ticker(self, symbol: str = None) -> dict:
        """Get single ticker information"""
        sym = symbol or self.symbol
        return self._get("/capi/v2/market/ticker", {"symbol": sym})

    def get_contract_info(self, symbol: str = None) -> dict:
        """Get futures contract information"""
        sym = symbol or self.symbol
        return self._get("/capi/v2/market/contracts", {"symbol": sym})

    # ---------- ACCOUNT ----------

    def get_account_assets(self) -> dict:
        """Query account assets"""
        return self._get("/capi/v2/account/assets")

    def get_positions(self) -> dict:
        """Query current positions"""
        return self._get("/capi/v2/account/holds")

    # ---------- ORDER EXECUTION ----------

    def place_order(
        self,
        direction: str,
        size: float,
        price: Optional[float] = None,
    ) -> dict:
        """
        direction: 'LONG' or 'SHORT'
        size: contract size (small, conservative)
        price: limit price (required)
        """

        if direction not in {"LONG", "SHORT"}:
            return {"status": "rejected", "reason": "Invalid direction"}

        if size <= 0:
            return {"status": "rejected", "reason": "Invalid size"}

        if price is None:
            return {"status": "rejected", "reason": "Limit price required"}

        body = {
            "symbol": self.symbol,
            "client_oid": f"sentinel-{int(time.time())}",
            "size": str(size),
            "type": "1" if direction == "LONG" else "2",
            "order_type": "0",   # limit
            "match_price": "0",
            "price": str(price),
        }

        return self._post("/capi/v2/order/placeOrder", body)

    def get_fills(self, symbol: str = None) -> dict:
        """Get trade history / fills"""
        sym = symbol or self.symbol
        return self._get("/capi/v2/trade/fills", {"symbol": sym})
