import pandas as pd
import numpy as np
from collections import deque
from typing import Dict, List

class AdaptiveLearningAgent:
    """
    AI Agent with Online Learning Capabilities
    
    Key Features:
    1. Learn from recent trading outcomes
    2. Adapt thresholds based on market conditions
    3. Track regime-specific performance
    4. Dynamic confidence calibration
    5. Exploit patterns in recent market behavior
    """
    
    def __init__(self, lookback_window: int = 100):
        self.lookback_window = lookback_window
        
        # Regime-specific performance tracking
        self.regime_performance = {
            'TREND_UP': deque(maxlen=50),
            'TREND_DOWN': deque(maxlen=50),
            'RANGE': deque(maxlen=50),
            'VOLATILITY_EXPANSION': deque(maxlen=50),
            'VOLATILITY_COMPRESSION': deque(maxlen=50)
        }
        
        # Signal-specific win rates
        self.signal_outcomes = {
            'LONG': {'wins': 0, 'losses': 0, 'total_pnl': 0.0},
            'SHORT': {'wins': 0, 'losses': 0, 'total_pnl': 0.0}
        }
        
        # Adaptive thresholds (learned online) - OPTIMIZED FOR COMPETITION
        self.confidence_threshold = 0.60  # Optimized to 0.60 for 2-3 trades/day/symbol
        self.min_confidence = 0.58  # Floor with calibration headroom
        self.max_confidence = 0.75  # Maximum allowed (was 0.9)
        
        # Market condition memory
        self.recent_volatility = deque(maxlen=lookback_window)
        self.recent_returns = deque(maxlen=lookback_window)
        self.recent_volumes = deque(maxlen=lookback_window)
        
        # Pattern detection
        self.pattern_buffer = deque(maxlen=20)  # Last 20 price movements
        
    def record_outcome(self, regime: str, signal: str, pnl: float, confidence: float):
        """
        Record trading outcome for online learning
        
        Args:
            regime: Market regime when trade was made
            signal: LONG or SHORT
            pnl: Profit/loss from the trade
            confidence: Confidence score when signal was generated
        """
        # Update regime performance
        self.regime_performance[regime].append({
            'pnl': pnl,
            'confidence': confidence,
            'signal': signal
        })
        
        # Update signal outcomes
        if pnl > 0:
            self.signal_outcomes[signal]['wins'] += 1
        else:
            self.signal_outcomes[signal]['losses'] += 1
        self.signal_outcomes[signal]['total_pnl'] += pnl
    
    def get_regime_win_rate(self, regime: str) -> float:
        """Calculate win rate for specific regime"""
        outcomes = self.regime_performance[regime]
        if len(outcomes) == 0:
            return 0.5  # Neutral prior
        
        wins = sum(1 for o in outcomes if o['pnl'] > 0)
        return wins / len(outcomes)
    
    def get_signal_win_rate(self, signal: str) -> float:
        """Calculate overall win rate for signal direction"""
        # NO-TRADE has no win rate (neutral)
        if signal == 'NO-TRADE':
            return 0.5
        
        if signal not in self.signal_outcomes:
            return 0.5  # Neutral prior for unknown signals
        
        stats = self.signal_outcomes[signal]
        total = stats['wins'] + stats['losses']
        if total == 0:
            return 0.5
        return stats['wins'] / total
    
    def adapt_confidence_threshold(self):
        """
        Dynamically adjust confidence threshold based on recent performance
        
        Logic:
        - If recent trades are losing → increase threshold (be more selective)
        - If recent trades are winning → decrease threshold (be more aggressive)
        """
        # Calculate recent win rate across all regimes
        all_recent_outcomes = []
        for outcomes in self.regime_performance.values():
            all_recent_outcomes.extend(outcomes)
        
        if len(all_recent_outcomes) < 10:
            return  # Not enough data
        
        # Get last 20 outcomes
        recent = all_recent_outcomes[-20:]
        recent_win_rate = sum(1 for o in recent if o['pnl'] > 0) / len(recent)
        
        # Adapt threshold (MORE AGGRESSIVE ADAPTATION)
        if recent_win_rate < 0.35:  # Losing streak (was 0.4)
            self.confidence_threshold = min(
                self.max_confidence,
                self.confidence_threshold + 0.03  # Increase more (was 0.02)
            )
        elif recent_win_rate > 0.55:  # Winning streak (was 0.6, more lenient)
            self.confidence_threshold = max(
                self.min_confidence,
                self.confidence_threshold - 0.02  # Decrease more (was 0.01)
            )
        
        print(f"[Adaptive AI] Win rate: {recent_win_rate:.2f}, Adjusted confidence threshold: {self.confidence_threshold:.3f}")
    
    def detect_market_pattern(self, recent_prices: List[float]) -> Dict[str, float]:
        """
        Detect short-term patterns in price movement
        
        Returns:
            Dictionary of pattern scores:
            - momentum_strength: 0-1 (how strong is current momentum)
            - reversal_probability: 0-1 (probability of reversal)
            - continuation_probability: 0-1 (probability of continuation)
        """
        if len(recent_prices) < 10:
            return {
                'momentum_strength': 0.5,
                'reversal_probability': 0.5,
                'continuation_probability': 0.5
            }
        
        prices = np.array(recent_prices[-20:])
        returns = np.diff(prices) / prices[:-1]
        
        # Momentum strength (using exponential moving average of returns)
        weights = np.exp(np.linspace(-1., 0., len(returns)))
        weights /= weights.sum()
        momentum = abs(np.sum(weights * returns))
        momentum_strength = min(1.0, momentum * 10)  # Scale to 0-1
        
        # Reversal detection (mean reversion signal)
        # Check if we're far from recent mean
        recent_mean = prices[-10:].mean()
        current_deviation = abs(prices[-1] - recent_mean) / recent_mean
        reversal_probability = min(1.0, current_deviation * 100)  # Scale to 0-1
        
        # Continuation probability (trend strength)
        # Count consecutive moves in same direction
        consecutive = 1
        for i in range(len(returns)-1, 0, -1):
            if returns[i] * returns[i-1] > 0:  # Same sign
                consecutive += 1
            else:
                break
        continuation_probability = min(1.0, consecutive / 10)
        
        return {
            'momentum_strength': momentum_strength,
            'reversal_probability': reversal_probability,
            'continuation_probability': continuation_probability
        }
    
    def calibrate_confidence(self, base_confidence: float, regime: str, signal: str, 
                            market_patterns: Dict[str, float]) -> float:
        """
        Calibrate confidence score using learned information
        
        Args:
            base_confidence: Initial confidence from model
            regime: Current market regime
            signal: Proposed signal (LONG/SHORT/NO-TRADE)
            market_patterns: Pattern detection results
        
        Returns:
            Calibrated confidence score
        """
        # Start with base confidence
        calibrated = base_confidence
        
        # NO-TRADE signals don't need much calibration
        if signal == 'NO-TRADE':
            return calibrated
        
        # COMPETITION MODE: More generous confidence boosts
        
        # Base boost for having any signal (encourages trading)
        if signal in ['LONG', 'SHORT']:
            calibrated += 0.12  # INCREASED: Base boost for taking action (was 0.08)
        
        # Adjust based on regime-specific win rate
        regime_win_rate = self.get_regime_win_rate(regime)
        regime_adjustment = (regime_win_rate - 0.5) * 0.25  # Increased from 0.2
        calibrated += regime_adjustment
        
        # Adjust based on signal-specific win rate
        signal_win_rate = self.get_signal_win_rate(signal)
        signal_adjustment = (signal_win_rate - 0.5) * 0.20  # Increased from 0.15
        calibrated += signal_adjustment
        
        # Adjust based on momentum/pattern alignment (MORE GENEROUS)
        if signal == 'LONG' and market_patterns['momentum_strength'] > 0.25:  # Lowered from 0.3
            calibrated += 0.10  # Increased from 0.08
        elif signal == 'SHORT' and market_patterns['momentum_strength'] > 0.25:
            calibrated += 0.10
        
        # Penalize if reversal likely (LESS STRICT)
        if market_patterns['reversal_probability'] > 0.8:  # Increased from 0.7
            calibrated -= 0.05  # Reduced penalty from 0.1
        
        # Boost if continuation likely (MORE GENEROUS)
        if market_patterns['continuation_probability'] > 0.5:  # Lowered from 0.7
            calibrated += 0.08  # Increased from 0.05
        
        # Clamp to valid range
        calibrated = np.clip(calibrated, 0.0, 1.0)
        
        return calibrated
    
    def should_trade(self, calibrated_confidence: float) -> bool:
        """
        Decide if we should trade based on calibrated confidence
        and adaptive threshold
        """
        # Periodically adapt threshold
        self.adapt_confidence_threshold()
        
        return calibrated_confidence >= self.confidence_threshold
    
    def get_stats(self) -> Dict:
        """Get current learning statistics"""
        return {
            'confidence_threshold': self.confidence_threshold,
            'regime_performance': {
                regime: {
                    'count': len(outcomes),
                    'win_rate': self.get_regime_win_rate(regime),
                    'avg_pnl': np.mean([o['pnl'] for o in outcomes]) if outcomes else 0.0
                }
                for regime, outcomes in self.regime_performance.items()
            },
            'signal_stats': self.signal_outcomes
        }


# Example usage
if __name__ == "__main__":
    agent = AdaptiveLearningAgent()
    
    # Simulate some trading outcomes
    agent.record_outcome('TREND_UP', 'LONG', 150.0, 0.75)
    agent.record_outcome('TREND_UP', 'LONG', -50.0, 0.65)
    agent.record_outcome('TREND_DOWN', 'SHORT', 200.0, 0.80)
    agent.record_outcome('RANGE', 'LONG', -30.0, 0.60)
    
    # Check learned statistics
    print("Adaptive Learning Stats:")
    print(agent.get_stats())
    
    # Test pattern detection
    prices = [100, 101, 102, 103, 104, 105, 106, 105, 104, 103]
    patterns = agent.detect_market_pattern(prices)
    print("\nPattern Detection:")
    print(patterns)
    
    # Test confidence calibration
    base_conf = 0.70
    calibrated = agent.calibrate_confidence(base_conf, 'TREND_UP', 'LONG', patterns)
    print(f"\nBase Confidence: {base_conf:.3f}")
    print(f"Calibrated Confidence: {calibrated:.3f}")
    print(f"Should Trade: {agent.should_trade(calibrated)}")


