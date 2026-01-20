"""
LLM Integration Module

Wrapper for LLaMA-2-7B model integration into Sentinel Alpha.
Provides AI-enhanced reasoning for trading decisions.
"""

import time
import hashlib
import json
from typing import Dict, Optional, Any
from pathlib import Path


class LLMIntegration:
    """
    LLaMA-2-7B Integration for AI Trading Decisions
    
    Provides enhanced reasoning for:
    - Regime interpretation
    - Confidence calibration
    - Risk assessment
    - Position sizing rationale
    """
    
    def __init__(self, config=None):
        """
        Initialize LLM integration.
        
        Args:
            config: ModelConfig instance. If None, uses get_model_config()
        """
        if config is None:
            from config.model_config import get_model_config
            config = get_model_config()
        
        self.config = config
        self.llm = None
        self.enabled = config.llm_enabled
        self.fallback_mode = config.llm_fallback_mode
        self.load_failed = False
        
        # Try to load model if enabled
        if self.enabled:
            self._load_model()
    
    def _load_model(self):
        """Load LLaMA model with error handling"""
        try:
            # Validate model exists first
            is_valid, message = self.config.validate_model_exists()
            if not is_valid:
                print(f"⚠️  LLM Model Validation Failed: {message}")
                if self.fallback_mode == 'halt':
                    raise RuntimeError(f"LLM required but invalid: {message}")
                self.load_failed = True
                self.enabled = False
                return
            
            # Try to import llama-cpp-python
            try:
                from llama_cpp import Llama
            except ImportError:
                print("⚠️  llama-cpp-python not installed. Install with: pip install llama-cpp-python")
                if self.fallback_mode == 'halt':
                    raise RuntimeError("llama-cpp-python required but not installed")
                self.load_failed = True
                self.enabled = False
                return
            
            # Load model
            print(f"🤖 Loading LLaMA model from {self.config.llm_full_path}...")
            start_time = time.time()
            
            self.llm = Llama(
                model_path=str(self.config.llm_full_path),
                n_ctx=self.config.llm_n_ctx,
                n_threads=self.config.llm_n_threads,
                verbose=False
            )
            
            load_time = time.time() - start_time
            print(f"✅ LLaMA model loaded successfully ({load_time:.2f}s)")
            
        except Exception as e:
            print(f"❌ Failed to load LLM model: {e}")
            if self.fallback_mode == 'halt':
                raise RuntimeError(f"LLM required but failed to load: {e}")
            self.load_failed = True
            self.enabled = False
    
    def _generate(self, prompt: str, max_tokens: int = 100, temperature: float = 0.7) -> str:
        """
        Generate text from LLM with error handling.
        
        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0 - 1.0)
            
        Returns:
            Generated text or empty string on failure
        """
        if not self.enabled or self.llm is None:
            return ""
        
        try:
            response = self.llm(
                prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                stop=["</s>", "\n\n"],
                echo=False
            )
            
            return response['choices'][0]['text'].strip()
        
        except Exception as e:
            print(f"⚠️  LLM inference error: {e}")
            return ""
    
    def interpret_regime(self, regime: str, market_data: Dict) -> str:
        """
        Interpret market regime with LLM reasoning.
        
        Args:
            regime: Detected regime (e.g., 'TREND_UP', 'RANGE', 'VOLATILE')
            market_data: Market data dict with price, volatility, momentum
            
        Returns:
            LLM-generated interpretation
        """
        if not self.enabled:
            return f"Regime: {regime} (LLM disabled)"
        
        prompt = f"""Analyze this market regime for crypto trading:
Regime: {regime}
Price: ${market_data.get('price', 0):.2f}
Momentum: {market_data.get('momentum', 0):.4f}
Volatility: {market_data.get('volatility', 0):.4f}

Provide a brief 1-sentence trading interpretation:"""
        
        interpretation = self._generate(prompt, max_tokens=50, temperature=0.5)
        return interpretation if interpretation else f"{regime} detected"
    
    def calibrate_confidence(
        self,
        base_confidence: float,
        regime: str,
        signal: str,
        patterns: Dict
    ) -> Dict[str, Any]:
        """
        Use LLM to provide reasoning for confidence calibration.
        
        Args:
            base_confidence: Initial confidence score
            regime: Current market regime
            signal: Trading signal (LONG/SHORT/NO-TRADE)
            patterns: Market pattern scores
            
        Returns:
            Dict with 'reasoning' and 'adjustment' (confidence delta)
        """
        if not self.enabled:
            return {
                'reasoning': 'LLM disabled - using base confidence',
                'adjustment': 0.0
            }
        
        momentum_strength = patterns.get('momentum_strength', 0.5)
        continuation_prob = patterns.get('continuation_probability', 0.5)
        
        prompt = f"""Trading decision analysis:
Signal: {signal}
Regime: {regime}
Base Confidence: {base_confidence:.2%}
Momentum: {momentum_strength:.2f}
Continuation Prob: {continuation_prob:.2f}

Should confidence be adjusted? Reply with: INCREASE/DECREASE/MAINTAIN and brief reason:"""
        
        reasoning = self._generate(prompt, max_tokens=60, temperature=0.6)
        
        # Parse adjustment from reasoning
        adjustment = 0.0
        if 'INCREASE' in reasoning.upper():
            adjustment = 0.03
        elif 'DECREASE' in reasoning.upper():
            adjustment = -0.03
        
        return {
            'reasoning': reasoning if reasoning else "Maintained base confidence",
            'adjustment': adjustment
        }
    
    def assess_risk(
        self,
        signal: str,
        market_data: Dict,
        current_positions: int
    ) -> str:
        """
        Generate risk assessment narrative.
        
        Args:
            signal: Proposed trading signal
            market_data: Current market conditions
            current_positions: Number of open positions
            
        Returns:
            Risk assessment summary
        """
        if not self.enabled:
            return f"Risk: {current_positions}/5 positions active"
        
        prompt = f"""Risk assessment for crypto trade:
Signal: {signal}
Open Positions: {current_positions}/5
Volatility: {market_data.get('volatility', 0):.4f}
Momentum: {market_data.get('momentum', 0):.4f}

Brief risk assessment (1 sentence):"""
        
        assessment = self._generate(prompt, max_tokens=40, temperature=0.5)
        return assessment if assessment else "Standard risk parameters apply"
    
    def explain_position_size(
        self,
        confidence: float,
        signal: str,
        account_balance: float,
        proposed_size: float
    ) -> str:
        """
        Generate rationale for position sizing.
        
        Args:
            confidence: Signal confidence
            signal: Trading signal
            account_balance: Current account balance
            proposed_size: Proposed position size
            
        Returns:
            Position sizing rationale
        """
        if not self.enabled:
            return f"Size based on {confidence:.1%} confidence, ${account_balance:.0f} balance"
        
        size_pct = (proposed_size * 50000 / account_balance) * 100  # Rough estimation
        
        prompt = f"""Position sizing justification:
Signal: {signal}
Confidence: {confidence:.1%}
Account: ${account_balance:.0f}
Proposed Size: {proposed_size:.4f} BTC (~{size_pct:.1f}% account)

Brief sizing rationale (1 sentence):"""
        
        rationale = self._generate(prompt, max_tokens=40, temperature=0.5)
        return rationale if rationale else f"Conservative sizing at {confidence:.1%} confidence"
    
    def get_status(self) -> Dict[str, Any]:
        """Get LLM integration status"""
        return {
            'enabled': self.enabled,
            'loaded': self.llm is not None,
            'load_failed': self.load_failed,
            'fallback_mode': self.fallback_mode,
            'model_path': str(self.config.llm_full_path) if self.config else 'N/A'
        }


