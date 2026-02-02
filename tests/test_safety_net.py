
import unittest
from unittest.mock import MagicMock, patch
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from live_trading_bot import SentinelLiveTradingBot
from execution.weex_adapter import WeexExecutionAdapter

class TestSLSafetyNet(unittest.TestCase):
    @patch('live_trading_bot.WeexExecutionAdapter')
    def test_missing_sl_placement(self, MockAdapter):
        # Setup
        bot = SentinelLiveTradingBot(symbols=['cmt_btcusdt'], dry_run=True)
        bot.adapter = MockAdapter.return_value
        
        # Scenario: Position Exists, NO SL found
        bot.adapter.get_positions.return_value = [{
            'symbol': 'cmt_btcusdt',
            'holdAmount': '1.0',
            'side': 'LONG',
            'avgPrice': '50000'
        }]
        
        # Mock _get return for plans (Empty list = no active SL)
        bot.adapter._get.return_value = []
        # Support place_tp_sl_order returning success
        bot.adapter.place_tp_sl_order.return_value = {'success': True}
        
        # Execute
        bot.check_and_fix_missing_sl()
        
        # Verify
        # Should have called place_tp_sl_order with approx 49000 (50000 * 0.98)
        bot.adapter.place_tp_sl_order.assert_called_once()
        args = bot.adapter.place_tp_sl_order.call_args
        self.assertEqual(args[0][0], 'loss_plan') # plan_type
        self.assertAlmostEqual(args[0][1], 49000.0, delta=100) # price (2% below 50k)
        
    @patch('live_trading_bot.WeexExecutionAdapter')
    def test_existing_sl_no_action(self, MockAdapter):
        # Setup
        bot = SentinelLiveTradingBot(symbols=['cmt_btcusdt'], dry_run=True)
        bot.adapter = MockAdapter.return_value
        
        # Scenario: Position Exists, SL DOES exist
        bot.adapter.get_positions.return_value = [{
            'symbol': 'cmt_btcusdt',
            'holdAmount': '1.0',
            'side': 'LONG',
            'avgPrice': '50000'
        }]
        
        bot.adapter._get.return_value = [{
            'planType': 'loss_plan',
            'status': 'active',
            'triggerPrice': '49000'
        }]
        
        # Execute
        bot.check_and_fix_missing_sl()
        
        # Verify
        bot.adapter.place_tp_sl_order.assert_not_called()

if __name__ == '__main__':
    unittest.main()
