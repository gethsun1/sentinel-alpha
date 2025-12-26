class SentinelAlphaAgent:
    """
    Autonomous AI trading agent for WEEX AI Wars.
    """

    def __init__(
        self,
        signal_engine,
        execution_adapter,
        execution_guard,
        pnl_guard,
        audit_logger
    ):
        self.signal_engine = signal_engine
        self.execution_adapter = execution_adapter
        self.execution_guard = execution_guard
        self.pnl_guard = pnl_guard
        self.audit_logger = audit_logger

        self.internal_state = {
            "regime": None,
            "confidence": None,
            "last_action": None,
        }

    def perceive(self, market_data):
        signals = self.signal_engine.generate_signals(market_data)
        return signals.iloc[-1]

    def decide(self, signal_row):
        self.internal_state["regime"] = signal_row["regime"]
        self.internal_state["confidence"] = signal_row["confidence"]

        return signal_row["signal"]

    def act(self, decision, price):
        if not self.pnl_guard.can_trade():
            return "HALTED"

        if not self.execution_guard.can_trade(size=0.0001):
            return "BLOCKED"

        result = self.execution_adapter.place_order(
            direction=decision,
            size=0.0001,
            price=price
        )

        self.execution_guard.register_trade(0.0001)
        self.internal_state["last_action"] = decision

        return result

    def step(self, market_data):
        signal = self.perceive(market_data)
        decision = self.decide(signal)
        action = self.act(decision, signal["price"])

        self.audit_logger.log_step(
            perception=signal.to_dict(),
            decision=decision,
            action=action,
            state=self.internal_state
        )

        return action
