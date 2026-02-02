
import unittest
from unittest.mock import MagicMock, patch
import sys
import os
import pandas as pd

# Add root directory to path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from live_trading_bot import SentinelLiveTradingBot
from strategy.tpsl_calculator import TPSLCalculator

class TestBlitzScalp(unittest.TestCase):
    
    def test_tpsl_multipliers(self):
        calc = TPSLCalculator()
        # Test TREND_UP
        sl_m, tp_m = calc._get_regime_multipliers('TREND_UP', 0.8)
        self.assertEqual(sl_m, 1.0)
        self.assertEqual(tp_m, 2.5)
        
        # Test RANGE
        sl_m, tp_m = calc._get_regime_multipliers('RANGE', 0.8)
        self.assertEqual(sl_m, 0.7)
        self.assertEqual(tp_m, 1.5)

    @patch('live_trading_bot.WeexExecutionAdapter')
    def test_min_confidence_threshold(self, MockAdapter):
        bot = SentinelLiveTradingBot(symbols=['cmt_btcusdt'], dry_run=True)
        self.assertEqual(bot.min_confidence, 0.60)

    @patch('live_trading_bot.WeexExecutionAdapter')
    def test_aggressive_profit_locking(self, MockAdapter):
        bot = SentinelLiveTradingBot(symbols=['cmt_btcusdt'], dry_run=True)
        bot.adapter = MockAdapter.return_value
        bot.adapter.symbol = 'cmt_btcusdt'
        bot.adapter.place_tp_sl_order.return_value = {'success': True}
        bot.symbol_rules['cmt_btcusdt'] = {'price_step': 0.01, 'qty_step': 0.01, 'min_qty': 0.01}
        
        # Mock an active trade
        trade = {
            'direction': 'LONG',
            'size': 1.0,
            'entry_price': 100.0,
            'entry_time': 0,
            'profit_lock_tier': 0
        }
        bot.active_trades['cmt_btcusdt'] = [trade]
        
        # ROI = 2.5% (triggers Tier 1)
        bot.manage_active_trades('cmt_btcusdt', 102.5)
        self.assertEqual(trade['profit_lock_tier'], 1)
        self.assertAlmostEqual(trade['stop_loss'], 100.1, places=1) # 100 * (1 + 0.1/100)

        # ROI = 6% (triggers Tier 2)
        bot.manage_active_trades('cmt_btcusdt', 106.0)
        self.assertEqual(trade['profit_lock_tier'], 2)
        self.assertAlmostEqual(trade['stop_loss'], 101.0, places=1) # 100 * (1 + 1.0/100)

if __name__ == '__main__':
    unittest.main()
