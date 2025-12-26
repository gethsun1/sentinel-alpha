class PositionSizer:
    """
    Determines order size using confidence and agent memory.
    """

    def __init__(self, base_size=0.0001, max_size=0.001):
        self.base_size = base_size
        self.max_size = max_size

    def size(self, confidence: float, adaptive_factor: float) -> float:
        raw = self.base_size * confidence * adaptive_factor
        return round(min(raw, self.max_size), 6)
