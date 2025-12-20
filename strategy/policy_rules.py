class PolicyRules:
    """
    Contains static parameters for risk management and compliance.
    """

    def __init__(self):
        # Confidence threshold below which no trade is allowed
        self.min_confidence = 0.5

        # Maximum allowed conceptual leverage
        self.max_leverage = 20

        # Cooldown periods (number of ticks) after high volatility or loss
        self.cooldown_period = 2

        # Volatility thresholds for gating
        self.volatility_block_threshold = 0.05

        # Minimum number of signals required for valid strategy submission
        self.min_signal_count = 10

        # Prohibited strategies (martingale, grid, averaging down)
        self.prohibited_strategies = [
            "martingale",
            "grid",
            "averaging_down"
        ]

    def check_signal_count(self, signals):
        """
        Ensure minimum number of signals generated for hackathon compliance.
        """
        return len(signals) >= self.min_signal_count

    def is_signal_allowed(self, confidence, volatility):
        """
        Returns True if a signal passes confidence and volatility checks.
        """
        if confidence < self.min_confidence:
            return False
        if volatility > self.volatility_block_threshold:
            return False
        return True

if __name__ == "__main__":
    # Demo checks
    policy = PolicyRules()
    print("Minimum signal count required:", policy.min_signal_count)
    print("Max conceptual leverage:", policy.max_leverage)
    print("Volatility threshold for gating:", policy.volatility_block_threshold)
