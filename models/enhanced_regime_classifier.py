import pandas as pd
import numpy as np
from typing import Dict, Tuple

class EnhancedRegimeClassifier:
    """
    AI-Enhanced Market Regime Classifier using Fuzzy Logic & Multi-Feature Scoring
    
    Improvements over basic classifier:
    1. Fuzzy membership functions (no hard thresholds)
    2. Multi-feature weighted scoring
    3. Regime transition smoothing
    4. Confidence-weighted regime persistence
    """
    
    def __init__(self, features: pd.DataFrame):
        self.features = features.copy()
        
        # Fuzzy membership thresholds (learned from data)
        self.volatility_low = 0.008
        self.volatility_medium = 0.015
        self.volatility_high = 0.025
        
        # Regime persistence (prevent rapid switching)
        self.last_regime = None
        self.regime_persistence_count = 0
        self.min_persistence = 3  # Minimum ticks before regime change
    
    def fuzzy_membership(self, value: float, low: float, mid: float, high: float) -> Dict[str, float]:
        """
        Compute fuzzy membership degrees
        Returns: {'low': score, 'medium': score, 'high': score}
        """
        membership = {}
        
        # Low membership (triangular)
        if value <= low:
            membership['low'] = 1.0
        elif value <= mid:
            membership['low'] = (mid - value) / (mid - low)
        else:
            membership['low'] = 0.0
        
        # Medium membership (triangular)
        if value <= low:
            membership['medium'] = 0.0
        elif value <= mid:
            membership['medium'] = (value - low) / (mid - low)
        elif value <= high:
            membership['medium'] = (high - value) / (high - mid)
        else:
            membership['medium'] = 0.0
        
        # High membership (triangular)
        if value <= mid:
            membership['high'] = 0.0
        elif value <= high:
            membership['high'] = (value - mid) / (high - mid)
        else:
            membership['high'] = 1.0
        
        return membership
    
    def compute_regime_scores(self, row: pd.Series) -> Dict[str, float]:
        """
        Compute fuzzy scores for each possible regime
        Returns: {'TREND_UP': score, 'TREND_DOWN': score, ...}
        """
        # Get fuzzy memberships
        vol_membership = self.fuzzy_membership(
            row['volatility'], 
            self.volatility_low, 
            self.volatility_medium, 
            self.volatility_high
        )
        
        returns = row['returns']
        volume_accel = row['volume_acceleration']
        stability = row['regime_stability']
        
        # Regime scoring (weighted combination of features)
        scores = {}
        
        # TREND_UP: High volatility + Positive returns + Volume confirmation
        scores['TREND_UP'] = (
            vol_membership['high'] * 0.4 +
            max(0, returns * 100) * 0.3 +  # Positive returns boost
            max(0, volume_accel) * 0.2 +   # Positive volume boost
            (1 / (1 + np.exp(-stability))) * 0.1  # Stability sigmoid
        )
        
        # TREND_DOWN: High volatility + Negative returns + Volume confirmation
        scores['TREND_DOWN'] = (
            vol_membership['high'] * 0.4 +
            max(0, -returns * 100) * 0.3 +  # Negative returns boost
            max(0, volume_accel) * 0.2 +
            (1 / (1 + np.exp(-stability))) * 0.1
        )
        
        # RANGE: Low volatility + Low returns + High stability
        scores['RANGE'] = (
            vol_membership['low'] * 0.5 +
            (1 - abs(returns) * 100) * 0.3 +  # Low movement
            (1 / (1 + np.exp(-stability))) * 0.2
        )
        
        # VOLATILITY_EXPANSION: Very high volatility + Low stability
        scores['VOLATILITY_EXPANSION'] = (
            vol_membership['high'] * 0.6 +
            (1 - 1 / (1 + np.exp(-stability))) * 0.4  # Low stability
        )
        
        # VOLATILITY_COMPRESSION: Low volatility + High stability
        scores['VOLATILITY_COMPRESSION'] = (
            vol_membership['low'] * 0.5 +
            (1 / (1 + np.exp(-stability))) * 0.5
        )
        
        # Normalize scores
        total = sum(scores.values())
        if total > 0:
            scores = {k: v/total for k, v in scores.items()}
        
        return scores
    
    def apply_regime_persistence(self, new_regime: str, confidence: float) -> str:
        """
        Smooth regime transitions to prevent whipsawing
        """
        if self.last_regime is None:
            self.last_regime = new_regime
            self.regime_persistence_count = 1
            return new_regime
        
        # If same regime, increment counter
        if new_regime == self.last_regime:
            self.regime_persistence_count += 1
            return new_regime
        
        # If different regime, check if we should switch
        # Only switch if:
        # 1. We've been in current regime long enough, OR
        # 2. New regime has very high confidence (>0.8)
        if self.regime_persistence_count >= self.min_persistence or confidence > 0.8:
            self.last_regime = new_regime
            self.regime_persistence_count = 1
            return new_regime
        else:
            # Stay in current regime
            self.regime_persistence_count += 1
            return self.last_regime
    
    def classify(self) -> Tuple[pd.Series, pd.Series]:
        """
        Classify market regimes with confidence scores
        Returns: (regimes, confidences)
        """
        regimes = []
        confidences = []
        
        for idx, row in self.features.iterrows():
            # Compute fuzzy scores for all regimes
            scores = self.compute_regime_scores(row)
            
            # Best regime is highest score
            best_regime = max(scores, key=scores.get)
            best_confidence = scores[best_regime]
            
            # Apply persistence smoothing
            final_regime = self.apply_regime_persistence(best_regime, best_confidence)
            
            regimes.append(final_regime)
            confidences.append(best_confidence)
        
        return pd.Series(regimes, index=self.features.index), pd.Series(confidences, index=self.features.index)

# Demo usage
if __name__ == "__main__":
    from data.feature_engineering import FeatureEngineering
    from data.market_stream import BinanceClientMock, MarketStream
    
    client = BinanceClientMock()
    stream = MarketStream(client, symbol="BTCUSDT")
    df = stream.fetch_tick()
    
    fe = FeatureEngineering(df)
    features = fe.generate_features()
    
    # Use enhanced classifier
    classifier = EnhancedRegimeClassifier(features)
    regimes, regime_confidences = classifier.classify()
    
    print("Regimes:", regimes.head())
    print("Regime Confidences:", regime_confidences.head())


