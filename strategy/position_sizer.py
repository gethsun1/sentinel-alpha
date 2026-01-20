class PositionSizer:
    """
    Determines order size using confidence and agent memory.
    Handles symbol-specific minimum sizes and step sizes for WEEX.
    """
    
    # WEEX minimum order sizes and step sizes per symbol
    # Adjusted for $1000 account with 4x leverage (~$250 per trade max)
    SYMBOL_SPECS = {
        'cmt_btcusdt': {'min_size': 1, 'step_size': 1, 'base_size': 1},
        'cmt_ethusdt': {'min_size': 1, 'step_size': 1, 'base_size': 1},
        'cmt_solusdt': {'min_size': 1, 'step_size': 1, 'base_size': 1},
        'cmt_dogeusdt': {'min_size': 100, 'step_size': 100, 'base_size': 100},
        'cmt_xrpusdt': {'min_size': 10, 'step_size': 10, 'base_size': 10},
        'cmt_adausdt': {'min_size': 10, 'step_size': 10, 'base_size': 10},
        'cmt_bnbusdt': {'min_size': 0.1, 'step_size': 0.1, 'base_size': 0.1},
        'cmt_ltcusdt': {'min_size': 0.1, 'step_size': 0.1, 'base_size': 0.1},
    }

    def __init__(self, base_size=None, max_size=None):
        # Legacy parameters - ignored in favor of symbol-specific sizing
        self.base_size = base_size
        self.max_size = max_size

    def size(self, confidence: float, adaptive_factor: float, symbol: str = 'cmt_btcusdt', 
             account_balance: float = 1000.0, max_risk_pct: float = 2.0) -> float:
        """
        Calculate position size based on:
        - Symbol-specific minimums and step sizes
        - Confidence level
        - Account balance and risk percentage
        - Adaptive learning factor
        """
        # Get symbol specifications
        spec = self.SYMBOL_SPECS.get(symbol, self.SYMBOL_SPECS['cmt_btcusdt'])
        
        # Calculate max risk amount in USD
        max_risk_usd = account_balance * (max_risk_pct / 100.0)
        
        # Scale base size by confidence and adaptive factor (more conservative)
        # Confidence range: 0.5-1.0, adaptive_factor typically 0.8-1.2
        # Use much more conservative scaling for small account
        confidence_multiplier = 1.0 + (confidence - 0.5)  # 1.0 to 1.5 range
        size_raw = spec['base_size'] * confidence_multiplier * adaptive_factor
        
        # Round to step size
        step = spec['step_size']
        size_rounded = round(size_raw / step) * step
        
        # Ensure minimum size
        size_final = max(size_rounded, spec['min_size'])
        
        # Safety cap: Use minimum sizes only for now
        # This ensures we don't exceed account margin
        size_final = spec['min_size']
        
        return size_final
