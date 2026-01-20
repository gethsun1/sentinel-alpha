class DecisionExplainer:
    """
    Converts internal agent state into human-readable rationale.
    """

    def explain(self, regime, confidence, adaptive_factor, decision):
        return (
            f"Market regime detected as {regime}. "
            f"Signal confidence measured at {confidence:.2f}. "
            f"Adaptive risk factor set to {adaptive_factor:.2f} "
            f"based on recent performance. "
            f"Final decision: {decision}."
        )
