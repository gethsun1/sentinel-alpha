import pandas as pd
import numpy as np

class RegimeClassifier:
    """
    Classifies market regimes based on streaming features.
    Example regimes:
      - TREND_UP
      - TREND_DOWN
      - RANGE
      - VOLATILITY_EXPANSION
      - VOLATILITY_COMPRESSION
    """

    def __init__(self, features: pd.DataFrame):
        """
        features: DataFrame with columns ['returns', 'volatility', 'volume_acceleration', 'regime_stability']
        """
        self.features = features.copy()

    def classify(self) -> pd.Series:
        """
        Returns a pandas Series of regime labels for each row.
        """
        labels = []
        for idx, row in self.features.iterrows():
            if row['volatility'] > 0.02 and row['returns'] > 0:
                labels.append('TREND_UP')
            elif row['volatility'] > 0.02 and row['returns'] < 0:
                labels.append('TREND_DOWN')
            elif row['volatility'] < 0.01:
                labels.append('RANGE')
            elif row['volatility'] > 0.03:
                labels.append('VOLATILITY_EXPANSION')
            else:
                labels.append('VOLATILITY_COMPRESSION')
        return pd.Series(labels, index=self.features.index)

if __name__ == "__main__":
    from data.feature_engineering import FeatureEngineering
    from data.market_stream import BinanceClientMock, MarketStream

    client = BinanceClientMock()
    stream = MarketStream(client, symbol="BTCUSDT")
    df = stream.fetch_tick()

    fe = FeatureEngineering(df)
    features = fe.generate_features()

    classifier = RegimeClassifier(features)
    regimes = classifier.classify()
    print(regimes.head())
