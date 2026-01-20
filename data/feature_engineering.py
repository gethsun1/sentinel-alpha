import pandas as pd
import numpy as np

class FeatureEngineering:
    def __init__(self, data: pd.DataFrame):
        """
        data: DataFrame with columns ['timestamp', 'price', 'quantity']
        """
        self.data = data.copy()

    def compute_returns(self) -> pd.Series:
        """Compute log returns of price."""
        return np.log(self.data['price'] / self.data['price'].shift(1)).fillna(0)

    def compute_volatility(self, window: int = 10) -> pd.Series:
        """Compute rolling volatility (standard deviation of returns)."""
        returns = self.compute_returns()
        return returns.rolling(window=window).std().fillna(0)

    def compute_volume_acceleration(self, window: int = 10) -> pd.Series:
        """Compute rolling volume acceleration."""
        vol = self.data['quantity']
        return vol.diff().rolling(window=window).mean().fillna(0)

    def compute_regime_stability(self, window: int = 10) -> pd.Series:
        """
        Placeholder for regime stability metric.
        Example: rolling variance of returns or volatility normalized.
        """
        returns = self.compute_returns()
        return 1 / (returns.rolling(window=window).var() + 1e-6)

    def generate_features(self) -> pd.DataFrame:
        """Return DataFrame with derived features."""
        features = pd.DataFrame(index=self.data.index)
        features['price'] = self.data['price']
        features['returns'] = self.compute_returns()
        features['volatility'] = self.compute_volatility()
        features['volume_acceleration'] = self.compute_volume_acceleration()
        features['regime_stability'] = self.compute_regime_stability()
        return features

if __name__ == "__main__":
    from market_stream import BinanceClientMock, MarketStream

    client = BinanceClientMock()
    stream = MarketStream(client, symbol="BTCUSDT")
    df = stream.fetch_tick()

    fe = FeatureEngineering(df)
    features = fe.generate_features()
    print(features.head())
