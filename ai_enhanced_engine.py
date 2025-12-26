"""
AI-Enhanced Signal Engine Integration
Combines enhanced models for maximum competition performance
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple

from data.feature_engineering import FeatureEngineering
from models.enhanced_regime_classifier import EnhancedRegimeClassifier
from models.adaptive_learning_agent import AdaptiveLearningAgent
from models.risk_filter import RiskFilter


class AIEnhancedSignalEngine:
    """
    Competition-Ready AI Signal Engine
    
    Combines:
    1. Enhanced fuzzy logic regime classifier
    2. Adaptive learning agent
    3. Pattern recognition
    4. Dynamic confidence calibration
    5. Multi-layer risk filtering
    """
    
    def __init__(self, market_data: pd.DataFrame):
        self.market_data = market_data.copy()
        
        # Feature engineering
        self.features = FeatureEngineering(market_data).generate_features()
        
        # AI Models
        self.regime_classifier = EnhancedRegimeClassifier(self.features)
        self.adaptive_agent = AdaptiveLearningAgent(lookback_window=100)
        
        # Track signals for learning
        self.signal_history = []
        self.last_signal_price = None
        self.last_signal_idx = None
    
    def generate_signals(self) -> pd.DataFrame:
        """
        Generate AI-enhanced trading signals
        
        Returns:
            DataFrame with columns:
            - timestamp
            - price
            - regime
            - base_confidence
            - pattern_scores
            - calibrated_confidence
            - signal (LONG/SHORT/NO-TRADE)
            - reasoning (explanation)
        """
        # Step 1: Enhanced regime classification with fuzzy logic
        regimes, base_confidences = self.regime_classifier.classify()
        
        # Step 2: Detect patterns in price movement
        prices = self.market_data['price'].values
        pattern_scores = []
        
        for i in range(len(prices)):
            if i < 10:
                # Not enough data for patterns
                pattern_scores.append({
                    'momentum_strength': 0.5,
                    'reversal_probability': 0.5,
                    'continuation_probability': 0.5
                })
            else:
                patterns = self.adaptive_agent.detect_market_pattern(
                    prices[max(0, i-20):i+1].tolist()
                )
                pattern_scores.append(patterns)
        
        # Step 3: Generate initial signals based on regimes
        initial_signals = []
        for regime in regimes:
            if regime == 'TREND_UP':
                initial_signals.append('LONG')
            elif regime == 'TREND_DOWN':
                initial_signals.append('SHORT')
            else:
                initial_signals.append('NO-TRADE')
        
        # Step 4: Calibrate confidence using adaptive learning
        calibrated_confidences = []
        final_signals = []
        reasoning = []
        
        for idx in range(len(regimes)):
            regime = regimes.iloc[idx]
            signal = initial_signals[idx]
            base_conf = base_confidences.iloc[idx]
            patterns = pattern_scores[idx]
            
            # Calibrate confidence with learned information
            calibrated_conf = self.adaptive_agent.calibrate_confidence(
                base_conf, regime, signal, patterns
            )
            
            # Decide if we should trade
            should_trade = self.adaptive_agent.should_trade(calibrated_conf)
            
            # Final signal
            if not should_trade or signal == 'NO-TRADE':
                final_signal = 'NO-TRADE'
                reason = self._generate_no_trade_reasoning(
                    regime, calibrated_conf, patterns, should_trade
                )
            else:
                final_signal = signal
                reason = self._generate_trade_reasoning(
                    signal, regime, calibrated_conf, patterns
                )
            
            calibrated_confidences.append(calibrated_conf)
            final_signals.append(final_signal)
            reasoning.append(reason)
        
        # Construct result DataFrame
        result = pd.DataFrame({
            'timestamp': self.market_data['timestamp'],
            'price': self.market_data['price'],
            'regime': regimes.values,
            'base_confidence': base_confidences.values,
            'momentum': [p['momentum_strength'] for p in pattern_scores],
            'reversal_prob': [p['reversal_probability'] for p in pattern_scores],
            'continuation_prob': [p['continuation_probability'] for p in pattern_scores],
            'calibrated_confidence': calibrated_confidences,
            'signal': final_signals,
            'reasoning': reasoning
        })
        
        return result
    
    def update_learning(self, signal_df: pd.DataFrame):
        """
        Update adaptive learning agent with outcomes
        
        Call this after trades are executed to enable online learning
        
        Args:
            signal_df: DataFrame from generate_signals() with actual outcomes
        """
        # Find executed trades (non NO-TRADE signals)
        trades = signal_df[signal_df['signal'] != 'NO-TRADE'].copy()
        
        if len(trades) == 0:
            return
        
        # Calculate PnL for each trade
        for idx in range(len(trades) - 1):
            current = trades.iloc[idx]
            next_price = trades.iloc[idx + 1]['price']
            
            # Calculate PnL based on signal direction
            if current['signal'] == 'LONG':
                pnl = next_price - current['price']
            else:  # SHORT
                pnl = current['price'] - next_price
            
            # Record outcome for learning
            self.adaptive_agent.record_outcome(
                regime=current['regime'],
                signal=current['signal'],
                pnl=pnl,
                confidence=current['calibrated_confidence']
            )
    
    def _generate_trade_reasoning(self, signal: str, regime: str, 
                                  confidence: float, patterns: Dict) -> str:
        """Generate human-readable explanation for trade decision"""
        reason_parts = []
        
        # Regime reasoning
        reason_parts.append(f"Market regime: {regime}")
        
        # Confidence reasoning
        if confidence > 0.8:
            reason_parts.append(f"Very high confidence ({confidence:.2f})")
        elif confidence > 0.7:
            reason_parts.append(f"High confidence ({confidence:.2f})")
        else:
            reason_parts.append(f"Moderate confidence ({confidence:.2f})")
        
        # Pattern reasoning
        if patterns['momentum_strength'] > 0.6:
            reason_parts.append("Strong momentum detected")
        if patterns['continuation_probability'] > 0.7:
            reason_parts.append("Trend continuation likely")
        
        # Signal-regime alignment
        if (signal == 'LONG' and regime == 'TREND_UP') or \
           (signal == 'SHORT' and regime == 'TREND_DOWN'):
            reason_parts.append("Signal aligned with regime")
        
        # Learning component
        regime_wr = self.adaptive_agent.get_regime_win_rate(regime)
        signal_wr = self.adaptive_agent.get_signal_win_rate(signal)
        
        if regime_wr > 0.6:
            reason_parts.append(f"Regime has {regime_wr:.1%} win rate")
        if signal_wr > 0.6:
            reason_parts.append(f"{signal} signals have {signal_wr:.1%} win rate")
        
        return " | ".join(reason_parts)
    
    def _generate_no_trade_reasoning(self, regime: str, confidence: float,
                                     patterns: Dict, threshold_passed: bool) -> str:
        """Generate explanation for why no trade was taken"""
        if not threshold_passed:
            threshold = self.adaptive_agent.confidence_threshold
            return f"Confidence {confidence:.2f} below threshold {threshold:.2f}"
        
        if regime not in ['TREND_UP', 'TREND_DOWN']:
            return f"Non-trending regime ({regime}) - staying flat"
        
        if patterns['reversal_probability'] > 0.7:
            return "High reversal probability detected - avoiding entry"
        
        return "Risk filters rejected signal"
    
    def get_performance_stats(self) -> Dict:
        """Get current AI learning statistics"""
        return self.adaptive_agent.get_stats()


# Demo usage
if __name__ == "__main__":
    from data.market_stream import BinanceClientMock, MarketStream
    
    print("=" * 70)
    print("AI-ENHANCED SIGNAL ENGINE DEMO")
    print("=" * 70)
    print()
    
    # Get market data
    client = BinanceClientMock()
    stream = MarketStream(client, symbol="BTCUSDT")
    market_data = stream.fetch_tick()
    
    # Create AI engine
    engine = AIEnhancedSignalEngine(market_data)
    
    # Generate signals
    print("Generating AI-enhanced signals...")
    signals = engine.generate_signals()
    
    # Display results
    print("\nSignal Summary:")
    print(f"Total ticks: {len(signals)}")
    print(f"LONG signals: {(signals['signal'] == 'LONG').sum()}")
    print(f"SHORT signals: {(signals['signal'] == 'SHORT').sum()}")
    print(f"NO-TRADE: {(signals['signal'] == 'NO-TRADE').sum()}")
    print()
    
    # Show sample signals
    print("Sample Signals (last 5):")
    print("-" * 70)
    for idx in range(max(0, len(signals)-5), len(signals)):
        row = signals.iloc[idx]
        print(f"\nTick {idx}:")
        print(f"  Price: ${row['price']:.2f}")
        print(f"  Regime: {row['regime']}")
        print(f"  Signal: {row['signal']}")
        print(f"  Confidence: {row['calibrated_confidence']:.3f}")
        print(f"  Reasoning: {row['reasoning']}")
    
    print()
    print("=" * 70)
    
    # Simulate learning (for demo)
    print("\nSimulating online learning...")
    engine.update_learning(signals)
    
    # Show learned statistics
    print("\nLearning Statistics:")
    stats = engine.get_performance_stats()
    print(f"Adaptive confidence threshold: {stats['confidence_threshold']:.3f}")
    print()
    
    print("Regime Performance:")
    for regime, perf in stats['regime_performance'].items():
        if perf['count'] > 0:
            print(f"  {regime}: {perf['count']} trades, "
                  f"{perf['win_rate']:.1%} win rate, "
                  f"avg PnL: ${perf['avg_pnl']:.2f}")


