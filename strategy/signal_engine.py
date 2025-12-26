import pandas as pd
from data.feature_engineering import FeatureEngineering
from models.regime_classifier import RegimeClassifier
from models.confidence_model import ConfidenceModel
from models.risk_filter import RiskFilter

from execution.execution_guard import ExecutionGuard
from execution.weex_adapter import WeexExecutionAdapter
from utils.logger import JsonLogger
import yaml


class SignalEngine:
    """
    Combines AI signal intelligence with execution governance.
    """

    def __init__(self, market_data: pd.DataFrame, config_path: str = None):
        """
        market_data: DataFrame with ['timestamp', 'price', 'quantity']
        config_path: optional competition/live config
        """
        self.market_data = market_data.copy()
        self.features = FeatureEngineering(market_data).generate_features()

        self.config = None
        self.guard = None
        self.adapter = None
        self.audit_logger = None
        self.compliance_logger = None

        if config_path:
            self._load_execution_layer(config_path)

    def _load_execution_layer(self, config_path: str):
        with open(config_path) as f:
            self.config = yaml.safe_load(f)

        self.guard = ExecutionGuard(
            cooldown_seconds=self.config["exchange"]["cooldown_seconds"],
            max_position=self.config["exchange"]["max_position_size"],
        )

        self.adapter = WeexExecutionAdapter(
            api_key="WEEX_API_KEY",
            secret_key="WEEX_SECRET",
            passphrase="WEEX_PASSPHRASE",
            default_symbol=self.config["exchange"]["symbol"],
            leverage=self.config["exchange"]["leverage"],
            dry_run=self.config["mode"] != "live",
        )

        self.audit_logger = JsonLogger(self.config["logging"]["audit_path"])
        self.compliance_logger = JsonLogger(self.config["logging"]["compliance_path"])

    def generate_signals(self) -> pd.DataFrame:
        """
        Pure AI inference layer (no execution).
        Returns:
        ['timestamp', 'price', 'regime', 'confidence', 'signal']
        """
        classifier = RegimeClassifier(self.features)
        regimes = classifier.classify()

        confidence_model = ConfidenceModel(self.features, regimes)
        confidence_scores = confidence_model.compute_confidence()

        risk_filter = RiskFilter(self.features, regimes, confidence_scores)
        signals = risk_filter.apply_filter()

        return pd.DataFrame({
            "timestamp": self.market_data["timestamp"],
            "price": self.market_data["price"],
            "regime": regimes,
            "confidence": confidence_scores,
            "signal": signals,
        })

    def execute_signals(self, df_signals: pd.DataFrame):
        """
        Competition-safe execution layer.
        """
        if not self.adapter:
            raise RuntimeError("Execution layer not initialized")

        for _, row in df_signals.iterrows():
            if row["signal"] == "NO_TRADE":
                continue

            event = {
                "direction": row["signal"],
                "confidence": row["confidence"],
                "price": row["price"],
                "timestamp": row["timestamp"],
            }

            self.audit_logger.log({"event": "signal_evaluated", **event})

            if row["confidence"] < self.config["risk"]["min_confidence"]:
                self.compliance_logger.log({
                    "event": "rejected",
                    "reason": "low_confidence",
                    **event
                })
                continue

            size = self.config["exchange"]["max_position_size"]

            if not self.guard.can_trade(size):
                self.compliance_logger.log({
                    "event": "blocked",
                    "reason": "cooldown_or_position_limit",
                    **event
                })
                continue

            result = self.adapter.place_order(
                direction=row["signal"],
                size=size,
                price=row["price"]
            )

            self.audit_logger.log({
                "event": "order_placed",
                "result": result,
                **event
            })

            self.guard.register_trade(size)
