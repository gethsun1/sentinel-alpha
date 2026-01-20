#!/usr/bin/env python3
"""
LLM Inference Test Script

Tests LLaMA-2-7B model loading and inference performance.
"""

import time
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.model_config import ModelConfig
from models.llm_integration import LLMIntegration


def test_model_config():
    """Test model configuration"""
    print("="*70)
    print("TESTING MODEL CONFIGURATION")
    print("="*70)
    
    try:
        config = ModelConfig()
        print(f"\n✅ Config loaded successfully")
        print(f"  LLM Enabled: {config.llm_enabled}")
        print(f"  Model Path: {config.llm_full_path}")
        print(f"  Fallback Mode: {config.llm_fallback_mode}")
        print(f"  Threads: {config.llm_n_threads}")
        print(f"  Context: {config.llm_n_ctx}")
        
        is_valid, message = config.validate_model_exists()
        print(f"\n  Validation: {message}")
        
        if not is_valid:
            print(f"\n❌ Model validation failed!")
            print(f"   Please ensure model file exists at: {config.llm_full_path}")
            return False
        
        return True
        
    except Exception as e:
        print(f"\n❌ Config test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_llm_loading():
    """Test LLM model loading"""
    print("\n" + "="*70)
    print("TESTING LLM MODEL LOADING")
    print("="*70)
    
    try:
        llm = LLMIntegration()
        status = llm.get_status()
        
        print(f"\n  Enabled: {status['enabled']}")
        print(f"  Loaded: {status['loaded']}")
        print(f"  Load Failed: {status['load_failed']}")
        print(f"  Fallback Mode: {status['fallback_mode']}")
        
        if not status['enabled']:
            print(f"\n⚠️  LLM is disabled in config")
            print(f"   To enable: Set llm_enabled: true in competition.yaml")
            return True  # Not an error, just disabled
        
        if status['load_failed']:
            print(f"\n❌ LLM failed to load!")
            return False
        
        if not status['loaded']:
            print(f"\n❌ LLM not loaded!")
            return False
        
        print(f"\n✅ LLM loaded successfully")
        return True
        
    except Exception as e:
        print(f"\n❌ LLM loading test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_basic_inference(llm):
    """Test basic inference"""
    print("\n" + "="*70)
    print("TESTING BASIC INFERENCE")
    print("="*70)
    
    if not llm.enabled:
        print("\n⚠️  LLM disabled, skipping inference test")
        return True
    
    try:
        prompt = "What is 2 + 2? Answer briefly:"
        
        print(f"\nPrompt: {prompt}")
        print("Generating response...")
        
        start_time = time.time()
        response = llm._generate(prompt, max_tokens=20, temperature=0.1)
        elapsed = time.time() - start_time
        
        print(f"\nResponse: {response}")
        print(f"Inference Time: {elapsed:.2f}s")
        
        if elapsed > 5.0:
            print(f"\n⚠️  WARNING: Inference took >{elapsed:.1f}s (target: <5s)")
            print("   Consider reducing n_threads or using faster hardware")
        else:
            print(f"\n✅ Inference performance acceptable ({elapsed:.2f}s)")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Basic inference test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_trading_inference(llm):
    """Test trading-specific inference"""
    print("\n" + "="*70)
    print("TESTING TRADING-SPECIFIC INFERENCE")
    print("="*70)
    
    if not llm.enabled:
        print("\n⚠️  LLM disabled, skipping trading inference test")
        return True
    
    try:
        # Test regime interpretation
        print("\n1. Testing Regime Interpretation:")
        market_data = {
            'price': 96500.0,
            'momentum': 0.0025,
            'volatility': 0.018
        }
        
        start_time = time.time()
        result = llm.interpret_regime('TREND_UP', market_data)
        elapsed = time.time() - start_time
        
        print(f"   Result: {result}")
        print(f"   Time: {elapsed:.2f}s")
        
        # Test confidence calibration
        print("\n2. Testing Confidence Calibration:")
        patterns = {
            'momentum_strength': 0.7,
            'continuation_probability': 0.65
        }
        
        start_time = time.time()
        result = llm.calibrate_confidence(0.68, 'TREND_UP', 'LONG', patterns)
        elapsed = time.time() - start_time
        
        print(f"   Reasoning: {result['reasoning']}")
        print(f"   Adjustment: {result['adjustment']:+.2%}")
        print(f"   Time: {elapsed:.2f}s")
        
        # Test risk assessment
        print("\n3. Testing Risk Assessment:")
        start_time = time.time()
        result = llm.assess_risk('LONG', market_data, 2)
        elapsed = time.time() - start_time
        
        print(f"   Result: {result}")
        print(f"   Time: {elapsed:.2f}s")
        
        # Test position sizing rationale
        print("\n4. Testing Position Sizing Rationale:")
        start_time = time.time()
        result = llm.explain_position_size(0.68, 'LONG', 1000.0, 0.0002)
        elapsed = time.time() - start_time
        
        print(f"   Result: {result}")
        print(f"   Time: {elapsed:.2f}s")
        
        print(f"\n✅ All trading inference tests passed")
        return True
        
    except Exception as e:
        print(f"\n❌ Trading inference test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all LLM inference tests"""
    print("="*70)
    print("LLaMA-2-7B INFERENCE TEST SUITE")
    print("="*70)
    
    # Test 1: Model Configuration
    if not test_model_config():
        print("\n❌ TEST SUITE FAILED: Config test failed")
        return False
    
    # Test 2: LLM Loading
    if not test_llm_loading():
        print("\n❌ TEST SUITE FAILED: Loading test failed")
        return False
    
    # Create LLM instance for remaining tests
    llm = LLMIntegration()
    
    # Test 3: Basic Inference
    if not test_basic_inference(llm):
        print("\n❌ TEST SUITE FAILED: Basic inference test failed")
        return False
    
    # Test 4: Trading-Specific Inference
    if not test_trading_inference(llm):
        print("\n❌ TEST SUITE FAILED: Trading inference test failed")
        return False
    
    # Summary
    print("\n" + "="*70)
    print("✅ ALL TESTS PASSED")
    print("="*70)
    
    if llm.enabled and llm.llm is not None:
        print("\n🎉 LLaMA model is ready for trading!")
    else:
        print("\n⚠️  LLM is disabled or not loaded")
        print("   Bot will operate without LLM enhancement")
    
    return True


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
