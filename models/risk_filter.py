import pandas as pd

class RiskFilter:
    """
    Filters signals based on predefined risk conditions.
    """

    def __init__(self, features: pd.DataFrame, regimes: pd.Series, confidence: pd.Series):
        self.features = features.copy()
        self.regimes = regimes.copy()
        self.confidence = confidence.copy()
        self.cooldown_counter = 0

    def apply_filter(self) -> pd.Series:
        """
        Returns filtered signals:
          - LONG, SHORT, or NO-TRADE
        """
        filtered_signals = []

        for idx in self.features.index:
            regime = self.regimes[idx]
            score = self.confidence[idx]
            vol = self.features.loc[idx, 'volatility']

            # Cooldown logic: block signals for 1 step after VERY high volatility
            # ADJUSTED: Increased threshold from 0.05 to 0.10 (less restrictive)
            if vol > 0.10:
                self.cooldown_counter = 2

            if self.cooldown_counter > 0:
                filtered_signals.append('NO-TRADE')
                self.cooldown_counter -= 1
                continue

            # Confidence threshold gating - Updated to match system-wide threshold
            # Minimum confidence required: 0.65
            if score < 0.65:
                filtered_signals.append('NO-TRADE')
                continue

            # Signal assignment based on regime
            if regime == 'TREND_UP':
                filtered_signals.append('LONG')
            elif regime == 'TREND_DOWN':
                filtered_signals.append('SHORT')
            else:
                filtered_signals.append('NO-TRADE')

        return pd.Series(filtered_signals, index=self.features.index)

if __name__ == "__main__":
    from data.feature_engineering import FeatureEngineering
    from data.market_stream import BinanceClientMock, MarketStream
    from models.regime_classifier import RegimeClassifier
    from models.confidence_model import ConfidenceModel

    client = BinanceClientMock()
    stream = MarketStream(client, symbol="BTCUSDT")
    df = stream.fetch_tick()

    fe = FeatureEngineering(df)
    features = fe.generate_features()

    classifier = RegimeClassifier(features)
    regimes = classifier.classify()

    confidence_model = ConfidenceModel(features, regimes)
    confidence_scores = confidence_model.compute_confidence()

    risk_filter = RiskFilter(features, regimes, confidence_scores)
    signals = risk_filter.apply_filter()
    print(signals.head())