# Singleton instance
_llm_instance: Optional[LLMIntegration] = None


def get_llm() -> LLMIntegration:
    """Get singleton LLM integration instance"""
    global _llm_instance
    if _llm_instance is None:
        _llm_instance = LLMIntegration()
    return _llm_instance


if __name__ == '__main__':
    # Test LLM integration
    print("Testing LLM Integration...")
    llm = LLMIntegration()
    
    print("\nStatus:")
    print(json.dumps(llm.get_status(), indent=2))
    
    if llm.enabled:
        print("\n" + "="*70)
        print("Testing Regime Interpretation:")
        market_data = {
            'price': 96500.0,
            'momentum': 0.002,
            'volatility': 0.015
        }
        result = llm.interpret_regime('TREND_UP', market_data)
        print(f"Result: {result}")
        
        print("\n" + "="*70)
        print("Testing Confidence Calibration:")
        patterns = {
            'momentum_strength': 0.7,
            'continuation_probability': 0.65
        }
        result = llm.calibrate_confidence(0.68, 'TREND_UP', 'LONG', patterns)
        print(f"Reasoning: {result['reasoning']}")
        print(f"Adjustment: {result['adjustment']:+.2%}")
    else:
        print("\n⚠️  LLM not enabled or failed to load")
        print("To enable: Set llm_enabled: true in competition.yaml")
