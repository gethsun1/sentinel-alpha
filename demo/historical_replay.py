import pandas as pd
import numpy as np
from strategy.signal_engine import SignalEngine
from data.market_stream import BinanceClientMock, MarketStream

class HistoricalReplay:
    """
    Provides demo data and simulated signals for review and evaluation.
    """

    def __init__(self):
        self.client = BinanceClientMock()
        self.symbol = "BTCUSDT"

    def simulate(self) -> pd.DataFrame:
        """
        Fetches demo market data and returns signals with regimes and confidence.
        """
        stream = MarketStream(self.client, self.symbol)
        df_market = stream.fetch_tick()

        engine = SignalEngine(df_market)
        df_signals = engine.generate_signals()
        return df_signals

if __name__ == "__main__":
    replay = HistoricalReplay()
    df_demo = replay.simulate()
    print(df_demo.head())
