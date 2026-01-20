import pandas as pd
import numpy as np

class ConfidenceModel:
    """
    Computes a confidence score for each regime signal.
    Score range: 0 (low) → 1 (high)
    """

    def __init__(self, features: pd.DataFrame, regimes: pd.Series):
        self.features = features.copy()
        self.regimes = regimes.copy()

    def compute_confidence(self) -> pd.Series:
        """
        Simple heuristic:
        - Higher regime_stability → higher confidence
        - Lower volatility → higher confidence in RANGE
        - Higher volatility → moderate confidence in TREND
        """
        scores = []
        for idx, row in self.features.iterrows():
            regime = self.regimes[idx]
            base = row['regime_stability']
            if regime in ['TREND_UP', 'TREND_DOWN']:
                score = min(1.0, base * (1 - row['volatility']))
            elif regime == 'RANGE':
                score = min(1.0, base * (1 - row['volatility']/2))
            else:  # volatility expansion/compression
                score = max(0.3, min(0.8, base))
            scores.append(score)
        return pd.Series(scores, index=self.features.index)

if __name__ == "__main__":
    from data.feature_engineering import FeatureEngineering
    from data.market_stream import BinanceClientMock, MarketStream
    from models.regime_classifier import RegimeClassifier

    client = BinanceClientMock()
    stream = MarketStream(client, symbol="BTCUSDT")
    df = stream.fetch_tick()

    fe = FeatureEngineering(df)
    features = fe.generate_features()

    classifier = RegimeClassifier(features)
    regimes = classifier.classify()

    confidence_model = ConfidenceModel(features, regimes)
    confidence_scores = confidence_model.compute_confidence()
    print(confidence_scores.head())
