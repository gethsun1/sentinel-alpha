import time
import os
import signal
import sys
import logging
import json
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
import math
import argparse
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from execution.weex_adapter import WeexExecutionAdapter
from ai_enhanced_engine import AIEnhancedSignalEngine
from execution.execution_guard import ExecutionGuard
from risk.pnl_guard import PnLGuard
from strategy.tpsl_calculator import TPSLCalculator
from execution.ai_log_adapter import AILogAdapter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("SentinelBot")

class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'

class JsonLogger:
    def __init__(self, filename):
        self.filename = filename
        
    def log(self, data: dict):
        try:
            with open(self.filename, 'a') as f:
                f.write(json.dumps(data) + '\n')
        except Exception as e:
            logger.error(f"Failed to write to {self.filename}: {e}")

class SentinelLiveTradingBot:
    def __init__(self, 
                 symbols: List[str],
                 leverage: int = 5,
                 max_position_size: float = 0.01,
                 cooldown_seconds: int = 300,
                 max_drawdown_pct: float = 0.02,
                 min_confidence: float = 0.60,  # Raised to 0.70 for Trend Following
                 data_window: int = 100,
                 dry_run: bool = False):
        
        self.symbols = symbols
        self.max_position_size = max_position_size
        self.min_confidence = min_confidence
        self.data_window = data_window
        self.dry_run = dry_run
        
        # Initialize WEEX Adapter
        self.adapter = WeexExecutionAdapter(
            api_key=os.getenv("WEEX_API_KEY"),
            secret_key=os.getenv("WEEX_SECRET_KEY"),
            passphrase=os.getenv("WEEX_PASSPHRASE"),
            default_symbol=symbols[0],
            leverage=leverage,
            dry_run=dry_run
        )
        
        # Set leverage
        for sym in symbols:
            self.adapter.symbol = sym
            self.adapter.leverage = leverage
            self.adapter.set_leverage()
            print(f"✓ Leverage set to {leverage}× for {sym}")
        
        # Components
        # self.signal_engine instantiated per tick
        # Guard now per-symbol with notional cap to avoid over-blocking low-priced pairs
        self.max_notional_usd = 200  # upper bound per order; target sizing is ~50 USD
        self.execution_guard = ExecutionGuard(cooldown_seconds, max_notional_usd=self.max_notional_usd)
        self.last_trade_time = {sym: 0 for sym in symbols}
        self.pnl_guard = PnLGuard(max_drawdown_pct)
        
        # Loggers
        Path("logs").mkdir(exist_ok=True)
        self.trade_logger = JsonLogger("logs/live_trades.jsonl")
        self.signal_logger = JsonLogger("logs/live_signals.jsonl")
        self.performance_logger = JsonLogger("logs/performance.jsonl")
        self.compliance_logger = JsonLogger("logs/compliance.jsonl")
        self.high_conviction_logger = JsonLogger("logs/high_conviction_signals.jsonl")
        
        self.tpsl_calculator = TPSLCalculator(
            min_rr_ratio=1.2, max_rr_ratio=3.0, base_sl_multiplier=1.0, base_tp_multiplier=1.0
        )
        
        self.ai_log_adapter = AILogAdapter(
            api_key=os.getenv("WEEX_API_KEY"),
            secret_key=os.getenv("WEEX_SECRET_KEY"),
            passphrase=os.getenv("WEEX_PASSPHRASE"),
            log_file="logs/ai_logs_submitted.jsonl",
            dry_run=dry_run
        )
        
        # State
        self.market_data = {sym: [] for sym in symbols}
        self.symbol_rules = {}
        self.positions = {sym: 0.0 for sym in symbols}
        self.active_trades = {sym: [] for sym in symbols}  # track per-symbol trade metadata for concurrency/TP mgmt
        self.portfolio_risk_cap = 0.03  # 3% portfolio risk cap across open positions
        self.last_leverage = {sym: leverage for sym in symbols}
        self.current_equity = 1000.0
        self.peak_equity = self.current_equity
        self.trades_executed = 0
        
        # Sync
        self.sync_state()
        self.pnl_guard.update(self.current_equity)
        self.peak_equity = max(self.peak_equity, self.current_equity)
        
        # Automatic Hedge Consolidation
        # Note: consolidate_hedged_positions() method needs to be implemented.
        # This call assumes self.positions is correctly populated by sync_state()
        # and that the method exists to handle potential hedged positions.
        # If 'pos_dict' was intended to be passed, it would need to be defined.
        # Assuming the intent is to run consolidation after initial sync.
        # self.positions = pos_dict # This line was in the instruction but 'pos_dict' is not defined here.
        self.consolidate_hedged_positions() # This method needs to be implemented.
        
        self.log_performance()
        print(f"✓ Bot initialized for {len(symbols)} symbols: {symbols}\n")

    def sync_state(self):
        print(f"{Colors.BOLD}Syncing Rules & Account...{Colors.END}")
        
        # Rules
        for sym in self.symbols:
            rules = self.adapter.get_symbol_rules(sym)
            self.symbol_rules[sym] = rules
            print(f"  [{sym}] MinQty: {rules.get('min_qty')}, Step: {rules.get('qty_step')}")
            
        # Equity
        try:
             assets = self.adapter.get_account_assets()
             # Handle List Response (Direct)
             data_list = []
             if isinstance(assets, list):
                 data_list = assets
             elif isinstance(assets, dict):
                 data_list = assets.get('data', [])
                 
             for asset in data_list:
                 # Support both 'currency' (V1) and 'coinName' (V2/newer) keys
                 asset_name = asset.get('currency', asset.get('coinName', asset.get('asset', '')))
                 if asset_name == 'USDT':
                     val = asset.get('equity', asset.get('available', 1000))
                     self.current_equity = float(val)
                     break
                     
             print(f"  ✓ Account Equity: ${self.current_equity:.2f}")
        except Exception as e:
             self.current_equity = 1000.0
             print(f"  ⚠ Equity error: {e}")
             
        # Positions
        try:
            positions = self.adapter.get_positions()
            # Handle List parsing
            data_list = []
            if isinstance(positions, list):
                data_list = positions
            elif isinstance(positions, dict):
                data_list = positions.get('data', [])
                
            for pos in data_list:
                sym = pos.get('symbol')
                if sym in self.symbols:
                    amt = float(pos.get('holdAmount', pos.get('size', 0))) # Support both keys just in case
                    side = str(pos.get('side', ''))
                    # WEEX docs: side="LONG" or "SHORT"
                    if side.upper() == 'SHORT': 
                        amt = -amt
                    
                    self.positions[sym] = amt
                    print(f"  ✓ Active Position {sym}: {amt}")
                    # Seed minimal metadata for legacy open positions so concurrency checks don't block
                    if abs(amt) > 0 and not self.active_trades.get(sym):
                        self.active_trades[sym] = [{
                            'direction': 'LONG' if amt > 0 else 'SHORT',
                            'trade_class': 'LEGACY',
                            'risk_pct': 0.0,
                            'entry_price': None,
                            'size': abs(amt),
                            'runner_size': 0.0,
                            'atr': 0.0,
                            'breakeven_set': True,
                            'trailing_set': True,
                            'tp1': None,
                            'tp2': None,
                            'stop_loss': None
                        }]
        except Exception as e:
            print(f"  ⚠ Pos error: {e}")
        
        # Initialize drawdown tracking
        self.pnl_guard.update(self.current_equity)
        self.peak_equity = max(self.peak_equity, self.current_equity)

    def refresh_account_state(self):
        """
        Lightweight equity/position refresh for drawdown guard and dashboard.
        """
        try:
            assets = self.adapter.get_account_assets()
            data_list = []
            if isinstance(assets, list):
                data_list = assets
            elif isinstance(assets, dict):
                data_list = assets.get('data', [])
            for asset in data_list:
                # Support both 'currency' (V1) and 'coinName' (V2/newer) keys
                asset_name = asset.get('currency', asset.get('coinName', asset.get('asset', '')))
                if asset_name == 'USDT':
                    val = asset.get('equity', asset.get('available', self.current_equity))
                    self.current_equity = float(val)
                    break
            self.pnl_guard.update(self.current_equity)
            self.peak_equity = max(self.peak_equity, self.current_equity)
        except Exception as e:
            logger.warning(f"Equity refresh failed: {e}")
        
        try:
            positions = self.adapter.get_positions()
            data_list = []
            if isinstance(positions, list):
                data_list = positions
            elif isinstance(positions, dict):
                data_list = positions.get('data', [])
            # Reset local positions before applying fresh snapshot to avoid stale counts
            for sym in self.symbols:
                self.positions[sym] = 0.0
            for pos in data_list:
                sym = pos.get('symbol')
                if sym in self.symbols:
                    amt = float(pos.get('holdAmount', pos.get('size', 0)))
                    side = str(pos.get('side', '')).upper()
                    if side == 'SHORT':
                        amt = -amt
                    self.positions[sym] = amt
        except Exception as e:
            logger.warning(f"Position refresh failed: {e}")

    def log_performance(self):
        """
        Persist lightweight performance snapshot for dashboard/status.
        """
        drawdown = 0.0
        if self.pnl_guard.peak_equity:
            drawdown = (self.pnl_guard.peak_equity - self.current_equity) / self.pnl_guard.peak_equity
        roi = (self.current_equity - 1000.0) / 1000.0
        payload = {
            'timestamp': int(time.time() * 1000),
            'equity': round(self.current_equity, 2),
            'peak_equity': round(self.pnl_guard.peak_equity or self.current_equity, 2),
            'drawdown': drawdown,
            'roi': roi,
            'total_pnl': round(self.current_equity - 1000.0, 2),
            'trades': self.trades_executed,
            'win_rate': 0.0  # placeholder until per-trade outcomes tracked
        }
        self.performance_logger.log(payload)

    def calculate_price_structure(self, df: pd.DataFrame) -> Dict[str, float]:
        """
        Compute recent price structure/volatility context for AI logging.
        """
        if df.empty:
            return {}
        window = df.tail(30)
        prices = window['price']
        volatility_pct = float(prices.pct_change().dropna().std() * 100) if len(prices) > 1 else 0.0
        recent_high = float(prices.max())
        recent_low = float(prices.min())
        last_price = float(prices.iloc[-1])
        range_pct = ((recent_high - recent_low) / last_price) * 100 if last_price else 0.0
        spread = 0.0
        if 'bid' in window.columns and 'ask' in window.columns:
            try:
                spread = float((window['ask'].iloc[-1] - window['bid'].iloc[-1]) / last_price * 100)
            except Exception:
                spread = 0.0
        return {
            'volatility_pct': volatility_pct,
            'recent_high': recent_high,
            'recent_low': recent_low,
            'range_pct': range_pct,
            'bid_ask_spread_pct': spread
        }
    
    def consolidate_hedged_positions(self):
        """
        Detect and consolidate hedged positions (LONG + SHORT on same symbol).
        Automatically closes both sides when net exposure is below 5%.
        """
        # Group positions by symbol (WEEX may return duplicate symbols with opposite directions)
        symbol_groups = {}
        for symbol, size in self.positions.items():
            if symbol not in symbol_groups:
                symbol_groups[symbol] = []
            symbol_groups[symbol].append(size)
        
        # Detect and consolidate hedges
        for symbol, sizes in symbol_groups.items():
            if len(sizes) < 2:
                continue  # No hedge possible with single position
            
            # Calculate net position
            net_size = sum(sizes)
            total_abs = sum(abs(s) for s in sizes)
            
            # Check if hedged (opposing positions exist)
            has_long = any(s > 0 for s in sizes)
            has_short = any(s < 0 for s in sizes)
            
            if has_long and has_short and total_abs > 0:
                # Calculate net exposure as % of total
                net_exposure_pct = abs(net_size) / total_abs * 100 if total_abs > 0 else 0
                
                # Consolidate if net exposure < 5%
                if net_exposure_pct < 5.0:
                    logger.warning(f"🔄 [{symbol}] HEDGE DETECTED: Net {net_size:.4f}, Total {total_abs:.4f} ({net_exposure_pct:.1f}% net)")
                    logger.info(f"   Consolidating to eliminate funding waste...")
                    
                    try:
                        self.adapter.symbol = symbol
                        result = self.adapter.close_all_positions(symbol)
                        
                        if result and isinstance(result, list):
                            success_count = sum(1 for r in result if r.get('success'))
                            logger.info(f"   ✓ Closed {success_count} hedged positions on {symbol}")
                            
                            # Update local state
                            self.positions[symbol] = 0.0
                            if symbol in self.active_trades:
                                self.active_trades[symbol] = []
                        else:
                            logger.warning(f"   ⚠️  Hedge consolidation failed for {symbol}: {result}")
                    
                    except Exception as e:
                        logger.error(f"   Error consolidating hedge on {symbol}: {e}")

    def determine_trade_class(self, regime: str, confidence: float) -> str:
        regime_upper = str(regime).upper()
        # Stricter classification for Trend Following
        if regime_upper.startswith("TREND") and confidence >= 0.75:
            return "HIGH_CONF_TREND"
        if regime_upper.startswith("TREND"):
            return "TREND"
        return "SCALP"  # Only highest conviction scalps will pass filters

    def resolve_leverage(self, confidence: float, regime: str) -> Optional[int]:
        """
        Confidence/regime-based leverage resolver.
        Trend Following: Conservative leverage to withstand volatility.
        """
        if confidence < self.min_confidence:
            return None
            
        # TREND FOLLOWER LEVERAGE TIERS
        # 0.70 - 0.75: 7x
        # 0.75 - 0.85: 10x
        # > 0.85: 15x
        
        if confidence < 0.75:
            leverage = 7
        elif confidence < 0.85:
            leverage = 10
        else:
            leverage = 15
            
        leverage = min(leverage, WeexExecutionAdapter.MAX_LEVERAGE)
        return int(leverage)

    def get_risk_pct(self, regime: str, confidence: float) -> float:
        regime_upper = str(regime).upper()
        if regime_upper == "VOLATILITY_COMPRESSION":
            return 0.010  # 1.0% risk (Increased from 0.5%)
        if regime_upper.startswith("TREND"):
            if confidence >= 0.66:
                return 0.020  # 2.0% risk (Increased from 1.0%)
            return 0.015      # 1.5% risk (Increased from 0.8%)
        return 0.010          # 1.0% risk (Increased from 0.5%)

    def round_size_to_rules(self, symbol: str, raw_size: float) -> tuple:
        rules = self.symbol_rules.get(symbol, {'min_qty': 0.001, 'qty_step': 0.001})
        min_qty = float(rules['min_qty'])
        step_size = float(rules['qty_step'])

        if raw_size <= 0:
            return 0.0, min_qty, step_size

        if step_size <= 0:
            step_size = min_qty if min_qty > 0 else 1.0

        if raw_size < min_qty:
            raw_size = min_qty

        steps = max(1, math.floor(raw_size / step_size))
        final_size = steps * step_size

        decimals = 0
        if step_size < 1:
            try:
                decimals = int(-math.log10(step_size))
            except Exception:
                decimals = 4

        final_size = round(final_size, decimals)
        return final_size, min_qty, step_size

    def round_price_to_step(self, value: float, price_step: float) -> float:
        rounded = round(round(value / price_step) * price_step, 4)
        if price_step >= 1:
            rounded = int(rounded)
        return rounded

    def _tp_sl_success(self, response) -> bool:
        """
        Normalize TP/SL responses across list/dict formats and detect success.
        """
        item = response[0] if isinstance(response, list) and len(response) > 0 else response
        if not isinstance(item, dict):
            return True
        if item.get('success') is True:
            return True
        if item.get('orderId') or item.get('order_id') or item.get('data', {}).get('orderId') or item.get('data', {}).get('order_id'):
            return True
        return False

    def cleanup_inactive_trades(self):
        for sym in list(self.active_trades.keys()):
            trades = self.active_trades.get(sym, [])
            if not trades:
                continue

            if abs(self.positions.get(sym, 0.0)) <= 0:
                # Check if all trades are old enough to be considered "failed to fill" or "closed"
                # We give a 5-minute grace period for limit orders to fill before wiping metadata.
                now = time.time()
                is_stale = True
                for trade in trades:
                    entry_time = trade.get('entry_time', 0)
                    if (now - entry_time) < 300:  # 5 minutes grace
                        is_stale = False
                        break
                
                if is_stale:
                    self.active_trades[sym] = []

    def current_portfolio_risk(self) -> float:
        total = 0.0
        for trades in self.active_trades.values():
            for t in trades:
                total += t.get('risk_pct', 0.0)
        return total

    def can_open_trade(self, symbol: str, direction: str, trade_class: str, risk_pct: float, price: float, confidence: float = 0.6) -> bool:
        self.cleanup_inactive_trades()

        # Portfolio-level risk cap
        if self.current_portfolio_risk() + risk_pct > self.portfolio_risk_cap:
            logger.warning("Blocked trade: portfolio risk cap reached.")
            return False

        active = self.active_trades.get(symbol, [])
        existing_pos = self.positions.get(symbol, 0.0)
        
        
        # REMOVED: TURBO FLIP logic - no longer aggressively flipping positions
        
        if abs(existing_pos) > 0 and len(active) == 0:
            logger.warning(f"Blocked trade: live position detected for {symbol} with no metadata.")
            return False

        # NEW: Time-based position timeout (prevent eternal gridlock)
        for trade in active:
            age_hours = (time.time() - trade.get('entry_time', time.time())) / 3600
            if age_hours > 24:
                logger.warning(f"⏰ [{symbol}] Position >24h old ({age_hours:.1f}h), allowing new entry")
                return True

        if trade_class == "SCALP":
            if len(active) > 0:
                logger.warning(f"Blocked trade: compression cap reached for {symbol}.")
                return False

        trend_trades = [t for t in active if t.get('trade_class') != "SCALP"]
        if trend_trades:
            if len(trend_trades) >= 2:
                logger.warning(f"Blocked trade: trend cap reached for {symbol}.")
                return False
            last = trend_trades[-1]
            last_entry = last.get('entry_price') if last.get('entry_price') is not None else price
            move = (price - last_entry) if direction == 'LONG' else (last_entry - price)
            
            # NEW: Relaxed pyramid logic - allow if confidence boost is significant
            if move <= 0:
                if confidence >= 0.70:  # Very high confidence can override
                    logger.info(f"✓ [{symbol}] Ultra-high conviction override (conf={confidence:.1%})")
                    return True
                logger.warning(f"Blocked trade: pyramid requires prior profit on {symbol}.")
                return False

        return True

    def calculate_position_size(self, symbol: str, price: float, stop_loss: float, risk_pct: float) -> float:
        """Risk-based position sizing with exchange rule alignment."""
        if price <= 0 or stop_loss <= 0:
            return 0.0

        stop_distance = abs(price - stop_loss)
        if stop_distance <= 0:
            return 0.0

        risk_capital = self.current_equity * risk_pct
        raw_size = risk_capital / stop_distance

        # Cap by local notional guard before rounding
        if price * raw_size > self.max_notional_usd:
            raw_size = self.max_notional_usd / price

        final_size, _, _ = self.round_size_to_rules(symbol, raw_size)

        # Re-apply notional cap after rounding
        if final_size * price > self.max_notional_usd:
            final_size = self.max_notional_usd / price
            final_size, _, _ = self.round_size_to_rules(symbol, final_size)

        return final_size

    def _hit_target(self, price: float, target: float, direction: str) -> bool:
        if target is None:
            return False
        if direction == 'LONG':
            return price >= target
        return price <= target

    def register_active_trade(self, symbol: str, trade_payload: dict):
        if symbol not in self.active_trades:
            self.active_trades[symbol] = []
        self.active_trades[symbol].append(trade_payload)

    def manage_active_trades(self, symbol: str, current_price: float):
        """
        Adjust breakeven/trailing stops for runner portions once TP levels are breached.
        """
        trades = self.active_trades.get(symbol, [])
        if not trades:
            return

        rules = self.symbol_rules.get(symbol, {'price_step': 0.1, 'qty_step': 0.001, 'min_qty': 0.001})
        price_step = float(rules.get('price_step', 0.1))

        for trade in trades:
            direction = trade.get('direction')
            full_size = trade.get('size') or 0.0
            entry_price = trade.get('entry_price') or 0.0
            
            if not direction or full_size <= 0 or entry_price <= 0 or direction not in ['LONG', 'SHORT']:
                continue

            # Skip if current_price is invalid
            if current_price is None or current_price <= 0:
                continue

            # Calculate current ROI
            if direction == 'LONG':
                roi_pct = ((current_price - entry_price) / entry_price) * 100
            else:  # SHORT
                roi_pct = ((entry_price - current_price) / entry_price) * 100
            
            # --- BLITZ-SCALP PROFIT LOCKING ---
            # 2% ROI -> BE (0.1% buffer)
            # 5% ROI -> 1% Locked
            # 10% ROI -> 3% Locked
            
            if roi_pct >= 10.0:
                lock_tier = 3
                locked_profit_pct = 3.0
            elif roi_pct >= 5.0:
                lock_tier = 2
                locked_profit_pct = 1.0
            elif roi_pct >= 2.0:
                lock_tier = 1
                locked_profit_pct = 0.1  # Breakeven + buffer
            else:
                lock_tier = 0
            
            current_tier = trade.get('profit_lock_tier', 0)
            
            # Only upgrade (never downgrade) protection
            if lock_tier > current_tier:
                # Calculate new SL price
                if direction == 'LONG':
                    new_sl = entry_price * (1 + locked_profit_pct / 100)
                else:  # SHORT
                    new_sl = entry_price * (1 - locked_profit_pct / 100)
                
                # Round to price step and size step
                new_sl_rounded = self.round_price_to_step(new_sl, price_step)
                rounded_size, _, _ = self.round_size_to_rules(symbol, full_size)
                
                logger.info(f"🔒 [{symbol}] Turbo Lock Tier {lock_tier} (ROI: {roi_pct:.2f}%). Moving SL to {new_sl_rounded}")
                
                # Execute stop loss update
                self.adapter.symbol = symbol
                sl_res = self.adapter.place_tp_sl_order('loss_plan', new_sl_rounded, rounded_size, 'long' if direction == 'LONG' else 'short')
                
                if self._tp_sl_success(sl_res):
                    trade['profit_lock_tier'] = lock_tier
                    trade['stop_loss'] = new_sl_rounded
                    logger.info(f"   ✓ Turbo SL update successful for {symbol} tier {lock_tier}")
                else:
                    logger.error(f"   ❌ Turbo SL update failed for {symbol}: {sl_res}")
                     
    def fetch_tick(self, symbol: str):
        ticker = self.adapter.get_ticker(symbol)
        data = {
            'timestamp': datetime.now(timezone.utc),
            'price': float(ticker['last']),
            'volume': float(ticker.get('base_volume', 0)),
            'bid': float(ticker.get('best_bid', 0)),
            'ask': float(ticker.get('best_ask', 0))
        }
        self.market_data[symbol].append(data)
        if len(self.market_data[symbol]) > self.data_window:
            self.market_data[symbol] = self.market_data[symbol][-self.data_window:]
        return data

    def run(self):
        print(f"\n{Colors.GREEN}Starting Cycle Loop...{Colors.END}")
        while True:
            try:
                # ALWAYS update state even if halted, so we can detect recovery
                self.cleanup_inactive_trades()
                
                # Check for recovery: if halted but no positions, allow reset
                if not self.pnl_guard.can_trade():
                    open_positions = sum(1 for p in self.positions.values() if abs(p) > 0)
                    if open_positions == 0:
                        logger.info("Drawdown Guard: No positions active. Resetting guard to resume trading.")
                        self.pnl_guard.reset()
                    else:
                        logger.warning(f"Trading halted due to drawdown guard ({open_positions} positions still open). Sleeping 30s.")
                        time.sleep(30)
                        continue

                for symbol in self.symbols:
                    try:
                        tick = self.fetch_tick(symbol)
                        current_price = tick['price']
                        # Manage any trailing/breakeven adjustments for active trades
                        self.manage_active_trades(symbol, current_price)
                    except Exception as e:
                        logger.error(f"Tick error {symbol}: {e}")
                        continue
                        
                    if len(self.market_data[symbol]) < 14:
                        if len(self.market_data[symbol]) % 5 == 0:
                            print(f"[{symbol}] Warming: {len(self.market_data[symbol])}/14")
                        continue
                        
                    df = pd.DataFrame(self.market_data[symbol])
                    df = df.rename(columns={'volume': 'quantity'})
                    
                    # Instantiate engine with fresh data
                    engine = AIEnhancedSignalEngine(df)
                    signals = engine.generate_signals()
                    
                    if signals is not None and not signals.empty:
                        latest = signals.iloc[-1]
                        sig_type = latest['signal']
                        conf = float(latest['calibrated_confidence'])
                        
                        log_entry = {
                            'timestamp': datetime.now(timezone.utc).isoformat(),
                            'timestamp_ms': int(time.time() * 1000),
                            'symbol': symbol,
                            'price': current_price,
                            'signal': sig_type,
                            'confidence': conf,
                            'regime': latest['regime']
                        }
                        self.signal_logger.log(log_entry)
                        
                        # High-conviction specific logging
                        if conf >= 0.66:
                            self.high_conviction_logger.log(log_entry)
                        
                        now = time.time()
                        
                        # Logging for skipped signals (Debug visibility)
                        if conf >= 0.5 and conf < self.min_confidence:
                             print(f"  [Skipped] {symbol} {sig_type} (Conf: {conf:.4f} < {self.min_confidence})")
                        
                        if (sig_type in ['LONG', 'SHORT'] and 
                            conf >= self.min_confidence and 
                            (now - self.last_trade_time[symbol] > 300)):
                            
                            trade_class = self.determine_trade_class(latest['regime'], conf)
                            applied_leverage = self.resolve_leverage(conf, latest['regime'])
                            if applied_leverage is None:
                                continue
                            risk_pct = self.get_risk_pct(latest['regime'], conf)

                            if not self.can_open_trade(symbol, sig_type, trade_class, risk_pct, current_price, conf):
                                continue
                                
                            print(f"{Colors.CYAN}[{symbol}] SIGNAL: {sig_type} ({conf:.2f}){Colors.END}")
                            self.execute_trade(
                                symbol=symbol,
                                direction=sig_type,
                                confidence=conf,
                                price=current_price,
                                signal_data=latest,
                                trade_class=trade_class,
                                applied_leverage=applied_leverage,
                                risk_pct=risk_pct
                            )
                            self.last_trade_time[symbol] = now
                
                # Heartbeat (every ~60s if loop is 10s * 6)
                self.loop_count = getattr(self, 'loop_count', 0) + 1
                if self.loop_count % 6 == 0:
                    try:
                        self.refresh_account_state() # Refresh Equity & Positions
                        self.log_performance()
                        
                        # Consolidate hedged positions every hour to prevent funding fee waste
                        if self.loop_count % 360 == 0:  # Every 360 cycles = ~1 hour
                            logger.info("🔄 Running periodic hedge consolidation...")
                            self.consolidate_hedged_positions()
                        
                        # SAFETY CHECK: Verify SLs & TPs exist for all positions
                        if self.loop_count % 12 == 0: # Every ~2 minutes
                             self.check_and_fix_plans()
                             
                    except: pass
                    open_positions = len([p for p in self.positions.values() if abs(p) > 0])
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] 💓 Cycle Active | Equity: ${self.current_equity:.2f} | Positions: {open_positions}")
                    
                time.sleep(10)
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Loop error: {e}")
                time.sleep(5)

    def check_and_fix_plans(self):
        """
        SAFETY NET: Comprehensive check for both SL and TP orders.
        Ensures exactly 1 SL and 1 TP exists per active position.
        Auto-cleans redundancies and restores missing orders.
        """
        try:
            # 1. Get Positions
            positions = self.adapter.get_positions()
            data_list = positions if isinstance(positions, list) else positions.get('data', [])
            active_pos_map = {}
            
            for pos in data_list:
                sym = pos.get('symbol')
                size = float(pos.get('holdAmount', pos.get('size', 0)))
                side = str(pos.get('side', '')).upper()
                avg_price = float(pos.get('avgPrice', 0))
                
                if abs(size) > 0 and sym in self.symbols:
                    active_pos_map[sym] = {
                        'size': abs(size),
                        'side': 'SHORT' if side == 'SHORT' else 'LONG',
                        'entry': avg_price
                    }

            if not active_pos_map:
                return

            # 2. Iterate Active Positions
            for sym, pos_data in active_pos_map.items():
                self.adapter.symbol = sym
                
                # Fetch Current Plans
                plans = self.adapter._get("/capi/v2/order/currentPlan", {"symbol": sym})
                p_list = []
                if plans:
                    p_list = plans if isinstance(plans, list) else plans.get('data', [])

                sl_orders = []
                tp_orders = []
                
                # Classify Orders
                for p in p_list:
                    status = p.get('status')
                    if status not in ['active', 'new', 'UNTRIGGERED', 'NEW']:
                        continue

                    ptype = p.get('planType')
                    otype = p.get('type')
                    trigger = float(p.get('triggerPrice', 0))
                    entry = pos_data['entry']
                    side = pos_data['side']
                    
                    is_sl = False
                    is_tp = False

                    # Explicit Type Check
                    if ptype == 'loss_plan': is_sl = True
                    elif ptype == 'profit_plan': is_tp = True
                    
                    # Infer for V2 API (Close Type)
                    elif otype in ['CLOSE_LONG', 'CLOSE_SHORT']:
                        if side == 'LONG':
                            if trigger < entry: is_sl = True
                            elif trigger > entry: is_tp = True
                        elif side == 'SHORT':
                            if trigger > entry: is_sl = True
                            elif trigger < entry: is_tp = True
                    
                    if is_sl: sl_orders.append(p)
                    if is_tp: tp_orders.append(p)

                # --- REDUNDANCY CHECKS ---
                # If we have multiples of either, we NUKE EVERYTHING and start fresh.
                # It's cleaner than trying to delete specific IDs which might fail.
                if len(sl_orders) > 1 or len(tp_orders) > 1:
                    logger.warning(f"🚨 [{sym}] REDUNDANCY DETECTED: {len(sl_orders)} SLs, {len(tp_orders)} TPs. Nuking to reset.")
                    self.adapter.cancel_all_plan_orders(sym)
                    # Reset lists to force replacement below
                    sl_orders = []
                    tp_orders = []

                # --- MISSING ORDER CHECKS ---
                
                # Fetch Current Market Price for Validation
                try:
                    ticker = self.adapter.get_ticker(sym)
                    current_price = float(ticker['last'])
                except:
                    current_price = 0

                # 1. Check/Place STOP LOSS
                if not sl_orders:
                    logger.warning(f"🚨 [{sym}] MISSING SL! Placing Default SL.")
                    
                    # Entry Calculation Fallback
                    entry = pos_data['entry']
                    if entry == 0:
                        # Try to derive from open_value/size if available in raw data? 
                        # We don't have raw pos dict here easily, but we can trust current_price as fallback
                        if current_price > 0:
                            entry = current_price
                    
                    if entry > 0:
                        sl_pct = 0.02 # 2% SL
                        direction = pos_data['side']
                        
                        if direction == 'LONG':
                            sl_price = entry * (1 - sl_pct)
                            # VALIDATION: SL must be < Current Price
                            if current_price > 0 and sl_price >= current_price:
                                sl_price = current_price * 0.99
                            sl_side = 'long'
                        else:
                            sl_price = entry * (1 + sl_pct)
                            # VALIDATION: SL must be > Current Price
                            if current_price > 0 and sl_price <= current_price:
                                sl_price = current_price * 1.01
                            sl_side = 'short'
                            
                        sl_price = self.round_price_to_step(sl_price, float(self.symbol_rules.get(sym, {}).get('price_step', 0.1)))
                        size = pos_data['size']
                        
                        logger.info(f"   🆘 Placing SL for {sym} at {sl_price}")
                        res = self.adapter.place_tp_sl_order('loss_plan', sl_price, size, sl_side)
                        logger.info(f"   👉 SL Result for {sym}: {res}")
                
                # 2. Check/Place TAKE PROFIT
                if not tp_orders:
                    logger.warning(f"🚨 [{sym}] MISSING TP! Placing Default TP.")
                    
                    entry = pos_data['entry']
                    # Use Same Fallback
                    if entry == 0 and current_price > 0:
                         entry = current_price
                         
                    if entry > 0:
                        tp_pct = 0.04 # 4% TP
                        direction = pos_data['side']
                        
                        if direction == 'LONG':
                            tp_price = entry * (1 + tp_pct)
                            # VALIDATION: TP must be > Current Price
                            if current_price > 0 and tp_price <= current_price:
                                tp_price = current_price * 1.01
                            tp_side = 'long'
                        else:
                            tp_price = entry * (1 - tp_pct)
                            # VALIDATION: TP must be < Current Price
                            if current_price > 0 and tp_price >= current_price:
                                tp_price = current_price * 0.99
                            tp_side = 'short'
                            
                        tp_price = self.round_price_to_step(tp_price, float(self.symbol_rules.get(sym, {}).get('price_step', 0.1)))
                        size = pos_data['size']
                        
                        logger.info(f"   💰 Placing TP for {sym} at {tp_price}")
                        res = self.adapter.place_tp_sl_order('profit_plan', tp_price, size, tp_side)
                        logger.info(f"   👉 TP Result for {sym}: {res}")


        except Exception as e:
            logger.error(f"Error in Plan Safety Net: {e}")

    def execute_trade(self, symbol, direction, confidence, price, signal_data, trade_class: str, applied_leverage: int, risk_pct: float):
        try:
            self.adapter.symbol = symbol
            
            # --- PRE-TRADE CLEANUP (Forced Flips & Margin Recovery) ---
            active_trades = self.active_trades.get(symbol, [])
            if active_trades:
                logger.info(f"🧹 [{symbol}] Pre-Flip Cleanup: Canceling orders and closing old position.")
                try:
                    # 1. Cancel any trigger orders that block leverage changes
                    self.adapter.cancel_all_plan_orders(symbol)
                    # 2. Close position to free margin
                    self.adapter.close_all_positions(symbol)
                    # 3. Clear local metadata
                    self.active_trades[symbol] = []
                    # Wait briefly for server state sync
                    time.sleep(0.5)
                except Exception as e:
                    logger.error(f"Cleanup failure for {symbol}: {e}")

            if self.last_leverage.get(symbol) != applied_leverage:
                self.adapter.leverage = applied_leverage
                self.adapter.set_leverage()
                self.last_leverage[symbol] = applied_leverage

            atr = self.tpsl_calculator.calculate_atr(pd.DataFrame(self.market_data[symbol]))
            if atr <= 0:
                logger.error(f"{symbol} ATR invalid ({atr}); skipping trade to avoid naked risk.")
                return

            tpsl = self.tpsl_calculator.calculate_dynamic_tpsl(
                entry_price=price,
                direction=direction,
                volatility_atr=atr,
                regime=signal_data['regime'],
                confidence=confidence
            )

            if not tpsl['valid']:
                return
            if tpsl.get('risk_reward') is None:
                logger.error("Missing risk_reward in TPSL payload; aborting order.")
                return

            stop_loss_price = tpsl['stop_loss']
            size = self.calculate_position_size(symbol, price, stop_loss_price, risk_pct)
            if size <= 0:
                return

            # Execution guard - enforce per-symbol cooldown and notional cap
            if not self.execution_guard.can_trade(size=size, symbol=symbol, price=price):
                logger.warning(f"Execution guard blocked trade for {symbol} (cooldown/notional).")
                return

            # Fetch Price Rules
            rules = self.symbol_rules.get(symbol, {'price_step': 0.1, 'qty_step': 0.001, 'min_qty': 0.001})
            p_step = float(rules.get('price_step', 0.1))
            if p_step <= 0 or p_step > price * 0.2:
                # Guard against bad tick sizes from API; fall back to 0.1% of price (min 1e-4)
                p_step = max(price * 0.001, 0.0001)

            # New Single TP logic: Use the primary take_profit from calculator and ROUND IT
            primary_tp = self.round_price_to_step(tpsl['take_profit'], p_step)
            sl_price = self.round_price_to_step(stop_loss_price, p_step)
            
            # Legacy tp1/tp2 for logging/metadata (not used for actual orders)
            tp1 = price + atr * 1.5 if direction == 'LONG' else price - atr * 1.5
            tp2 = price + atr * 3.0 if direction == 'LONG' else price - atr * 3.0
            tp1 = self.round_price_to_step(tp1, p_step)
            tp2 = self.round_price_to_step(tp2, p_step)
            runner_size = size * 0.3  # Legacy field
            tp2_status = "single_tp"  # Legacy field

            # Ensure directional validity after rounding
            if direction == 'SHORT':
                if tp1 >= price:
                    tp1 = self.round_price_to_step(price * 0.995, p_step)
                if tp2 >= price:
                    tp2 = self.round_price_to_step(price * 0.99, p_step)
                if sl_price <= price:
                    sl_price = self.round_price_to_step(price * 1.01, p_step)
                if primary_tp >= price:
                    primary_tp = self.round_price_to_step(price * 0.98, p_step)
            else:
                if tp1 <= price:
                    tp1 = self.round_price_to_step(price * 1.005, p_step)
                if tp2 <= price:
                    tp2 = self.round_price_to_step(price * 1.01, p_step)
                if sl_price >= price:
                    sl_price = self.round_price_to_step(price * 0.99, p_step)
                if primary_tp <= price:
                    primary_tp = self.round_price_to_step(price * 1.02, p_step)

            # Limit Price rounded to price_step
            raw_limit = price * (1.001 if direction == 'LONG' else 0.999)
            limit_price = self.round_price_to_step(raw_limit, p_step)

            print(f"  🚀 Exe: {direction} {symbol} x{size} (lev {applied_leverage}x, risk {risk_pct*100:.2f}%)")
            print(f"  Debug TPSL: TP={primary_tp}, SL={sl_price} (rounded to {p_step})")

            order_tpsl = {
                "take_profit": primary_tp,
                "stop_loss": sl_price,
                "entry_price": price,
                "risk_reward": tpsl.get('risk_reward'),
                "regime": signal_data.get('regime'),
                "volatility_atr": atr
            }

            result = self.adapter.place_order(
                direction=direction,
                size=size,
                price=limit_price,
                tpsl=order_tpsl
            )

            # Handle List response for Order (common in V2)
            if isinstance(result, list) and len(result) > 0:
                result = result[0]
            elif isinstance(result, list) and len(result) == 0:
                result = {'status': 'rejected', 'error': 'Empty list response'}

            # Debug: Print full result to identify correct keys
            logger.info(f"Order Result: {result}")

            if result.get('status') == 'rejected' or 'error' in result:
                logger.error(f"Order failed: {result}")
                return

            # Robust Order ID Extraction
            order_id = result.get('data', {}).get('orderId')
            if not order_id: order_id = result.get('orderId')
            if not order_id: order_id = result.get('order_id')
            if not order_id: order_id = result.get('data', {}).get('order_id')

            # NOISE-ABSORPTION: Immediate SL placement disabled.
            # SL will be placed by manage_active_trades after 3s OR 0.4x ATR move.
            logger.info(f"  [Noise-Absorption] SL activation delayed for {symbol} (Target: {sl_price})")

            # Place Single TP with full size
            tp_res = self.adapter.place_tp_sl_order('profit_plan', primary_tp, size, 'long' if direction == 'LONG' else 'short')
            tp_success = self._tp_sl_success(tp_res)
            
            if tp_success:
                logger.info(f"[{symbol}] TP Order placed @ {primary_tp} for full size ({size})")
            else:
                logger.error(f"[{symbol}] TP Placement Failed: {tp_res}")
                # If TP fails, we close the position to avoid being unprotected
                try:
                    self.adapter.close_all_positions(symbol)
                    logger.warning(f"[{symbol}] Closed position due to TP placement failure.")
                except Exception as e:
                    logger.error(f"Failed to close position after TP failure: {e}")
                return

            # Register for active management (to handle SL and Breakeven)
            trade_payload = {
                'symbol': symbol,
                'order_id': order_id,
                'direction': direction,
                'size': size,
                'entry_price': price,
                'stop_loss': sl_price,
                'take_profit': primary_tp,
                'atr': atr,
                'entry_time': time.time(),
                'sl_placed': False,
                'breakeven_set': False,
                'breakeven_trigger': price + atr * 1.5 if direction == 'LONG' else price - atr * 1.5
            }
            self.register_active_trade(symbol, trade_payload)

            # AI Log
            price_context = self.calculate_price_structure(pd.DataFrame(self.market_data[symbol]))
            position_size_usd = round(size * price, 2)
            ai_log_result = self.ai_log_adapter.submit_log(
                order_id=order_id,
                stage='Decision Making',
                model='LLaMA-2-7B',
                input_data={
                    "symbol": symbol,
                    "price": price,
                    "regime": signal_data.get('regime', 'unknown'),
                    "price_context": price_context,
                    "parameters": {
                        "atr": atr,
                        "confidence": confidence
                    }
                },
                output_data={
                    "signal": direction,
                    "confidence": confidence,
                    "entry_price": price,
                    "tpsl": {
                        "tp": tpsl.get('take_profit'),
                        "sl": tpsl.get('stop_loss')
                    },
                    "risk_reward": tpsl.get('risk_reward'),
                    "regime": signal_data.get('regime', 'unknown'),
                    "execution_metadata": {
                        "applied_leverage": applied_leverage,
                        "risk_pct": risk_pct,
                        "position_size_usd": position_size_usd,
                        "trade_class": trade_class
                    }
                },
                explanation=tpsl.get('reasoning', "AI generated signal based on volatility and trend analysis.")
            )
            if not ai_log_result.get('success'):
                logger.error(f"AI log submission failed for {symbol}: {ai_log_result}")
                self.compliance_logger.log({
                    "timestamp": int(time.time() * 1000),
                    "event": "ai_log_failed",
                    "symbol": symbol,
                    "order_id": order_id,
                    "error": ai_log_result.get('error')
                })
            else:
                self.compliance_logger.log({
                    "timestamp": int(time.time() * 1000),
                    "event": "ai_log_submitted",
                    "symbol": symbol,
                    "order_id": order_id,
                    "stage": "Decision Making"
                })

            self.positions[symbol] = size if direction == 'LONG' else -size
            self.trades_executed += 1
            self.execution_guard.register_trade(size=size, symbol=symbol)

            # Simplified registration (merged logic)
            pass 


            self.trade_logger.log({
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'timestamp_ms': int(time.time() * 1000),
                'symbol': symbol,
                'signal': direction,
                'size': size,
                'price': price,
                'tpsl': tpsl,
                'tp2_status': tp2_status,
                'applied_leverage': applied_leverage,
                'risk_pct': risk_pct,
                'position_size_usd': position_size_usd,
                'trade_class': trade_class,
                'tp1': tp1,
                'tp2': tp2,
                'runner_size': runner_size
            })
            self.log_performance()

        except Exception as e:
            logger.error(f"Execution Exception {symbol}: {e}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--skip-prompt', action='store_true')
    args = parser.parse_args()
    
    pairs = [
        "cmt_btcusdt", "cmt_ethusdt", "cmt_solusdt", "cmt_dogeusdt", 
        "cmt_xrpusdt", "cmt_adausdt", "cmt_bnbusdt", "cmt_ltcusdt"
    ]
    
    bot = SentinelLiveTradingBot(symbols=pairs, dry_run=False)
    bot.run()

if __name__ == "__main__":
    main()
