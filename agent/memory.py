from collections import deque
import numpy as np

class AgentMemory:
    """
    Short-horizon adaptive memory for Sentinel Alpha.
    Stores recent outcomes to modulate risk and sizing.
    """

    def __init__(self, max_steps=50):
        self.recent_pnls = deque(maxlen=max_steps)
        self.recent_confidences = deque(maxlen=max_steps)

    def record(self, pnl: float, confidence: float):
        self.recent_pnls.append(pnl)
        self.recent_confidences.append(confidence)

    def performance_score(self) -> float:
        if not self.recent_pnls:
            return 1.0
        return np.tanh(np.mean(self.recent_pnls))

    def confidence_alignment(self) -> float:
        if not self.recent_confidences:
            return 1.0
        return np.mean(self.recent_confidences)

    def adaptive_factor(self) -> float:
        """
        Combines performance and confidence alignment.
        Output bounded between 0.5 and 1.5
        """
        factor = self.performance_score() * self.confidence_alignment()
        return float(np.clip(factor, 0.5, 1.5))
