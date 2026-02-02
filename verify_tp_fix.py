
import unittest
from unittest.mock import MagicMock, patch
import os

# Mock env vars early
os.environ['WEEX_API_KEY'] = 'test'
os.environ['WEEX_SECRET_KEY'] = 'test'
os.environ['WEEX_PASSPHRASE'] = 'test'

from live_trading_bot import SentinelLiveTradingBot

class TestTPFixes(unittest.TestCase):
    @patch('live_trading_bot.WeexExecutionAdapter')
    def test_tp_sl_management(self, MockAdapter):
        print("\nTesting TP/SL Management Logic...")
        mock_instance = MockAdapter.return_value
        bot = SentinelLiveTradingBot(symbols=['test'], dry_run=False)
        bot.adapter = mock_instance
        bot.symbol_rules = {'test': {'price_step': 0.1, 'qty_step': 1}}
        
        # Setup: Active Long Position
        mock_instance.get_positions.return_value = [{'symbol': 'test', 'holdAmount': 10, 'side': 'LONG', 'avgPrice': 100}]
        
        # Scenario 1: Only SL Exists (Missing TP)
        # Entry 100, SL 98 (Trigger < Entry). No TP.
        print("1. Testing Missing TP Restoration...")
        mock_instance._get.return_value = [{'type': 'CLOSE_LONG', 'triggerPrice': '98', 'status': 'UNTRIGGERED', 'planType': 'loss_plan'}]
        
        bot.check_and_fix_plans()
        
        # Should place TP (profit_plan)
        call_args = mock_instance.place_tp_sl_order.call_args
        self.assertIsNotNone(call_args)
        self.assertEqual(call_args[0][0], 'profit_plan')
        print("✓ Missing TP restored.")
        
        mock_instance.place_tp_sl_order.reset_mock()
        
        # Scenario 2: Redundancy (2 SLs)
        print("2. Testing Redundancy Cleanup (2 SLs)...")
        mock_instance._get.return_value = [
            {'type': 'CLOSE_LONG', 'triggerPrice': '98', 'status': 'UNTRIGGERED', 'planType': 'loss_plan'},
            {'type': 'CLOSE_LONG', 'triggerPrice': '97', 'status': 'UNTRIGGERED', 'planType': 'loss_plan'}
        ]
        
        bot.check_and_fix_plans()
        
        # Should cancel all and restore Both
        mock_instance.cancel_all_plan_orders.assert_called_with('test')
        self.assertEqual(mock_instance.place_tp_sl_order.call_count, 2)
        print("✓ Redundancy cleanup triggered and both restored.")
    
    @patch('live_trading_bot.WeexExecutionAdapter')
    def test_price_validation(self, MockAdapter):
        print("\nTesting Price Validation...")
        mock_instance = MockAdapter.return_value
        bot = SentinelLiveTradingBot(symbols=['test'], dry_run=False)
        bot.adapter = mock_instance
        bot.symbol_rules = {'test': {'price_step': 0.1, 'qty_step': 1}}
        
        # Scenario: Short Position Entry 100. Current Price 95. 
        # Default TP (4%) would be 96. (100 * 0.96)
        # But 96 > 95, so it's INVALID for a Trigger Order (Sell Short TP).
        # Should be clamped to 95 * 0.99 = 94.05 -> 94.0
        
        mock_instance.get_positions.return_value = [{'symbol': 'test', 'holdAmount': 10, 'side': 'SHORT', 'avgPrice': 100}]
        mock_instance._get.side_effect = lambda url, p: [] if 'currentPlan' in url else None # No existing plans
        mock_instance.get_ticker.return_value = {'last': '95.0'}
        
        bot.check_and_fix_plans()
        
        # Verify TP placement
        # Expect TP at ~94.0 (95 * 0.99)
        # check call args
        calls = mock_instance.place_tp_sl_order.call_args_list
        tp_call = [c for c in calls if c[0][0] == 'profit_plan'][0]
        price = tp_call[0][1]
        print(f"Placed TP Price: {price}")
        self.assertLess(price, 95.0)
        self.assertAlmostEqual(price, 94.0, delta=0.1)
        print("✓ Price clamped correctly below market.")


if __name__ == '__main__':
    unittest.main()
