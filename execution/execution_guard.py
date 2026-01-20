import time
from typing import Optional


class ExecutionGuard:
    """
    Lightweight execution throttle:
    - Cooldown enforced per symbol
    - Optional max notional check (USD) to avoid oversizing on low-price coins
    """

    def __init__(self, cooldown_seconds: int, max_notional_usd: Optional[float] = None):
        self.cooldown = cooldown_seconds
        self.max_notional_usd = max_notional_usd
        self.last_trade_ts = {}  # per-symbol timestamps

    def can_trade(self, size: float, symbol: str = "global", price: Optional[float] = None) -> bool:
        now = time.time()
        last = self.last_trade_ts.get(symbol, 0)

        # Per-symbol cooldown
        if now - last < self.cooldown:
            return False

        # Optional notional cap (protect against unit-mismatch on alt contracts)
        if self.max_notional_usd is not None and price is not None:
            notional = size * price
            if notional > self.max_notional_usd:
                return False

        return True

    def register_trade(self, size: float, symbol: str = "global"):
        self.last_trade_ts[symbol] = time.time()
