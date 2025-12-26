import time

class ExecutionGuard:
    def __init__(self, cooldown_seconds: int, max_position: float):
        self.cooldown = cooldown_seconds
        self.max_position = max_position
        self.last_trade_ts = 0
        self.current_position = 0.0

    def can_trade(self, size: float) -> bool:
        now = time.time()

        if now - self.last_trade_ts < self.cooldown:
            return False

        if abs(self.current_position + size) > self.max_position:
            return False

        return True

    def register_trade(self, size: float):
        self.last_trade_ts = time.time()
        self.current_position += size
