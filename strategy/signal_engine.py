import pandas as pd
from data.feature_engineering import FeatureEngineering
from models.regime_classifier import RegimeClassifier
from models.confidence_model import ConfidenceModel
from models.risk_filter import RiskFilter

class SignalEngine:
    """
    Combines features, AI models, and risk filters to emit final signals.
    """

    def __init__(self, market_data: pd.DataFrame):
        """
        market_data: DataFrame with ['timestamp', 'price', 'quantity']
        """
        self.market_data = market_data.copy()
        self.features = FeatureEngineering(market_data).generate_features()

    def generate_signals(self) -> pd.DataFrame:
        """
        Returns a DataFrame with columns:
        ['timestamp', 'price', 'regime', 'confidence', 'signal']
        """
        # Step 1: Classify market regime
        classifier = RegimeClassifier(self.features)
        regimes = classifier.classify()

        # Step 2: Compute confidence
        confidence_model = ConfidenceModel(self.features, regimes)
        confidence_scores = confidence_model.compute_confidence()

        # Step 3: Apply risk filters
        risk_filter = RiskFilter(self.features, regimes, confidence_scores)
        signals = risk_filter.apply_filter()

        # Combine results
        df_signals = pd.DataFrame({
            'timestamp': self.market_data['timestamp'],
            'price': self.market_data['price'],
            'regime': regimes,
            'confidence': confidence_scores,
            'signal': signals
        })

        return df_signals

if __name__ == "__main__":
    from data.market_stream import BinanceClientMock, MarketStream

    # Demo run
    client = BinanceClientMock()
    stream = MarketStream(client, symbol="BTCUSDT")
    df_market = stream.fetch_tick()

    engine = SignalEngine(df_market)
    df_signals = engine.generate_signals()
    print(df_signals.head())
