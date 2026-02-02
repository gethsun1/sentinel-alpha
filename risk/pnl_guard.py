class PnLGuard:
    """
    Halts trading if drawdown exceeds threshold.
    """

    def __init__(self, max_drawdown_pct: float):
        self.max_drawdown_pct = max_drawdown_pct
        self.peak_equity = None
        self.trading_halted = False

    def update(self, equity: float):
        if self.peak_equity is None:
            self.peak_equity = equity
            return

        self.peak_equity = max(self.peak_equity, equity)

        drawdown = (self.peak_equity - equity) / self.peak_equity

        if drawdown >= self.max_drawdown_pct:
            self.trading_halted = True

    def can_trade(self) -> bool:
        return not self.trading_halted

    def reset(self):
        """
        Full reset of the guard state.
        """
        self.peak_equity = None
        self.trading_halted = False

    def force_unhalt(self):
        """
        Allow trading to resume without resetting the peak equity.
        Useful if user manually cleared positions and wants to continue.
        """
        self.trading_halted = False
