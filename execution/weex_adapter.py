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
import uuid
from typing import Optional, Dict, Any


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
        from execution.mode import is_competition_mode, enforce_competition_mode
        
        # Enforce competition mode restrictions
        self.dry_run = enforce_competition_mode(dry_run)
        
        self.api_key = api_key
        self.secret_key = secret_key
        self.passphrase = passphrase
        self.symbol = default_symbol
        self.leverage = min(leverage, self.MAX_LEVERAGE)

        if self.symbol not in self.ALLOWED_SYMBOLS:
            raise ValueError("Symbol not allowed in WEEX competition")
        
        # Log competition mode status
        if is_competition_mode():
            print(f"🔒 COMPETITION MODE ACTIVE - Live trading enforced for {self.symbol}")


    # ---------- SIGNING ----------

    def _timestamp(self) -> str:
        return str(int(time.time() * 1000))

    def _unique_id(self, prefix: str) -> str:
        """
        Generate a collision-resistant client ID using time in nanoseconds + short uuid.
        Keeps IDs short enough for venue limits while avoiding same-second collisions.
        """
        return f"{prefix}-{time.time_ns()}-{uuid.uuid4().hex[:6]}"

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
        
    def get_symbol_rules(self, symbol: str) -> dict:
        """
        Fetch trading rules for symbol (min qty, step size, price step)
        Returns: {'min_qty': float, 'qty_step': float, 'price_step': float}
        """
        def _parse_price_step(val):
            """
            WEEX tick_size can be provided as an integer string representing decimals.
            e.g. '4' -> 0.0001, '2' -> 0.01. If already a float <1, use directly.
            """
            try:
                f = float(val)
                if f >= 1 and f.is_integer():
                    return 10 ** (int(-f))
                return f
            except Exception:
                return 0.1
        try:
            info = self.get_contract_info(symbol)
            contract = None
            
            # 1. Handle List Response (Direct or in data)
            target_list = []
            if isinstance(info, list):
                target_list = info
            elif isinstance(info, dict):
                target_list = info.get('data', [])
                
            for c in target_list:
                if c.get('symbol') == symbol:
                    contract = c
                    break

            if contract:
                # Parse WEEX specific keys
                # "size_increment": "4" -> 4 decimals -> 0.0001 step
                # "minOrderSize": "0.0001"
                try:
                    qty_scale = int(contract.get('size_increment', 0))
                except:
                    qty_scale = 0
                
                step = 1.0 / (10 ** qty_scale) if qty_scale > 0 else 1.0
                min_qty = float(contract.get('minOrderSize', 0))
                
                # Heuristic: If min_qty > step, likely the step is actually min_qty
                # (Fixes XRP: scale=0 -> step=1, but min=10 and API requires step=10)
                if min_qty > step:
                    step = min_qty

                return {
                    'min_qty': min_qty,
                    'qty_step': step,
                    'price_step': _parse_price_step(contract.get('tick_size', 0.1))
                }
        except Exception as e:
            print(f"Error fetching rules for {symbol}: {e}")
            
        # Default fallbacks
        if 'btc' in symbol: return {'min_qty': 0.001, 'qty_step': 0.001, 'price_step': 0.1}
        if 'eth' in symbol: return {'min_qty': 0.01, 'qty_step': 0.01, 'price_step': 0.01}
        return {'min_qty': 1.0, 'qty_step': 1.0, 'price_step': 0.0001}

    # ---------- ACCOUNT ----------

    def get_account_assets(self) -> dict:
        """Query account assets - returns balance, equity, PnL"""
        return self._get("/capi/v2/account/assets")

    def get_positions(self) -> dict:
        """Query current positions"""
        # Endpoint per user docs
        return self._get("/capi/v2/account/position/allPosition")

    # ---------- ORDER EXECUTION ----------

    def place_order(
        self,
        direction: str,
        size: float,
        price: Optional[float] = None,
        tpsl: Optional[Dict[str, Any]] = None,
    ) -> dict:
        """
        direction: 'LONG' or 'SHORT'
        size: contract size (small, conservative)
        price: limit price (required)
        tpsl: required TP/SL context with keys {take_profit, stop_loss, entry_price?, risk_reward?}
        """

        if direction not in {"LONG", "SHORT"}:
            return {"status": "rejected", "reason": "Invalid direction"}

        if size <= 0:
            return {"status": "rejected", "reason": "Invalid size"}

        if price is None:
            return {"status": "rejected", "reason": "Limit price required"}

        # Compliance gate: TP/SL must be provided and valid before any order hits the API
        if tpsl is None:
            return {"status": "rejected", "reason": "TP/SL payload missing (competition compliance)"}

        tp = tpsl.get("take_profit") or tpsl.get("tp")
        sl = tpsl.get("stop_loss") or tpsl.get("sl")
        entry_price = tpsl.get("entry_price")
        rr = tpsl.get("risk_reward")

        if tp is None or sl is None:
            return {"status": "rejected", "reason": "TP/SL required - None provided"}

        if tp <= 0 or sl <= 0:
            return {"status": "rejected", "reason": f"Invalid TP/SL values: tp={tp}, sl={sl}"}

        if entry_price is not None:
            if direction == "LONG" and sl >= entry_price:
                return {"status": "rejected", "reason": "LONG invalid: SL must be below entry"}
            if direction == "SHORT" and sl <= entry_price:
                return {"status": "rejected", "reason": "SHORT invalid: SL must be above entry"}

        if rr is not None and rr < 1.0:
            return {"status": "rejected", "reason": f"Risk-reward too low: {rr}"}

        body = {
            "symbol": self.symbol,
            "client_oid": self._unique_id("sentinel"),
            "size": str(size),
            "type": "1" if direction == "LONG" else "2",
            "order_type": "0",   # limit
            "match_price": "0",
            "price": str(price),
        }

        return self._post("/capi/v2/order/placeOrder", body)
    
    def close_all_positions(self, symbol: str = None) -> dict:
        """
        Close all positions (or specific symbol)
        If symbol is None, closes all positions at market price
        """
        body = {}
        if symbol:
            body['symbol'] = symbol
        
        return self._post("/capi/v2/order/closePositions", body)
    
    def place_tp_sl_order(
        self,
        plan_type: str,  # 'profit_plan' or 'loss_plan'
        trigger_price: float,
        size: float,
        position_side: str,  # 'long' or 'short'
        execute_price: float = 0,  # 0 = market price
        margin_mode: int = 1  # 1 = Cross, 3 = Isolated
    ) -> dict:
        """
        Place Take-Profit or Stop-Loss order
        
        plan_type: 'profit_plan' (TP) or 'loss_plan' (SL)
        trigger_price: Price that triggers the TP/SL
        size: Order quantity
        position_side: 'long' or 'short'
        execute_price: 0 for market, >0 for limit
        margin_mode: 1 for Cross, 3 for Isolated
        """
        body = {
            "symbol": self.symbol,
            "clientOrderId": self._unique_id(f"tpsl-{plan_type[:2]}"),
            "planType": plan_type,
            "triggerPrice": str(trigger_price),
            "executePrice": str(execute_price),
            "size": str(size),
            "positionSide": position_side,
            "marginMode": margin_mode
        }
        
        return self._post("/capi/v2/order/placeTpSlOrder", body)

    def get_fills(self, symbol: str = None) -> dict:
        """Get trade history / fills"""
        sym = symbol or self.symbol
        return self._get("/capi/v2/trade/fills", {"symbol": sym})
