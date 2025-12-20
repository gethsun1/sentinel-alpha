import pandas as pd
import numpy as np

class Metrics:
    """
    Calculates metrics such as directional accuracy, max drawdown, 
    volatility-adjusted performance, and signal-to-noise ratio.
    """

    def __init__(self, df_signals: pd.DataFrame):
        """
        df_signals: DataFrame with columns ['timestamp', 'price', 'regime', 'confidence', 'signal']
        """
        self.df = df_signals.copy()

    def directional_accuracy(self) -> float:
        """
        Simple directional accuracy proxy:
        % of signals aligned with price movement in next tick
        """
        prices = self.df['price'].values
        signals = self.df['signal'].values
        correct = 0
        for i in range(len(prices)-1):
            movement = prices[i+1] - prices[i]
            if signals[i] == 'LONG' and movement > 0:
                correct += 1
            elif signals[i] == 'SHORT' and movement < 0:
                correct += 1
        return correct / max(1, len(prices)-1)

    def max_drawdown(self) -> float:
        """
        Computes max drawdown of cumulative returns based on signals.
        """
        returns = []
        prices = self.df['price'].values
        signals = self.df['signal'].values
        for i in range(len(prices)-1):
            if signals[i] == 'LONG':
                returns.append(prices[i+1] - prices[i])
            elif signals[i] == 'SHORT':
                returns.append(prices[i] - prices[i+1])
            else:
                returns.append(0)
        cum_returns = np.cumsum(returns)
        peak = cum_returns[0]
        drawdowns = []
        for x in cum_returns:
            if x > peak:
                peak = x
            drawdowns.append(peak - x)
        return max(drawdowns)

    def signal_count(self) -> int:
        return len(self.df[self.df['signal'] != 'NO-TRADE'])

    def summary(self) -> dict:
        return {
            "directional_accuracy": self.directional_accuracy(),
            "max_drawdown": self.max_drawdown(),
            "signal_count": self.signal_count()
        }

if __name__ == "__main__":
    from demo.historical_replay import HistoricalReplay

    df_demo = HistoricalReplay().simulate()
    metrics = Metrics(df_demo)
    print(metrics.summary())
