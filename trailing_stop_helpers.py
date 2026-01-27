    def get_profit_lock_tier(self, roi_pct: float) -> int:
        """
        Map ROI percentage to profit lock tier.
        
        Args:
            roi_pct: Current unrealized ROI percentage
            
        Returns:
            Tier level (0-5)
        """
        if roi_pct >= 25:
            return 5  # Lock 8% profit
        elif roi_pct >= 20:
            return 4  # Lock 5% profit
        elif roi_pct >= 15:
            return 3  # Lock 3% profit
        elif roi_pct >= 10:
            return 2  # Lock 1% profit
        elif roi_pct >= 5:
            return 1  # Breakeven (0%)
        else:
            return 0  # No protection yet
    
    def get_sl_profit_for_tier(self, tier: int) -> float:
        """
        Return locked profit percentage for each tier.
        
        Args:
            tier: Tier level (0-5)
            
        Returns:
            Profit percentage to lock
        """
        tier_map = {
            0: None,  # Original SL (no lock)
            1: 0.0,   # Breakeven
            2: 1.0,   # +1%
            3: 3.0,   # +3%
            4: 5.0,   # +5%
            5: 8.0    # +8%
        }
        return tier_map.get(tier, 0.0)
    
    def calculate_roi_pct(self, entry_price: float, current_price: float, direction: str) -> float:
        """
        Calculate current unrealized ROI percentage.
        
        Args:
            entry_price: Position entry price
            current_price: Current market price
            direction: 'LONG' or 'SHORT'
            
        Returns:
            ROI percentage (positive = profit, negative = loss)
        """
        if direction == 'LONG':
            return ((current_price - entry_price) / entry_price) * 100
        else:  # SHORT
            return ((entry_price - current_price) / entry_price) * 100
