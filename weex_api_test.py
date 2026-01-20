"""
WEEX API Testing Script - Sentinel Alpha
==========================================

Mission: Pass WEEX API qualification before January 4
Purpose: Verify all required API endpoints work correctly

This script performs end-to-end testing of:
1. Connectivity (server time)
2. Authentication (all endpoints)
3. Market data (ticker, contract info)
4. Account query (assets)
5. Leverage setting
6. Order placement (~10 USDT test order)
7. Fill history

All actions are logged for WEEX support audit.
"""

import os
import sys
import json
import time
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from execution.weex_adapter import WeexExecutionAdapter
from dotenv import load_dotenv

# Load credentials from .env
load_dotenv()

# ANSI color codes for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

class WEEXAPITester:
    """Complete WEEX API testing suite"""
    
    def __init__(self, test_order_size_usd: float = 10.0, test_leverage: int = 4):
        """
        Args:
            test_order_size_usd: Test order size in USDT (default: 10)
            test_leverage: Test leverage (default: 4x)
        """
        self.test_order_size_usd = test_order_size_usd
        self.test_leverage = test_leverage
        self.results = []
        self.adapter = None
        
        # Create logs directory
        Path("logs").mkdir(exist_ok=True)
        self.log_file = f"logs/weex_api_test_{int(time.time())}.jsonl"
        
        print(f"\n{Colors.BOLD}{'='*70}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.BLUE}WEEX API QUALIFICATION TEST - SENTINEL ALPHA{Colors.END}")
        print(f"{Colors.BOLD}{'='*70}{Colors.END}\n")
        print(f"Test Configuration:")
        print(f"  - Order Size: ~{test_order_size_usd} USDT")
        print(f"  - Leverage: {test_leverage}×")
        print(f"  - Environment: LIVE COMPETITION")
        print(f"  - Log File: {self.log_file}")
        print(f"\n{Colors.BOLD}{'='*70}{Colors.END}\n")
    
    def log(self, test_name: str, status: str, data: dict, error: str = None):
        """Log test result"""
        result = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "test": test_name,
            "status": status,
            "data": data,
            "error": error
        }
        self.results.append(result)
        
        # Write to log file
        with open(self.log_file, "a") as f:
            f.write(json.dumps(result) + "\n")
        
        # Console output
        if status == "PASS":
            print(f"{Colors.GREEN}✓{Colors.END} {test_name}")
        elif status == "FAIL":
            print(f"{Colors.RED}✗{Colors.END} {test_name}")
            if error:
                print(f"  {Colors.RED}Error: {error}{Colors.END}")
        elif status == "INFO":
            print(f"{Colors.BLUE}ℹ{Colors.END} {test_name}")
    
    def initialize_adapter(self):
        """Test 0: Initialize WEEX adapter with credentials"""
        print(f"{Colors.BOLD}[0/7] Initializing WEEX Adapter...{Colors.END}")
        
        try:
            api_key = os.getenv("WEEX_API_KEY")
            secret_key = os.getenv("WEEX_SECRET_KEY")
            passphrase = os.getenv("WEEX_PASSPHRASE")
            
            if not all([api_key, secret_key, passphrase]):
                raise ValueError("Missing credentials in .env file")
            
            self.adapter = WeexExecutionAdapter(
                api_key=api_key,
                secret_key=secret_key,
                passphrase=passphrase,
                default_symbol="cmt_btcusdt",
                leverage=self.test_leverage,
                dry_run=False  # LIVE TESTING
            )
            
            self.log("Initialize Adapter", "PASS", {
                "symbol": "cmt_btcusdt",
                "leverage": self.test_leverage,
                "dry_run": False
            })
            print()
            return True
            
        except Exception as e:
            self.log("Initialize Adapter", "FAIL", {}, str(e))
            print()
            return False
    
    def test_connectivity(self):
        """Test 1: Server time endpoint"""
        print(f"{Colors.BOLD}[1/7] Testing Connectivity (Server Time)...{Colors.END}")
        
        try:
            response = self.adapter.get_server_time()
            
            # WEEX returns timestamp data directly or in various formats
            if "timestamp" in response or "epoch" in response or "iso" in response:
                self.log("Get Server Time", "PASS", response)
            elif "code" in response and response["code"] == "00000":
                self.log("Get Server Time", "PASS", response)
            else:
                self.log("Get Server Time", "FAIL", response, "Unexpected response format")
                
        except Exception as e:
            self.log("Get Server Time", "FAIL", {}, str(e))
        
        print()
    
    def test_ticker(self):
        """Test 2: Get ticker for cmt_btcusdt"""
        print(f"{Colors.BOLD}[2/7] Testing Market Data (Ticker)...{Colors.END}")
        
        try:
            response = self.adapter.get_ticker("cmt_btcusdt")
            
            if "symbol" in response or "last" in response:
                self.log("Get Ticker", "PASS", response)
                self.current_price = float(response.get("last", 0))
                self.log("Get Ticker", "INFO", {
                    "current_btc_price": self.current_price,
                    "mark_price": response.get("markPrice"),
                    "24h_change": response.get("priceChangePercent")
                })
            else:
                self.log("Get Ticker", "FAIL", response, "No ticker data")
                
        except Exception as e:
            self.log("Get Ticker", "FAIL", {}, str(e))
        
        print()
    
    def test_contract_info(self):
        """Test 3: Get contract information"""
        print(f"{Colors.BOLD}[3/7] Testing Contract Information...{Colors.END}")
        
        try:
            response = self.adapter.get_contract_info("cmt_btcusdt")
            
            if isinstance(response, list) and len(response) > 0:
                contract = response[0]
                self.log("Get Contract Info", "PASS", contract)
                self.log("Get Contract Info", "INFO", {
                    "min_order_size": contract.get("minOrderSize"),
                    "max_leverage": contract.get("maxLeverage"),
                    "maker_fee": contract.get("makerFeeRate"),
                    "taker_fee": contract.get("takerFeeRate")
                })
                self.min_order_size = float(contract.get("minOrderSize", "0.0001"))
            else:
                self.log("Get Contract Info", "FAIL", response, "No contract data")
                
        except Exception as e:
            self.log("Get Contract Info", "FAIL", {}, str(e))
        
        print()
    
    def test_account_assets(self):
        """Test 4: Query account assets"""
        print(f"{Colors.BOLD}[4/7] Testing Account Query (Assets)...{Colors.END}")
        
        try:
            response = self.adapter.get_account_assets()
            
            # Check if we got account data (may be array or object)
            if isinstance(response, list) and len(response) > 0:
                self.log("Get Account Assets", "PASS", response)
                # Check USDT balance
                for asset in response:
                    if asset.get("coinName") == "USDT" or asset.get("coin") == "USDT":
                        self.log("Get Account Assets", "INFO", {
                            "usdt_balance": asset.get("available"),
                            "usdt_equity": asset.get("equity"),
                            "usdt_frozen": asset.get("frozen")
                        })
            elif "code" in response and response["code"] == "00000":
                self.log("Get Account Assets", "PASS", response)
                if "data" in response:
                    for asset in response.get("data", []):
                        if asset.get("coin") == "USDT":
                            self.log("Get Account Assets", "INFO", {
                                "usdt_balance": asset.get("available"),
                                "usdt_locked": asset.get("frozen")
                            })
            else:
                self.log("Get Account Assets", "FAIL", response, "Failed to get assets")
                
        except Exception as e:
            self.log("Get Account Assets", "FAIL", {}, str(e))
        
        print()
    
    def test_set_leverage(self):
        """Test 5: Set leverage"""
        print(f"{Colors.BOLD}[5/7] Testing Leverage Setting ({self.test_leverage}×)...{Colors.END}")
        
        try:
            response = self.adapter.set_leverage()
            
            # WEEX returns code "200" or "00000" for success
            if ("code" in response and (response["code"] == "00000" or response["code"] == "200")) or \
               ("msg" in response and response["msg"] == "success"):
                self.log("Set Leverage", "PASS", {
                    "leverage": self.test_leverage,
                    "response": response
                })
            else:
                self.log("Set Leverage", "FAIL", response, "Failed to set leverage")
                
        except Exception as e:
            self.log("Set Leverage", "FAIL", {}, str(e))
        
        print()
    
    def test_place_order(self):
        """Test 6: Place a real test order (~10 USDT)"""
        print(f"{Colors.BOLD}[6/7] Testing Order Placement (~{self.test_order_size_usd} USDT)...{Colors.END}")
        
        try:
            # Calculate order size in BTC
            if not hasattr(self, 'current_price') or self.current_price <= 0:
                raise ValueError("No valid BTC price available")
            
            # Order size = USDT amount / BTC price
            order_size = self.test_order_size_usd / self.current_price
            
            # Ensure minimum order size
            if not hasattr(self, 'min_order_size'):
                self.min_order_size = 0.0001
            
            order_size = max(order_size, self.min_order_size)
            
            # Round to appropriate precision
            order_size = round(order_size, 4)
            
            # Calculate limit price (slightly above market for LONG to avoid immediate fill)
            limit_price = self.current_price * 1.001  # 0.1% above market
            limit_price = round(limit_price, 1)  # Round to tick size
            
            self.log("Place Order", "INFO", {
                "direction": "LONG",
                "size_btc": order_size,
                "size_usd_approx": order_size * self.current_price,
                "limit_price": limit_price,
                "market_price": self.current_price
            })
            
            # Place order
            response = self.adapter.place_order(
                direction="LONG",
                size=order_size,
                price=limit_price
            )
            
            # Check if order was placed (has order_id or client_oid)
            if "order_id" in response or "client_oid" in response:
                self.log("Place Order", "PASS", response)
                self.order_id = response.get("order_id") or response.get("data", {}).get("order_id")
                print(f"\n  {Colors.GREEN}Order placed successfully!{Colors.END}")
                print(f"  Order ID: {self.order_id}")
            elif "code" in response and response["code"] == "00000":
                self.log("Place Order", "PASS", response)
                self.order_id = response.get("data", {}).get("order_id")
                print(f"\n  {Colors.GREEN}Order placed successfully!{Colors.END}")
                print(f"  Order ID: {self.order_id}")
            else:
                self.log("Place Order", "FAIL", response, "Order placement failed")
                
        except Exception as e:
            self.log("Place Order", "FAIL", {}, str(e))
        
        print()
    
    def test_get_fills(self):
        """Test 7: Get trade history / fills"""
        print(f"{Colors.BOLD}[7/7] Testing Fill History Query...{Colors.END}")
        
        try:
            # Wait a moment for order to process
            time.sleep(2)
            
            response = self.adapter.get_fills("cmt_btcusdt")
            
            # Check for various success indicators
            if isinstance(response, list):
                # Direct array response
                self.log("Get Fills", "PASS", {"fill_count": len(response), "fills": response[:3]})
                if len(response) > 0:
                    self.log("Get Fills", "INFO", {
                        "recent_fills_count": len(response[:3]),
                        "fills": response[:3]
                    })
            elif "error" in response and response.get("status_code") == 521:
                # HTTP 521 error (this endpoint might not be available yet)
                self.log("Get Fills", "FAIL", response, "Endpoint returned HTTP 521 - may not be available yet")
            elif "code" in response and response["code"] == "00000":
                self.log("Get Fills", "PASS", response)
                if "data" in response and len(response.get("data", [])) > 0:
                    recent_fills = response["data"][:3]
                    self.log("Get Fills", "INFO", {
                        "recent_fills_count": len(recent_fills),
                        "fills": recent_fills
                    })
            else:
                self.log("Get Fills", "FAIL", response, "Failed to get fills")
                
        except Exception as e:
            self.log("Get Fills", "FAIL", {}, str(e))
        
        print()
    
    def print_summary(self):
        """Print test summary"""
        print(f"\n{Colors.BOLD}{'='*70}{Colors.END}")
        print(f"{Colors.BOLD}TEST SUMMARY{Colors.END}")
        print(f"{Colors.BOLD}{'='*70}{Colors.END}\n")
        
        passed = sum(1 for r in self.results if r["status"] == "PASS")
        failed = sum(1 for r in self.results if r["status"] == "FAIL")
        total = passed + failed
        
        print(f"Total Tests: {total}")
        print(f"{Colors.GREEN}Passed: {passed}{Colors.END}")
        print(f"{Colors.RED}Failed: {failed}{Colors.END}")
        
        if failed == 0:
            print(f"\n{Colors.GREEN}{Colors.BOLD}✓ ALL TESTS PASSED - WEEX API QUALIFICATION COMPLETE!{Colors.END}")
            print(f"\n{Colors.GREEN}You are ready for the competition!{Colors.END}")
            print(f"\nNext steps:")
            print(f"  1. Review logs: {self.log_file}")
            print(f"  2. Keep this test output for WEEX support if needed")
            print(f"  3. Proceed to model tuning phase")
        else:
            print(f"\n{Colors.RED}{Colors.BOLD}✗ SOME TESTS FAILED{Colors.END}")
            print(f"\nAction required:")
            print(f"  1. Review error logs: {self.log_file}")
            print(f"  2. Check API credentials")
            print(f"  3. Verify IP allowlisting")
            print(f"  4. Contact WEEX support if needed")
        
        print(f"\n{Colors.BOLD}{'='*70}{Colors.END}\n")
        
        return failed == 0
    
    def run_all_tests(self):
        """Execute all API tests in sequence"""
        if not self.initialize_adapter():
            print(f"{Colors.RED}Failed to initialize adapter. Aborting tests.{Colors.END}")
            return False
        
        # Run all tests
        self.test_connectivity()
        self.test_ticker()
        self.test_contract_info()
        self.test_account_assets()
        self.test_set_leverage()
        self.test_place_order()
        self.test_get_fills()
        
        # Print summary
        return self.print_summary()


def main():
    """Main entry point"""
    print(f"\n{Colors.YELLOW}⚠ WARNING: This script will place a REAL order on WEEX!{Colors.END}")
    print(f"{Colors.YELLOW}Order size: ~10 USDT at 4× leverage{Colors.END}\n")
    
    response = input("Continue? (yes/no): ").strip().lower()
    if response not in ["yes", "y"]:
        print(f"\n{Colors.YELLOW}Test aborted by user.{Colors.END}\n")
        return
    
    # Run tests
    tester = WEEXAPITester(
        test_order_size_usd=10.0,
        test_leverage=4
    )
    
    success = tester.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

