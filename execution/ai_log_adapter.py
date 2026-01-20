"""
AI Log Adapter - WEEX Competition Compliance

Submits AI decision logs to WEEX /capi/v2/order/uploadAiLog endpoint.
CRITICAL: Required for competition compliance - trades without AI logs = disqualification.

Handles:
- Log formatting per WEEX requirements
- Retry logic with exponential backoff
- Error handling and fallback logging
- TP/SL reasoning integration
"""

import time
import hmac
import hashlib
import base64
import json
import requests
from typing import Dict, Optional, Any
from pathlib import Path
from datetime import datetime, timezone


class AILogAdapter:
    """
    WEEX AI Log Submission Adapter
    
    Submits AI decision logs for competition compliance.
    Must be called for every trade to avoid disqualification.
    """
    
    BASE_URL = "https://api-contract.weex.com"
    UPLOAD_ENDPOINT = "/capi/v2/order/uploadAiLog"
    MAX_RETRIES = 3
    RETRY_DELAY = 2  # seconds
    MAX_EXPLANATION_LENGTH = 1000  # WEEX limit
    
    def __init__(self,
                 api_key: str,
                 secret_key: str,
                 passphrase: str,
                 log_file: str = "logs/ai_logs_submitted.jsonl",
                 dry_run: bool = False):
        """
        Initialize AI log adapter.
        
        Args:
            api_key: WEEX API key
            secret_key: WEEX secret key
            passphrase: WEEX passphrase
            log_file: Local file to log submission attempts
            dry_run: If True, simulate submission without API call
        """
        self.api_key = api_key
        self.secret_key = secret_key
        self.passphrase = passphrase
        self.dry_run = dry_run
        self.log_file = Path(log_file)
        
        # Create log directory if needed
        self.log_file.parent.mkdir(exist_ok=True)
        
        # Stats tracking
        self.submissions_attempted = 0
        self.submissions_successful = 0
        self.submissions_failed = 0
    
    def _timestamp(self) -> str:
        """Generate timestamp for API signature"""
        return str(int(time.time() * 1000))
    
    def _sign(self, timestamp: str, method: str, path: str, query: str, body: str) -> str:
        """Generate HMAC signature for WEEX API"""
        message = timestamp + method.upper() + path + query + body
        signature = hmac.new(
            self.secret_key.encode(),
            message.encode(),
            hashlib.sha256
        ).digest()
        return base64.b64encode(signature).decode()
    
    def _headers(self, signature: str, timestamp: str) -> Dict[str, str]:
        """Generate request headers"""
        return {
            "ACCESS-KEY": self.api_key,
            "ACCESS-SIGN": signature,
            "ACCESS-TIMESTAMP": timestamp,
            "ACCESS-PASSPHRASE": self.passphrase,
            "Content-Type": "application/json",
            "locale": "en-US"
        }
    
    def submit_log(self,
                   stage: str,
                   model: str,
                   input_data: Dict[str, Any],
                   output_data: Dict[str, Any],
                   explanation: str,
                   order_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Submit AI log to WEEX endpoint.
        
        Args:
            stage: Trading stage (e.g., "Strategy Generation", "Decision Making")
            model: AI model name (e.g., "LLaMA-2-7B-Q4", "Enhanced-Regime-Classifier")
            input_data: Dict containing AI input (prompt, market data, indicators)
            output_data: Dict containing AI output (signal, confidence, TP/SL, etc.)
            explanation: Natural language explanation (max 1000 chars)
            order_id: Optional order ID if trade was executed
            
        Returns:
            Dict with 'success' (bool), 'response' (API response), 'error' (if failed)
        """
        self.submissions_attempted += 1
        
        # Validate and truncate explanation
        explanation = self._validate_explanation(explanation)
        
        # Construct log payload
        payload = {
            "stage": stage,
            "model": model,
            "input": input_data,
            "output": output_data,
            "explanation": explanation
        }
        
        # Add order ID if provided
        if order_id:
            payload["orderId"] = order_id
        
        # Log locally first (for audit trail)
        self._log_locally(payload, order_id)
        
        # Submit to WEEX API (with retries)
        if self.dry_run:
            result = self._simulate_submission(payload)
        else:
            result = self._submit_with_retries(payload)
        
        # Update stats
        if result.get('success'):
            self.submissions_successful += 1
        else:
            self.submissions_failed += 1
        
        return result
    
    def _validate_explanation(self, explanation: str) -> str:
        """
        Validate and truncate explanation to WEEX limits.
        
        Args:
            explanation: Raw explanation text
            
        Returns:
            Validated explanation (max 1000 chars)
        """
        if not explanation:
            explanation = "AI-driven trade decision"
        
        # Truncate if too long
        if len(explanation) > self.MAX_EXPLANATION_LENGTH:
            explanation = explanation[:self.MAX_EXPLANATION_LENGTH - 3] + "..."
        
        return explanation
    
    def _log_locally(self, payload: Dict, order_id: Optional[str]):
        """Log submission attempt to local file"""
        try:
            log_entry = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'order_id': order_id,
                'stage': payload['stage'],
                'model': payload['model'],
                'payload': payload
            }
            
            with open(self.log_file, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
        
        except Exception as e:
            print(f"⚠️  Failed to log locally: {e}")
    
    def _submit_with_retries(self, payload: Dict) -> Dict[str, Any]:
        """
        Submit log to WEEX API with retry logic.
        
        Args:
            payload: AI log payload
            
        Returns:
            Dict with 'success', 'response', and optional 'error'
        """
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                # Generate signature
                ts = self._timestamp()
                body_json = json.dumps(payload)
                signature = self._sign(ts, "POST", self.UPLOAD_ENDPOINT, "", body_json)
                
                # Make request
                response = requests.post(
                    self.BASE_URL + self.UPLOAD_ENDPOINT,
                    headers=self._headers(signature, ts),
                    data=body_json,
                    timeout=10
                )
                
                # Parse response
                response_data = response.json()
                
                # Check success
                if response.status_code == 200 and response_data.get('code') == '00000':
                    return {
                        'success': True,
                        'response': response_data,
                        'attempt': attempt
                    }
                else:
                    error_msg = response_data.get('msg', 'Unknown error')
                    print(f"⚠️  AI log submission failed (attempt {attempt}/{self.MAX_RETRIES}): {error_msg}")
                    
                    if attempt < self.MAX_RETRIES:
                        time.sleep(self.RETRY_DELAY * attempt)  # Exponential backoff
                    else:
                        return {
                            'success': False,
                            'error': error_msg,
                            'response': response_data,
                            'attempts': attempt
                        }
            
            except Exception as e:
                print(f"❌ AI log submission error (attempt {attempt}/{self.MAX_RETRIES}): {e}")
                
                if attempt < self.MAX_RETRIES:
                    time.sleep(self.RETRY_DELAY * attempt)
                else:
                    return {
                        'success': False,
                        'error': str(e),
                        'attempts': attempt
                    }
        
        return {
            'success': False,
            'error': 'Max retries exceeded',
            'attempts': self.MAX_RETRIES
        }
    
    def _simulate_submission(self, payload: Dict) -> Dict[str, Any]:
        """Simulate submission in dry-run mode"""
        print(f"[DRY RUN] Would submit AI log:")
        print(f"  Stage: {payload['stage']}")
        print(f"  Model: {payload['model']}")
        print(f"  Input keys: {list(payload['input'].keys())}")
        print(f"  Output keys: {list(payload['output'].keys())}")
        print(f"  Explanation length: {len(payload['explanation'])} chars")
        
        return {
            'success': True,
            'response': {'code': '00000', 'msg': 'DRY_RUN_SUCCESS', 'data': 'upload success'},
            'dry_run': True
        }
    
    def get_stats(self) -> Dict[str, int]:
        """Get submission statistics"""
        return {
            'attempted': self.submissions_attempted,
            'successful': self.submissions_successful,
            'failed': self.submissions_failed,
            'success_rate': (
                self.submissions_successful / self.submissions_attempted 
                if self.submissions_attempted > 0 else 0.0
            )
        }


# Demo/Testing
if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    
    print("=" * 70)
    print("AI LOG ADAPTER - DEMO")
    print("=" * 70)
    print()
    
    # Load credentials
    load_dotenv()
    
    adapter = AILogAdapter(
        api_key=os.getenv("WEEX_API_KEY"),
        secret_key=os.getenv("WEEX_SECRET_KEY"),
        passphrase=os.getenv("WEEX_PASSPHRASE"),
        dry_run=True  # Set to False to test real submission
    )
    
    # Test Case 1: Strategy Generation
    print("Test Case 1: Strategy Generation Log")
    print("-" * 70)
    
    result = adapter.submit_log(
        stage="Strategy Generation",
        model="Enhanced-Regime-Classifier-v2",
        input_data={
            "prompt": "Analyze BTC/USDT market regime and generate trading recommendation",
            "market_data": {
                "price": 96500.0,
                "rsi_14": 58.3,
                "ema_20": 95800.0,
                "atr_14": 1200.0,
                "volume_24h": 25000.0
            },
            "regime_indicators": {
                "trend_strength": 0.65,
                "volatility": 0.012,
                "momentum": 0.003
            }
        },
        output_data={
            "signal": "LONG",
            "confidence": 0.72,
            "regime": "TREND_UP",
            "target_price": 99500.0,
            "stop_loss": 94700.0,
            "position_size": 0.0005
        },
        explanation=(
            "AI detected upward trending regime with high confidence (72%). "
            "Strong momentum (0.003) and positive trend strength (0.65) indicate continuation. "
            "RSI at 58.3 shows room for upside without overbought conditions. "
            "Stop-loss set at 1.5× ATR ($1800 below entry) to protect against trend exhaustion. "
            "Take-profit at $99,500 captures momentum with 4.35:1 risk-reward ratio."
        )
    )
    
    print(f"Result: {'✅ SUCCESS' if result['success'] else '❌ FAILED'}")
    if result.get('error'):
        print(f"Error: {result['error']}")
    print()
    
    # Test Case 2: Decision Making (with order ID)
    print("Test Case 2: Decision Making Log (Post-Trade)")
    print("-" * 70)
    
    result = adapter.submit_log(
        stage="Decision Making",
        model="LLaMA-2-7B-Q4",
        input_data={
            "regime": "RANGE",
            "confidence": 0.48,
            "market_volatility": 0.008,
            "recent_pnl": -50.0,
            "position_count": 1
        },
        output_data={
            "decision": "EXECUTE",
            "signal": "SHORT",
            "entry_price": 96500.0,
            "take_profit": 95100.0,
            "stop_loss": 97140.0,
            "size": 0.0002,
            "risk_reward": 2.19
        },
        explanation=(
            "AI confirmed SHORT signal in range-bound regime. "
            "Moderate confidence (48%) acceptable due to tight 0.8× ATR stop-loss. "
            "Mean-reversion strategy with 2.19:1 RR. Risk managed at $640 exposure."
        ),
        order_id="sentinel-1736784000"
    )
    
    print(f"Result: {'✅ SUCCESS' if result['success'] else '❌ FAILED'}")
    if result.get('error'):
        print(f"Error: {result['error']}")
    print()
    
    # Print stats
    print("Submission Statistics:")
    print("-" * 70)
    stats = adapter.get_stats()
    print(f"Attempted: {stats['attempted']}")
    print(f"Successful: {stats['successful']}")
    print(f"Failed: {stats['failed']}")
    print(f"Success Rate: {stats['success_rate']:.1%}")
    print()
    
    print("=" * 70)
    print("✓ AI Log Adapter Ready for Production")
    print("=" * 70)
