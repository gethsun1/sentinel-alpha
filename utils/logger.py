import json
import time
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional

class JsonLogger:
    def __init__(self, filepath: str):
        self.path = Path(filepath)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, event: dict):
        event["timestamp"] = int(time.time() * 1000)
        with self.path.open("a") as f:
            f.write(json.dumps(event) + "\n")


def get_learning_state_hash(agent_stats: Dict) -> str:
    """
    Generate hash of learning agent state for audit trail.
    
    Args:
        agent_stats: Statistics dict from AdaptiveLearningAgent.get_stats()
        
    Returns:
        SHA256 hash of state (first 16 chars)
    """
    # Create deterministic string representation of state
    state_str = json.dumps(agent_stats, sort_keys=True)
    hash_obj = hashlib.sha256(state_str.encode())
    return hash_obj.hexdigest()[:16]


def log_signal(
    logger: JsonLogger,
    pair: str,
    price: float,
    signal: str,
    confidence: float,
    regime: str,
    regime_probabilities: Optional[Dict] = None,
    learning_state_hash: Optional[str] = None,
    llm_reasoning: Optional[str] = None,
    reasoning: str = "",
    **extra_fields
):
    """
    Log trading signal with all required competition fields.
    
    Args:
        logger: JsonLogger instance
        pair: Trading pair symbol
        price: Current price
        signal: Trading signal (LONG/SHORT/NO-TRADE)
        confidence: Confidence score
        regime: Market regime
        regime_probabilities: Dict of regime probabilities
        learning_state_hash: Hash of adaptive learning state
        llm_reasoning: LLM-generated reasoning
        reasoning: Human-readable reasoning
        **extra_fields: Additional fields to include
    """
    event = {
        'pair': pair,
        'price': float(price),
        'signal': signal,
        'confidence': float(confidence),
        'regime': regime,
        'regime_probabilities': regime_probabilities or {regime: 1.0},
        'learning_state_hash': learning_state_hash or 'N/A',
        'llm_reasoning': llm_reasoning or 'LLM disabled',
        'reasoning': reasoning,
        **extra_fields
    }
    logger.log(event)


def log_trade(
    logger: JsonLogger,
    pair: str,
    signal: str,
    confidence: float,
    size: float,
    price: float,
    order_id: str,
    position_sizing_rationale: str,
    risk_filter_result: str = "PASSED",
    llm_reasoning: Optional[str] = None,
    forced: bool = False,
    **extra_fields
):
    """
    Log trade execution with position sizing rationale.
    
    Args:
        logger: JsonLogger instance
        pair: Trading pair symbol
        signal: Trading signal (LONG/SHORT)
        confidence: Signal confidence
        size: Position size
        price: Execution price
        order_id: Exchange order ID
        position_sizing_rationale: Explanation of position size calculation
        risk_filter_result: Risk filter outcome (PASSED/REJECTED)
        llm_reasoning: LLM-generated reasoning
        forced: Whether this was a forced trade
        **extra_fields: Additional fields
    """
    event = {
        'pair': pair,
        'signal': signal,
        'confidence': float(confidence),
        'size': float(size),
        'price': float(price),
        'order_id': order_id,
        'position_sizing_rationale': position_sizing_rationale,
        'risk_filter_result': risk_filter_result,
        'llm_reasoning': llm_reasoning or 'LLM disabled',
        'forced': forced,
        **extra_fields
    }
    logger.log(event)
