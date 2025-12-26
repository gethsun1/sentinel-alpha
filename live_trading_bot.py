"""
Sentinel Alpha - Live Trading Bot
WEEX Competition Integration

This bot:
1. Connects to WEEX real-time market data
2. Uses AI-enhanced signal generation
3. Places trades automatically
4. Manages risk with multi-layer protection
5. Logs everything for audit
"""

import os
import sys
import time
import json
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from typing import Dict, List
from dotenv import load_dotenv

# Import Sentinel Alpha components
from execution.weex_adapter import WeexExecutionAdapter
from ai_enhanced_engine import AIEnhancedSignalEngine
from models.adaptive_learning_agent import AdaptiveLearningAgent
from risk.pnl_guard import PnLGuard
from execution.execution_guard import ExecutionGuard
from utils.logger import JsonLogger
from pathlib import Path

# Load environment variables
load_dotenv()

# ANSI colors for terminal
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'


class SentinelLiveTradingBot:
    """
    Live trading bot for WEEX AI Wars Competition
    
    Features:
    - Real-time market data from WEEX
    - AI-enhanced signal generation
    - Multi-layer risk management
    - Automatic trade execution
    - Performance tracking
    - Full audit logging
    """
    
    def __init__(self, 
                 symbol: str = "cmt_btcusdt",
                 leverage: int = 4,
                 max_position_size: float = 0.001,
                 cooldown_seconds: int = 180,
                 max_drawdown_pct: float = 0.02,
                 min_confidence: float = 0.70,
                 data_window: int = 100,
                 dry_run: bool = False):
        """
        Initialize live trading bot
        
        Args:
            symbol: Trading pair (default: cmt_btcusdt)
            leverage: Trading leverage (default: 4x)
            max_position_size: Maximum position in BTC (default: 0.001)
            cooldown_seconds: Cooldown between trades (default: 180s = 3min)
            max_drawdown_pct: Maximum drawdown before halt (default: 2%)
            min_confidence: Minimum confidence to trade (default: 0.70)
            data_window: Number of ticks to keep for analysis (default: 100)
            dry_run: If True, simulate without real orders (default: False)
        """
        self.symbol = symbol
        self.leverage = leverage
        self.max_position_size = max_position_size
        self.cooldown_seconds = cooldown_seconds
        self.max_drawdown_pct = max_drawdown_pct
        self.min_confidence = min_confidence
        self.data_window = data_window
        self.dry_run = dry_run
        
        # Initialize WEEX adapter
        print(f"{Colors.BOLD}Initializing WEEX Connection...{Colors.END}")
        self.adapter = WeexExecutionAdapter(
            api_key=os.getenv("WEEX_API_KEY"),
            secret_key=os.getenv("WEEX_SECRET_KEY"),
            passphrase=os.getenv("WEEX_PASSPHRASE"),
            default_symbol=symbol,
            leverage=leverage,
            dry_run=dry_run
        )
        
        # Set leverage
        leverage_result = self.adapter.set_leverage()
        print(f"✓ Leverage set to {leverage}×")
        
        # Initialize risk guards
        print(f"{Colors.BOLD}Initializing Risk Management...{Colors.END}")
        self.execution_guard = ExecutionGuard(cooldown_seconds, max_position_size)
        self.pnl_guard = PnLGuard(max_drawdown_pct)
        print(f"✓ Risk guards active")
        
        # Initialize loggers
        Path("logs").mkdir(exist_ok=True)
        self.trade_logger = JsonLogger("logs/live_trades.jsonl")
        self.signal_logger = JsonLogger("logs/live_signals.jsonl")
        self.performance_logger = JsonLogger("logs/performance.jsonl")
        print(f"✓ Logging initialized")
        
        # Market data storage
        self.market_data = []
        self.current_position = 0.0  # BTC
        self.entry_price = 0.0
        self.initial_equity = 1000.0  # USDT (from your account)
        self.current_equity = self.initial_equity
        self.peak_equity = self.initial_equity
        
        # Performance tracking
        self.trades_executed = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_pnl = 0.0
        
        print(f"✓ Bot initialized successfully\n")
    
    def fetch_market_tick(self) -> Dict:
        """Fetch latest market data from WEEX"""
        ticker = self.adapter.get_ticker(self.symbol)
        
        return {
            'timestamp': datetime.now(timezone.utc),
            'price': float(ticker['last']),
            'volume': float(ticker.get('base_volume', 0)),
            'bid': float(ticker.get('best_bid', ticker['last'])),
            'ask': float(ticker.get('best_ask', ticker['last']))
        }
    
    def update_market_data(self, tick: Dict):
        """Add new tick to market data window"""
        self.market_data.append(tick)
        
        # Keep only recent data
        if len(self.market_data) > self.data_window:
            self.market_data = self.market_data[-self.data_window:]
    
    def generate_signals(self) -> pd.DataFrame:
        """Generate AI-enhanced trading signals"""
        # Convert market data to DataFrame
        df = pd.DataFrame(self.market_data)
        
        # Need at least 20 ticks for meaningful analysis
        if len(df) < 20:
            return None
        
        # Rename columns to match expected format
        df = df.rename(columns={'volume': 'quantity'})
        
        # Generate signals using AI engine
        engine = AIEnhancedSignalEngine(df)
        signals = engine.generate_signals()
        
        return signals
    
    def should_trade(self, signal_row: pd.Series) -> bool:
        """Check if we should execute trade"""
        # Check signal type
        if signal_row['signal'] == 'NO-TRADE':
            return False
        
        # Check confidence
        if signal_row['calibrated_confidence'] < self.min_confidence:
            return False
        
        # Check PnL guard
        if not self.pnl_guard.can_trade():
            print(f"{Colors.RED}⚠ PnL Guard: Trading halted due to drawdown{Colors.END}")
            return False
        
        # Check execution guard
        if not self.execution_guard.can_trade(self.max_position_size):
            return False
        
        return True
    
    def calculate_position_size(self, confidence: float, current_price: float) -> float:
        """Calculate position size based on confidence and risk"""
        # Base size (conservative)
        base_size = 0.0001  # 0.0001 BTC
        
        # Scale with confidence
        confidence_multiplier = confidence
        
        # Calculate size
        size = base_size * confidence_multiplier
        
        # Cap at maximum
        size = min(size, self.max_position_size)
        
        # Round to 4 decimals
        size = round(size, 4)
        
        return size
    
    def execute_trade(self, signal: str, confidence: float, price: float, reasoning: str):
        """Execute trade on WEEX"""
        # Calculate position size
        size = self.calculate_position_size(confidence, price)
        
        # Calculate limit price (0.1% from market)
        if signal == 'LONG':
            limit_price = price * 1.001
        else:  # SHORT
            limit_price = price * 0.999
        
        limit_price = round(limit_price, 1)
        
        print(f"\n{Colors.BOLD}Executing Trade:{Colors.END}")
        print(f"  Signal: {signal}")
        print(f"  Confidence: {confidence:.3f}")
        print(f"  Size: {size} BTC")
        print(f"  Price: ${price:.2f}")
        print(f"  Limit: ${limit_price:.2f}")
        print(f"  Reasoning: {reasoning}")
        
        if self.dry_run:
            print(f"{Colors.YELLOW}  [DRY RUN - No actual order placed]{Colors.END}")
            order_result = {
                'status': 'simulated',
                'order_id': f'DRY_RUN_{int(time.time())}',
                'size': size,
                'price': limit_price
            }
        else:
            # Place real order
            order_result = self.adapter.place_order(
                direction=signal,
                size=size,
                price=limit_price
            )
        
        # Log trade
        trade_record = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'signal': signal,
            'confidence': confidence,
            'size': size,
            'price': price,
            'limit_price': limit_price,
            'reasoning': reasoning,
            'order_result': order_result,
            'dry_run': self.dry_run
        }
        self.trade_logger.log(trade_record)
        
        # Update tracking
        self.execution_guard.register_trade(size)
        self.trades_executed += 1
        
        # Update position
        if signal == 'LONG':
            self.current_position += size
            self.entry_price = price
        else:
            self.current_position -= size
            self.entry_price = price
        
        print(f"{Colors.GREEN}✓ Trade executed successfully{Colors.END}")
        print(f"  Order ID: {order_result.get('order_id', 'N/A')}\n")
        
        return order_result
    
    def update_performance(self, current_price: float):
        """Update performance metrics"""
        # Calculate unrealized PnL
        if self.current_position != 0:
            unrealized_pnl = self.current_position * (current_price - self.entry_price)
        else:
            unrealized_pnl = 0.0
        
        # Update equity
        self.current_equity = self.initial_equity + self.total_pnl + unrealized_pnl
        
        # Update peak
        self.peak_equity = max(self.peak_equity, self.current_equity)
        
        # Update PnL guard
        self.pnl_guard.update(self.current_equity)
        
        # Calculate metrics
        drawdown = (self.peak_equity - self.current_equity) / self.peak_equity
        roi = (self.current_equity - self.initial_equity) / self.initial_equity
        
        win_rate = 0.0
        if self.trades_executed > 0:
            win_rate = self.winning_trades / self.trades_executed
        
        return {
            'equity': self.current_equity,
            'peak_equity': self.peak_equity,
            'drawdown': drawdown,
            'roi': roi,
            'total_pnl': self.total_pnl + unrealized_pnl,
            'trades': self.trades_executed,
            'win_rate': win_rate
        }
    
    def print_status(self, current_price: float):
        """Print current bot status"""
        perf = self.update_performance(current_price)
        
        print(f"\n{'='*70}")
        print(f"{Colors.BOLD}SENTINEL ALPHA - LIVE STATUS{Colors.END}")
        print(f"{'='*70}")
        print(f"Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"Symbol: {self.symbol}")
        print(f"Price: ${current_price:.2f}")
        print(f"\n{Colors.BOLD}Position:{Colors.END}")
        print(f"  Size: {self.current_position:.4f} BTC")
        print(f"  Entry: ${self.entry_price:.2f}" if self.current_position != 0 else "  Entry: N/A")
        print(f"\n{Colors.BOLD}Performance:{Colors.END}")
        print(f"  Equity: ${perf['equity']:.2f}")
        print(f"  ROI: {perf['roi']*100:.2f}%")
        print(f"  Drawdown: {perf['drawdown']*100:.2f}%")
        print(f"  Total PnL: ${perf['total_pnl']:.2f}")
        print(f"\n{Colors.BOLD}Trading:{Colors.END}")
        print(f"  Trades: {self.trades_executed}")
        print(f"  Win Rate: {perf['win_rate']*100:.1f}%")
        print(f"  Status: {'🔴 HALTED' if not self.pnl_guard.can_trade() else '🟢 ACTIVE'}")
        print(f"{'='*70}\n")
    
    def run(self, check_interval: int = 60, status_interval: int = 300):
        """
        Run live trading bot
        
        Args:
            check_interval: Seconds between market checks (default: 60s = 1min)
            status_interval: Seconds between status updates (default: 300s = 5min)
        """
        print(f"\n{Colors.BOLD}{Colors.GREEN}{'='*70}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.GREEN}SENTINEL ALPHA - LIVE TRADING BOT STARTED{Colors.END}")
        print(f"{Colors.BOLD}{Colors.GREEN}{'='*70}{Colors.END}\n")
        
        print(f"Configuration:")
        print(f"  Symbol: {self.symbol}")
        print(f"  Leverage: {self.leverage}×")
        print(f"  Max Position: {self.max_position_size} BTC")
        print(f"  Min Confidence: {self.min_confidence}")
        print(f"  Cooldown: {self.cooldown_seconds}s")
        print(f"  Max Drawdown: {self.max_drawdown_pct*100}%")
        print(f"  Check Interval: {check_interval}s")
        print(f"  Dry Run: {self.dry_run}")
        print()
        
        last_status_time = time.time()
        iteration = 0
        
        try:
            while True:
                iteration += 1
                
                try:
                    # Fetch market data
                    tick = self.fetch_market_tick()
                    self.update_market_data(tick)
                    
                    current_price = tick['price']
                    
                    # Print status periodically
                    if time.time() - last_status_time >= status_interval:
                        self.print_status(current_price)
                        last_status_time = time.time()
                    else:
                        # Brief update
                        print(f"[{iteration}] Price: ${current_price:.2f} | "
                              f"Data points: {len(self.market_data)} | "
                              f"Position: {self.current_position:.4f} BTC")
                    
                    # Generate signals (need enough data)
                    if len(self.market_data) >= 20:
                        signals = self.generate_signals()
                        
                        if signals is not None and len(signals) > 0:
                            # Get latest signal
                            latest_signal = signals.iloc[-1]
                            
                            # Log signal
                            self.signal_logger.log({
                                'timestamp': datetime.now(timezone.utc).isoformat(),
                                'price': current_price,
                                'regime': latest_signal['regime'],
                                'confidence': float(latest_signal['calibrated_confidence']),
                                'signal': latest_signal['signal'],
                                'reasoning': latest_signal['reasoning']
                            })
                            
                            # Check if should trade
                            if self.should_trade(latest_signal):
                                self.execute_trade(
                                    signal=latest_signal['signal'],
                                    confidence=float(latest_signal['calibrated_confidence']),
                                    price=current_price,
                                    reasoning=latest_signal['reasoning']
                                )
                    
                    # Log performance
                    perf = self.update_performance(current_price)
                    self.performance_logger.log({
                        'timestamp': datetime.now(timezone.utc).isoformat(),
                        **perf
                    })
                    
                except Exception as e:
                    print(f"{Colors.RED}Error in trading loop: {e}{Colors.END}")
                    import traceback
                    traceback.print_exc()
                
                # Wait before next check
                time.sleep(check_interval)
                
        except KeyboardInterrupt:
            print(f"\n{Colors.YELLOW}Bot stopped by user{Colors.END}")
            self.shutdown()
    
    def shutdown(self):
        """Graceful shutdown"""
        print(f"\n{Colors.BOLD}Shutting down Sentinel Alpha...{Colors.END}\n")
        
        # Print final performance
        if len(self.market_data) > 0:
            final_price = self.market_data[-1]['price']
            self.print_status(final_price)
        
        print(f"{Colors.GREEN}✓ Shutdown complete{Colors.END}\n")


def main():
    """Main entry point"""
    print("\n" + "="*70)
    print("SENTINEL ALPHA - LIVE TRADING BOT")
    print("WEEX AI Wars Competition")
    print("="*70 + "\n")
    
    # Configuration
    config = {
        'symbol': 'cmt_btcusdt',
        'leverage': 4,
        'max_position_size': 0.001,  # 0.001 BTC max
        'cooldown_seconds': 180,      # 3 minutes between trades
        'max_drawdown_pct': 0.02,     # 2% max drawdown
        'min_confidence': 0.70,       # 70% minimum confidence
        'data_window': 100,            # Keep 100 ticks
        'dry_run': False               # Set to True for testing
    }
    
    print("Configuration:")
    for key, value in config.items():
        print(f"  {key}: {value}")
    print()
    
    response = input("Start live trading? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        print("Cancelled.")
        return
    
    # Create and run bot
    bot = SentinelLiveTradingBot(**config)
    bot.run(check_interval=60, status_interval=300)


if __name__ == "__main__":
    main()

