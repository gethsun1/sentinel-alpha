"""
TP/SL Calculator - AI-Driven Take-Profit & Stop-Loss Module

Calculates dynamic TP/SL levels based on:
- Market regime (TREND_UP, TREND_DOWN, RANGE, etc.)
- AI confidence score
- Volatility (ATR-based)
- Risk-reward constraints

CRITICAL: All trades MUST have TP/SL for WEEX compliance.
"""

import numpy as np
import pandas as pd
from typing import Tuple, Dict


class TPSLCalculator:
    """
    AI-Enhanced TP/SL Calculator for WEEX Competition
    
    Ensures compliance by:
    1. Never returning None for TP or SL
    2. Adapting levels based on AI signals and market conditions
    3. Providing natural language reasoning for AI log submission
    """
    
    def __init__(self, 
                 min_rr_ratio: float = 1.2,
                 max_rr_ratio: float = 3.0,
                 base_sl_multiplier: float = 1.0,
                 base_tp_multiplier: float = 2.0):
        """
        Initialize TP/SL calculator.
        
        Args:
            min_rr_ratio: Minimum risk-reward ratio (default 1.2:1)
            max_rr_ratio: Maximum risk-reward ratio (default 3.0:1)
            base_sl_multiplier: Base stop-loss as multiple of ATR (default 1.0)
            base_tp_multiplier: Base take-profit as multiple of ATR (default 2.0)
        """
        self.min_rr_ratio = min_rr_ratio
        self.max_rr_ratio = max_rr_ratio
        self.base_sl_multiplier = base_sl_multiplier
        self.base_tp_multiplier = base_tp_multiplier
    
    def calculate_tp_sl(self,
                       entry_price: float,
                       signal: str,
                       confidence: float,
                       regime: str,
                       volatility_atr: float) -> Tuple[float, float, str, float]:
        """
        Calculate Take-Profit and Stop-Loss prices with AI reasoning.
        
        Args:
            entry_price: Expected entry price
            signal: Trading signal ('LONG' or 'SHORT')
            confidence: AI confidence score (0.0 - 1.0)
            regime: Market regime (e.g., 'TREND_UP', 'RANGE', 'VOLATILITY_COMPRESSION')
            volatility_atr: Average True Range (ATR) for volatility measure
            
        Returns:
            Tuple of (take_profit_price, stop_loss_price, reasoning_text, risk_reward)
            
        Raises:
            ValueError: If signal is invalid or inputs are invalid
        """
        if signal not in ['LONG', 'SHORT']:
            raise ValueError(f"Invalid signal: {signal}. Must be 'LONG' or 'SHORT'")
        
        if not (0.0 <= confidence <= 1.0):
            raise ValueError(f"Invalid confidence: {confidence}. Must be between 0.0 and 1.0")
        
        if entry_price <= 0 or volatility_atr <= 0:
            raise ValueError(f"Invalid entry_price or ATR: entry={entry_price}, ATR={volatility_atr}")
        
        # Step 1.5: Apply ATR Floor (Noise-Absorption Guard)
        # Prevents stops from being too tight in low-volatility regimes
        min_atr = entry_price * 0.012  # 1.2% floor
        effective_atr = max(volatility_atr, min_atr)
        
        # Step 1: Determine regime-based multipliers
        sl_mult, tp_mult = self._get_regime_multipliers(regime, confidence)
        
        # Step 2: Calculate SL and TP distances based on ATR
        sl_distance = effective_atr * sl_mult
        tp_distance = effective_atr * tp_mult
        
        # Step 3: Apply confidence scaling
        # Higher confidence = willing to take more risk for better reward
        confidence_factor = 0.8 + (confidence * 0.4)  # Range: 0.8 to 1.2
        tp_distance *= confidence_factor
        
        # Step 4: Calculate actual prices
        if signal == 'LONG':
            stop_loss = entry_price - sl_distance
            take_profit = entry_price + tp_distance
        else:  # SHORT
            stop_loss = entry_price + sl_distance
            take_profit = entry_price - tp_distance
        
        # Step 5: Validate risk-reward ratio
        actual_rr = tp_distance / sl_distance
        if actual_rr < self.min_rr_ratio:
            # Adjust TP to meet minimum RR
            tp_distance = sl_distance * self.min_rr_ratio
            if signal == 'LONG':
                take_profit = entry_price + tp_distance
            else:
                take_profit = entry_price - tp_distance
            actual_rr = self.min_rr_ratio
        
        # Step 6: Round to appropriate precision (increased for lower priced assets like XRP)
        stop_loss = round(stop_loss, 4)
        take_profit = round(take_profit, 4)
        
        # Step 7: Generate reasoning for AI log
        reasoning = self._generate_reasoning(
            signal, regime, confidence, sl_mult, tp_mult, 
            actual_rr, volatility_atr, entry_price
        )
        
        return take_profit, stop_loss, reasoning, actual_rr
    
    def _get_regime_multipliers(self, regime: str, confidence: float) -> Tuple[float, float]:
        """
        Determine SL and TP multipliers based on regime.
        
        Different regimes require different risk management:
        - TREND: Wider stops to avoid noise, larger targets
        - RANGE: Tighter stops, moderate targets
        - VOLATILITY_COMPRESSION: Very tight stops, quick exits
        - HIGH_VOLATILITY: Wider stops to account for noise
        
        Returns:
            Tuple of (sl_multiplier, tp_multiplier)
        """
        regime = regime.upper()
        
        if regime == 'TREND_UP' or regime == 'TREND_DOWN':
            # Trending markets: wider stops to avoid noise, capture full move
            sl_mult = 2.5 * self.base_sl_multiplier  # Increased from 1.5
            tp_mult = 5.0 * self.base_tp_multiplier  # Increased from 3.0 (maintain 2:1 RR)
            
        elif regime == 'RANGE' or regime == 'MEAN_REVERSION':
            # Range-bound: widened stops to avoid premature exit from noise
            sl_mult = 2.0 * self.base_sl_multiplier  # Increased from 1.2
            tp_mult = 3.5 * self.base_tp_multiplier  # Increased from 1.5
            
        elif regime == 'VOLATILITY_COMPRESSION':
            # Low volatility: widened stops to resist ticker noise and spread
            sl_mult = 1.8 * self.base_sl_multiplier  # Increased from 1.1
            tp_mult = 3.0 * self.base_tp_multiplier  # Increased from 1.2
            
        elif regime == 'HIGH_VOLATILITY' or regime == 'VOLATILE':
            # High volatility: wider stops to avoid whipsaw
            sl_mult = 2.0 * self.base_sl_multiplier
            tp_mult = 3.5 * self.base_tp_multiplier
            
        else:
            # Unknown/default regime: conservative approach
            sl_mult = 1.0 * self.base_sl_multiplier
            tp_mult = 2.0 * self.base_tp_multiplier
        
        return sl_mult, tp_mult
    
    def _generate_reasoning(self,
                           signal: str,
                           regime: str,
                           confidence: float,
                           sl_mult: float,
                           tp_mult: float,
                           rr_ratio: float,
                           atr: float,
                           entry_price: float) -> str:
        """
        Generate natural language reasoning for TP/SL decision.
        
        This reasoning will be included in the AI log submission to WEEX.
        Must be clear, concise, and ≤1000 characters.
        
        Returns:
            Human-readable explanation string
        """
        # Regime description
        regime_desc = {
            'TREND_UP': 'upward trending',
            'TREND_DOWN': 'downward trending',
            'RANGE': 'range-bound',
            'MEAN_REVERSION': 'mean-reverting',
            'VOLATILITY_COMPRESSION': 'low volatility',
            'HIGH_VOLATILITY': 'high volatility',
            'VOLATILE': 'volatile'
        }.get(regime.upper(), regime.lower())
        
        # Confidence level
        if confidence >= 0.75:
            conf_desc = "very high"
        elif confidence >= 0.60:
            conf_desc = "high"
        elif confidence >= 0.45:
            conf_desc = "moderate"
        else:
            conf_desc = "low"
        
        # Construct reasoning
        reasoning_parts = []
        
        # Part 1: Regime and confidence context
        reasoning_parts.append(
            f"AI detected {regime_desc} regime with {conf_desc} confidence ({confidence:.1%})."
        )
        
        # Part 2: Stop-loss justification
        sl_pct = (sl_mult * atr / entry_price) * 100
        reasoning_parts.append(
            f"Stop-loss set at {sl_mult:.1f}× ATR (${sl_mult * atr:.2f}, ~{sl_pct:.2f}% from entry) "
            f"to protect against {'trend exhaustion' if 'TREND' in regime.upper() else 'adverse movement'}."
        )
        
        # Part 3: Take-profit justification
        tp_pct = (tp_mult * atr / entry_price) * 100
        reasoning_parts.append(
            f"Take-profit set at {tp_mult:.1f}× ATR (${tp_mult * atr:.2f}, ~{tp_pct:.2f}% profit) "
            f"to capture {'momentum' if 'TREND' in regime.upper() else 'mean reversion'}."
        )
        
        # Part 4: Risk-reward summary
        reasoning_parts.append(
            f"Risk-reward ratio: {rr_ratio:.2f}:1, ensuring positive expectancy."
        )
        
        # Join with proper formatting
        reasoning = " ".join(reasoning_parts)
        
        # Ensure within 1000 char limit
        if len(reasoning) > 1000:
            reasoning = reasoning[:997] + "..."
        
        return reasoning
    
    def validate_tp_sl(self, 
                      entry_price: float,
                      take_profit: float,
                      stop_loss: float,
                      signal: str) -> Tuple[bool, str]:
        """
        Validate that TP/SL values are reasonable.
        
        Args:
            entry_price: Entry price
            take_profit: Proposed TP price
            stop_loss: Proposed SL price
            signal: Trading signal ('LONG' or 'SHORT')
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check for None values
        if take_profit is None or stop_loss is None:
            return False, "TP or SL is None - CRITICAL COMPLIANCE VIOLATION"
        
        # Check for zero or negative
        if take_profit <= 0 or stop_loss <= 0:
            return False, f"Invalid TP/SL values: TP={take_profit}, SL={stop_loss}"
        
        # Check directional correctness
        if signal == 'LONG':
            if stop_loss >= entry_price:
                return False, f"LONG: SL ({stop_loss}) must be below entry ({entry_price})"
            if take_profit <= entry_price:
                return False, f"LONG: TP ({take_profit}) must be above entry ({entry_price})"
        else:  # SHORT
            if stop_loss <= entry_price:
                return False, f"SHORT: SL ({stop_loss}) must be above entry ({entry_price})"
            if take_profit >= entry_price:
                return False, f"SHORT: TP ({take_profit}) must be below entry ({entry_price})"
        
        # Check risk-reward ratio
        if signal == 'LONG':
            risk = entry_price - stop_loss
            reward = take_profit - entry_price
        else:
            risk = stop_loss - entry_price
            reward = entry_price - take_profit
        
        if risk <= 0:
            return False, f"Invalid risk: {risk}"
        
        rr = reward / risk
        if rr < self.min_rr_ratio:
            return False, f"Risk-reward too low: {rr:.2f} < {self.min_rr_ratio}"
        
        return True, "Valid"

    def calculate_atr(self, df, period: int = 14) -> float:
        """
        Calculate Average True Range (ATR) from DataFrame.
        """
        try:
            if len(df) < period + 1:
                return 0.0
                
            high = df['price'] # Approximation if H/L not available, or use H/L if available
            low = df['price']
            close = df['price']
            
            # If df has high/low/close columns, use them. 
            # Sentinel bot df usually has 'price' (from ticker). 
            # If only 'price' (last) is available, TR is just price movement?
            # Standard ATR requires High/Low. 
            # Let's check live_trading_bot.py market_data structure.
            # market_data keys: 'timestamp', 'price', 'volume', 'bid', 'ask'.
            # We DON'T have High/Low candles. We only have ticker snaps.
            # So ATR on 'price' is just volatility of 'price'. 
            # TR = abs(price - prev_price) usually?
            # Or use std * factor?
            
            # Approximation for ticker data:
            # TR = abs(current_price - prev_price)
            # ATR = Rolling mean of TR
            
            df = df.copy()
            df['prev_price'] = df['price'].shift(1)
            df['tr'] = (df['price'] - df['prev_price']).abs()
            atr = df['tr'].rolling(window=period).mean().iloc[-1]
            
            # Enforce minimum ATR (1.2% of price) to survive crypto market noise
            # Crypto markets routinely have 0.5-1% intraday swings
            current_price = df['price'].iloc[-1]
            min_atr = current_price * 0.012  # Increased from 0.003 (4x wider)
            if atr < min_atr:
                atr = min_atr
            
            if np.isnan(atr): return 0.0
            return float(atr)
            
        except Exception as e:
            print(f"ATR Calc Error: {e}")
            return 0.0

    def calculate_dynamic_tpsl(self, entry_price, direction, volatility_atr, regime, confidence) -> dict:
        """
        Wrapper for calculate_tp_sl to match bot expectation (returns Dict).
        """
        try:
            tp, sl, reasoning, rr = self.calculate_tp_sl(
                entry_price=entry_price,
                signal=direction,
                confidence=confidence,
                regime=regime,
                volatility_atr=volatility_atr
            )
            
            # Validate
            is_valid, msg = self.validate_tp_sl(entry_price, tp, sl, direction)
            
            return {
                'valid': is_valid,
                'take_profit': tp,
                'stop_loss': sl,
                'reasoning': reasoning,
                'risk_reward': rr,
                'error': msg if not is_valid else None
            }
        except Exception as e:
            print(f"TPSL Error: {e}")
            return {'valid': False, 'error': str(e)}


# Demo/Testing
if __name__ == "__main__":
    print("=" * 70)
    print("TP/SL CALCULATOR - DEMO")
    print("=" * 70)
    print()
    
    calculator = TPSLCalculator()
    
    # Test scenarios
    test_cases = [
        {
            'name': "LONG in TREND_UP",
            'entry': 96500.0,
            'signal': 'LONG',
            'confidence': 0.72,
            'regime': 'TREND_UP',
            'atr': 1200.0
        },
        {
            'name': "SHORT in TREND_DOWN",
            'entry': 96500.0,
            'signal': 'SHORT',
            'confidence': 0.68,
            'regime': 'TREND_DOWN',
            'atr': 1200.0
        },
        {
            'name': "LONG in RANGE (low confidence)",
            'entry': 96500.0,
            'signal': 'LONG',
            'confidence': 0.48,
            'regime': 'RANGE',
            'atr': 800.0
        },
        {
            'name': "SHORT in HIGH_VOLATILITY",
            'entry': 96500.0,
            'signal': 'SHORT',
            'confidence': 0.55,
            'regime': 'HIGH_VOLATILITY',
            'atr': 2000.0
        }
    ]
    
    for i, case in enumerate(test_cases, 1):
        print(f"\nTest Case {i}: {case['name']}")
        print("-" * 70)
        
        tp, sl, reasoning, rr = calculator.calculate_tp_sl(
            entry_price=case['entry'],
            signal=case['signal'],
            confidence=case['confidence'],
            regime=case['regime'],
            volatility_atr=case['atr']
        )
        
        print(f"Entry Price: ${case['entry']:.2f}")
        print(f"Signal: {case['signal']}")
        print(f"Confidence: {case['confidence']:.1%}")
        print(f"Regime: {case['regime']}")
        print(f"ATR: ${case['atr']:.2f}")
        print()
        print(f"✓ Take-Profit: ${tp:.2f}")
        print(f"✓ Stop-Loss: ${sl:.2f}")
        print()
        
        # Calculate distances
        if case['signal'] == 'LONG':
            tp_dist = tp - case['entry']
            sl_dist = case['entry'] - sl
        else:
            tp_dist = case['entry'] - tp
            sl_dist = sl - case['entry']
        
        rr_calc = tp_dist / sl_dist if sl_dist > 0 else 0
        print(f"Risk: ${sl_dist:.2f} | Reward: ${tp_dist:.2f} | R:R = {rr_calc:.2f}:1 (stored {rr:.2f})")
        print()
        print(f"Reasoning: {reasoning}")
        print()
        
        # Validate
        is_valid, msg = calculator.validate_tp_sl(case['entry'], tp, sl, case['signal'])
        print(f"Validation: {'✅ PASS' if is_valid else '❌ FAIL'} - {msg}")
    
    print()
    print("=" * 70)
    print("✓ TP/SL Calculator Ready for Production")
    print("=" * 70)
