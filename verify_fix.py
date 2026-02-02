
import unittest
from unittest.mock import MagicMock, patch
import os

# Mock env vars early
os.environ['WEEX_API_KEY'] = 'test'
os.environ['WEEX_SECRET_KEY'] = 'test'
os.environ['WEEX_PASSPHRASE'] = 'test'

from live_trading_bot import SentinelLiveTradingBot

class TestFixes(unittest.TestCase):
    @patch('live_trading_bot.WeexExecutionAdapter')
    def test_sl_detection_logic(self, MockAdapter):
        print("\nTesting SL Detection Logic...")
        
        mock_instance = MockAdapter.return_value
        bot = SentinelLiveTradingBot(symbols=['test'], dry_run=False)
        bot.adapter = mock_instance # Ensure consistency
        bot.symbol_rules = {'test': {'price_step': 0.1, 'qty_step': 1}}
        
        # Scenario 1: Redundancy Trigger (>3 orders)
        print("1. Testing Redundancy Cleanup...")
        mock_instance.get_positions.return_value = [{'symbol': 'test', 'holdAmount': 10, 'side': 'LONG', 'avgPrice': 100}]
        mock_instance._get.return_value = [{'type': 'CLOSE_LONG', 'status': 'UNTRIGGERED'}] * 5 # 5 orders
        
        bot.check_and_fix_missing_sl()
        
        # Should have called cancel_all_plan_orders
        mock_instance.cancel_all_plan_orders.assert_called_with('test')
        # And then placed a new SL
        mock_instance.place_tp_sl_order.assert_called()
        print("✓ Redundancy cleanup triggered correctly.")

    @patch('live_trading_bot.WeexExecutionAdapter')
    def test_sl_recognition(self, MockAdapter):
        print("\nTesting SL Recognition (CLOSE_LONG)...")
        mock_instance = MockAdapter.return_value
        bot = SentinelLiveTradingBot(symbols=['test'], dry_run=False)
        bot.adapter = mock_instance
        bot.symbol_rules = {'test': {'price_step': 0.1, 'qty_step': 1}}
        
        mock_instance.get_positions.return_value = [{'symbol': 'test', 'holdAmount': 10, 'side': 'LONG', 'avgPrice': 100}]
        
        # Scenario 2: Existing SL (Trigger < Entry for Long)
        # Entry 100, Trigger 90 -> SL
        mock_instance._get.return_value = [{'type': 'CLOSE_LONG', 'triggerPrice': '90', 'status': 'UNTRIGGERED'}]
        # Reset mocks
        mock_instance.place_tp_sl_order.reset_mock()
        
        bot.check_and_fix_missing_sl()
        
        # Should NOT place new SL
        mock_instance.place_tp_sl_order.assert_not_called()
        print("✓ Correctly identified existing SL (CLOSE_LONG < Entry).")
        
        # Scenario 3: Only TP Exists (Trigger > Entry for Long)
        # Entry 100, Trigger 110 -> TP
        mock_instance._get.return_value = [{'type': 'CLOSE_LONG', 'triggerPrice': '110', 'status': 'UNTRIGGERED'}]
        
        bot.check_and_fix_missing_sl()
        
        # Should place new SL
        mock_instance.place_tp_sl_order.assert_called()
        print("✓ Correctly identified missing SL when only TP exists.")

if __name__ == '__main__':
    unittest.main()
