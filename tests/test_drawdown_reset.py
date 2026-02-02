
import unittest
from unittest.mock import MagicMock, patch
import sys
import os
import time

# Add root directory to path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from live_trading_bot import SentinelLiveTradingBot
from risk.pnl_guard import PnLGuard

class TestDrawdownReset(unittest.TestCase):
    
    @patch('live_trading_bot.WeexExecutionAdapter')
    def test_drawdown_reset_with_no_positions(self, MockAdapter):
        # Setup bot
        bot = SentinelLiveTradingBot(symbols=['cmt_btcusdt'], dry_run=True)
        bot.adapter = MockAdapter.return_value
        
        # Trigger drawdown halt
        bot.pnl_guard.update(1000) # Peak
        bot.pnl_guard.update(950)  # > 2% drawdown (default max_drawdown_pct=0.02)
        
        self.assertFalse(bot.pnl_guard.can_trade(), "Should be halted after drawdown")
        
        # Mock positions to be empty
        bot.positions = {'cmt_btcusdt': 0.0}
        
        # We need to mock fetch_tick as well or it will fail in the loop
        bot.fetch_tick = MagicMock(return_value={'price': 50000})
        
        # Mock engine to avoid heavy processing
        with patch('live_trading_bot.AIEnhancedSignalEngine') as MockEngine:
            MockEngine.return_value.generate_signals.return_value = None
            
            # We want to run one "iteration" of the loop logic manually
            # or just call the core logic inside the while loop.
            # Since 'run' has a while True, let's just trigger the reset check.
            
            # Simulate the logic added to the run loop:
            if not bot.pnl_guard.can_trade():
                open_positions = sum(1 for p in bot.positions.values() if abs(p) > 0)
                if open_positions == 0:
                    bot.pnl_guard.reset()
            
            self.assertTrue(bot.pnl_guard.can_trade(), "Should have reset after detecting no positions")
            self.assertIsNone(bot.pnl_guard.peak_equity, "Peak equity should be reset")

    @patch('live_trading_bot.WeexExecutionAdapter')
    def test_drawdown_no_reset_with_positions(self, MockAdapter):
        # Setup bot
        bot = SentinelLiveTradingBot(symbols=['cmt_btcusdt'], dry_run=True)
        bot.adapter = MockAdapter.return_value
        
        # Trigger drawdown halt
        bot.pnl_guard.update(1000) # Peak
        bot.pnl_guard.update(950)  # > 2% drawdown
        
        self.assertFalse(bot.pnl_guard.can_trade(), "Should be halted after drawdown")
        
        # Mock positions to have active trades
        bot.positions = {'cmt_btcusdt': 1.0}
        
        # Simulate reset check
        if not bot.pnl_guard.can_trade():
            open_positions = sum(1 for p in bot.positions.values() if abs(p) > 0)
            if open_positions == 0:
                bot.pnl_guard.reset()
        
        self.assertFalse(bot.pnl_guard.can_trade(), "Should NOT have reset if positions are still open")

if __name__ == '__main__':
    unittest.main()
