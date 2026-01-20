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
                 min_confidence: float = 0.52,
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
        
        self.tpsl_calculator = TPSLCalculator(
            min_rr_ratio=1.2, max_rr_ratio=3.0, base_sl_multiplier=1.0, base_tp_multiplier=2.0
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
                 if asset.get('currency') == 'USDT' or asset.get('asset') == 'USDT':
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
                if asset.get('currency') == 'USDT' or asset.get('asset') == 'USDT':
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

    def determine_trade_class(self, regime: str, confidence: float) -> str:
        regime_upper = str(regime).upper()
        if regime_upper.startswith("TREND") and confidence >= 0.62:
            return "HIGH_CONF_TREND"
        if regime_upper.startswith("TREND"):
            return "TREND"
        if regime_upper == "VOLATILITY_COMPRESSION":
            return "SCALP"
        return "SCALP"

    def resolve_leverage(self, confidence: float, regime: str) -> Optional[int]:
        """
        Confidence/regime-based leverage resolver with hard caps (10x-20x for 0.62+ threshold).
        Returns None when the trade should be rejected.
        """
        if confidence < self.min_confidence:
            return None
            
        regime_upper = str(regime).upper()
        
        # Optimized mapping for 0.62+ confidence range
        if confidence < 0.65:
            leverage = 10  # Base tier for minimum confidence
        elif confidence < 0.70:
            leverage = 15  # Strong confidence
        else:
            leverage = 20  # Exceptional confidence
            
        # Boost for TRENDING markets (these are typically highest conviction)
        if regime_upper.startswith("TREND") and confidence >= 0.65:
            leverage = min(leverage + 5, WeexExecutionAdapter.MAX_LEVERAGE)
            
        # Safety cap for compression/noise to prevent high-leverage whipsaws
        if regime_upper == "VOLATILITY_COMPRESSION":
            leverage = min(leverage, 15)  # Max 15x for compression
            
        leverage = max(leverage, 10)  # Floor at 10x for 0.62+ signals
        leverage = min(leverage, WeexExecutionAdapter.MAX_LEVERAGE)
        return int(leverage)

    def get_risk_pct(self, regime: str, confidence: float) -> float:
        regime_upper = str(regime).upper()
        if regime_upper == "VOLATILITY_COMPRESSION":
            return 0.005
        if regime_upper.startswith("TREND"):
            if confidence >= 0.62:
                return 0.01
            return 0.008
        return 0.005

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
            if abs(self.positions.get(sym, 0.0)) <= 0:
                if self.active_trades.get(sym):
                    self.active_trades[sym] = []

    def current_portfolio_risk(self) -> float:
        total = 0.0
        for trades in self.active_trades.values():
            for t in trades:
                total += t.get('risk_pct', 0.0)
        return total

    def can_open_trade(self, symbol: str, direction: str, trade_class: str, risk_pct: float, price: float) -> bool:
        self.cleanup_inactive_trades()

        # Portfolio-level risk cap
        if self.current_portfolio_risk() + risk_pct > self.portfolio_risk_cap:
            logger.warning("Blocked trade: portfolio risk cap reached.")
            return False

        active = self.active_trades.get(symbol, [])
        existing_pos = self.positions.get(symbol, 0.0)
        if abs(existing_pos) > 0 and len(active) == 0:
            logger.warning(f"Blocked trade: live position detected for {symbol} with no metadata.")
            return False

        if trade_class == "SCALP":
            if len(active) > 0:
                logger.warning(f"Blocked trade: compression cap reached for {symbol}.")
                return False

        trend_trades = [t for t in active if t.get('trade_class') != "SCALP"]
        if trend_trades:
            directions = {t.get('direction') for t in trend_trades}
            if directions and direction not in directions:
                logger.warning(f"Blocked trade: conflicting direction for {symbol}.")
                return False
            if len(trend_trades) >= 2:
                logger.warning(f"Blocked trade: trend cap reached for {symbol}.")
                return False
            last = trend_trades[-1]
            last_entry = last.get('entry_price') if last.get('entry_price') is not None else price
            move = (price - last_entry) if direction == 'LONG' else (last_entry - price)
            if move <= 0:
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
            runner_size = trade.get('runner_size', 0.0)
            full_size = trade.get('size', 0.0)
            atr = trade.get('atr', 0.0)
            entry_price = trade.get('entry_price', 0.0)
            sl_price = trade.get('stop_loss', 0.0)
            entry_time = trade.get('entry_time', 0.0)
            
            if full_size <= 0 or atr <= 0 or direction not in ['LONG', 'SHORT']:
                continue

            # Delayed SL Activation (Noise-Absorption)
            if not trade.get('sl_placed'):
                price_move = abs(current_price - entry_price)
                time_in_trade = time.time() - entry_time
                
                if time_in_trade >= 3.0 or price_move >= (0.4 * atr):
                    # Round size to symbol's step size requirements
                    rounded_size, _, _ = self.round_size_to_rules(symbol, full_size)
                    sl_price_rounded = self.round_price_to_step(sl_price, price_step)
                    
                    logger.info(f"[{symbol}] Noise-absorption window closed. Placing SL at {sl_price_rounded} for {rounded_size} (Move: {price_move:.4f}, Time: {time_in_trade:.1f}s)")
                    self.adapter.symbol = symbol
                    sl_res = self.adapter.place_tp_sl_order('loss_plan', sl_price_rounded, rounded_size, 'long' if direction == 'LONG' else 'short')
                    if self._tp_sl_success(sl_res):
                        trade['sl_placed'] = True
                    else:
                        logger.warning(f"Delayed SL placement failed for {symbol}: {sl_res}")
                continue # Skip further management until SL is active

            # Move stop to breakeven after TP1 hit
            if not trade.get('breakeven_set') and self._hit_target(current_price, trade.get('tp1'), direction):
                breakeven_trigger = self.round_price_to_step(trade.get('entry_price', current_price), price_step)
                self.adapter.symbol = symbol
                self.adapter.place_tp_sl_order('loss_plan', breakeven_trigger, runner_size, 'long' if direction == 'LONG' else 'short')
                trade['breakeven_set'] = True

            # Trail after TP2 hit using 1× ATR offset
            if trade.get('breakeven_set') and not trade.get('trailing_set') and self._hit_target(current_price, trade.get('tp2'), direction):
                if direction == 'LONG':
                    trailing_trigger = current_price - atr
                else:
                    trailing_trigger = current_price + atr
                trailing_trigger = self.round_price_to_step(trailing_trigger, price_step)
                self.adapter.symbol = symbol
                self.adapter.place_tp_sl_order('loss_plan', trailing_trigger, runner_size, 'long' if direction == 'LONG' else 'short')
                trade['trailing_set'] = True

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
                if not self.pnl_guard.can_trade():
                    logger.warning("Trading halted due to drawdown guard. Sleeping 30s.")
                    time.sleep(30)
                    continue
                
                self.cleanup_inactive_trades()

                for symbol in self.symbols:
                    try:
                        tick = self.fetch_tick(symbol)
                        current_price = tick['price']
                        # Manage any trailing/breakeven adjustments for active trades
                        self.manage_active_trades(symbol, current_price)
                    except Exception as e:
                        logger.error(f"Tick error {symbol}: {e}")
                        continue
                        
                    if len(self.market_data[symbol]) < 20:
                        if len(self.market_data[symbol]) % 10 == 0:
                            print(f"[{symbol}] Warming: {len(self.market_data[symbol])}/20")
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
                        
                        self.signal_logger.log({
                            'timestamp': datetime.now(timezone.utc).isoformat(),
                            'timestamp_ms': int(time.time() * 1000),
                            'symbol': symbol,
                            'price': current_price,
                            'signal': sig_type,
                            'confidence': conf,
                            'regime': latest['regime']
                        })
                        
                        now = time.time()
                        
                        # Logging for skipped signals (Debug visibility)
                        if conf >= 0.5 and conf < self.min_confidence:
                             print(f"  [Skipped] {symbol} {sig_type} (Conf: {conf:.2f} < {self.min_confidence})")
                        
                        if (sig_type in ['LONG', 'SHORT'] and 
                            conf >= self.min_confidence and 
                            (now - self.last_trade_time[symbol] > 300)):
                            
                            trade_class = self.determine_trade_class(latest['regime'], conf)
                            applied_leverage = self.resolve_leverage(conf, latest['regime'])
                            if applied_leverage is None:
                                continue
                            risk_pct = self.get_risk_pct(latest['regime'], conf)

                            if not self.can_open_trade(symbol, sig_type, trade_class, risk_pct, current_price):
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
                    except: pass
                    open_positions = len([p for p in self.positions.values() if abs(p) > 0])
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] 💓 Cycle Active | Equity: ${self.current_equity:.2f} | Positions: {open_positions}")
                    
                time.sleep(10)
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Loop error: {e}")
                time.sleep(5)

    def execute_trade(self, symbol, direction, confidence, price, signal_data, trade_class: str, applied_leverage: int, risk_pct: float):
        try:
            self.adapter.symbol = symbol
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

            # Partial TP levels
            tp1 = price + atr * 1.5 if direction == 'LONG' else price - atr * 1.5
            tp2 = price + atr * 3.0 if direction == 'LONG' else price - atr * 3.0
            tp1 = self.round_price_to_step(tp1, p_step)
            tp2 = self.round_price_to_step(tp2, p_step)
            sl_price = self.round_price_to_step(stop_loss_price, p_step)

            # Ensure directional validity after rounding
            if direction == 'SHORT':
                if tp1 >= price:
                    tp1 = self.round_price_to_step(price * 0.995, p_step)
                if tp2 >= price:
                    tp2 = self.round_price_to_step(price * 0.99, p_step)
                if sl_price <= price:
                    sl_price = self.round_price_to_step(price * 1.01, p_step)
            else:
                if tp1 <= price:
                    tp1 = self.round_price_to_step(price * 1.005, p_step)
                if tp2 <= price:
                    tp2 = self.round_price_to_step(price * 1.01, p_step)
                if sl_price >= price:
                    sl_price = self.round_price_to_step(price * 0.99, p_step)

            # Limit Price rounded to price_step
            raw_limit = price * (1.001 if direction == 'LONG' else 0.999)
            limit_price = self.round_price_to_step(raw_limit, p_step)

            # Position sizing splits
            size_tp1_raw = size * 0.30
            size_tp2_raw = size * 0.40
            size_tp1, _, _ = self.round_size_to_rules(symbol, size_tp1_raw)
            size_tp2, _, _ = self.round_size_to_rules(symbol, size_tp2_raw)

            # Ensure allocations do not exceed total size after rounding
            if size_tp1 + size_tp2 > size:
                size_tp2 = max(0.0, size - size_tp1)
                size_tp2, _, _ = self.round_size_to_rules(symbol, size_tp2)
            if size_tp1 + size_tp2 > size:
                size_tp1 = max(0.0, size - size_tp2)
                size_tp1, _, _ = self.round_size_to_rules(symbol, size_tp1)

            runner_size_raw = max(0.0, size - (size_tp1 + size_tp2))
            runner_size, _, _ = self.round_size_to_rules(symbol, runner_size_raw)

            if runner_size <= 0 and size_tp2 > 0:
                runner_size = size_tp2
                size_tp2 = 0.0
                runner_size, _, _ = self.round_size_to_rules(symbol, runner_size)

            print(f"  🚀 Exe: {direction} {symbol} x{size} (lev {applied_leverage}x, risk {risk_pct*100:.2f}%)")
            print(f"  Debug TPSL: TP1={tp1}, TP2={tp2}, SL={sl_price} (rounded to {p_step})")

            order_tpsl = {
                "take_profit": tpsl.get('take_profit', tp2),
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
            # Check: 1. data.orderId 2. orderId 3. order_id 4. data.order_id
            order_id = result.get('data', {}).get('orderId')
            if not order_id: order_id = result.get('orderId')
            if not order_id: order_id = result.get('order_id')
            if not order_id: order_id = result.get('data', {}).get('order_id')

            # NOISE-ABSORPTION: Immediate SL placement disabled.
            # SL will be placed by manage_active_trades after 3s OR 0.4x ATR move.
            logger.info(f"  [Noise-Absorption] SL activation delayed for {symbol} (Target: {sl_price})")

            # Place partial TPs with enforced success
            tp1_success = True
            if size_tp1 > 0:
                tp1_res = self.adapter.place_tp_sl_order('profit_plan', tp1, size_tp1, 'long' if direction == 'LONG' else 'short')
                tp1_success = self._tp_sl_success(tp1_res)
                if not tp1_success:
                    logger.error(f"TP1 Placement Failed: {tp1_res}")
                    self.compliance_logger.log({
                        "timestamp": int(time.time() * 1000),
                        "event": "tp1_failed",
                        "symbol": symbol,
                        "order_id": order_id,
                        "payload": tp1_res
                    })

            tp2_success = True
            tp2_status = "skipped"
            tp2_payload = None
            if size_tp2 > 0:
                tp2_res = self.adapter.place_tp_sl_order('profit_plan', tp2, size_tp2, 'long' if direction == 'LONG' else 'short')
                tp2_payload = tp2_res
                tp2_success = self._tp_sl_success(tp2_res)
                if not tp2_success:
                    logger.warning(f"TP2 placement failed, retrying with fresh client id: {tp2_res}")
                    tp2_retry = self.adapter.place_tp_sl_order('profit_plan', tp2, size_tp2, 'long' if direction == 'LONG' else 'short')
                    tp2_payload = tp2_retry
                    tp2_success = self._tp_sl_success(tp2_retry)
                    if tp2_success:
                        logger.info("TP2 retry succeeded.")
                    else:
                        logger.error(f"TP2 Placement Failed after retry: {tp2_retry}")
                        self.compliance_logger.log({
                            "timestamp": int(time.time() * 1000),
                            "event": "tp2_retry_failed",
                            "symbol": symbol,
                            "order_id": order_id,
                            "tp2_payload": tp2_retry
                        })
                tp2_status = "placed" if tp2_success else "missing"

            # If TP1 or TP2 (when size>0) failed, close position to avoid un-hedged trades
            if (size_tp1 > 0 and not tp1_success) or (size_tp2 > 0 and not tp2_success):
                try:
                    self.adapter.close_all_positions(symbol)
                except Exception as e:
                    logger.error(f"Failed to close position after TP failure for {symbol}: {e}")
                return

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

            self.register_active_trade(symbol, {
                'direction': direction,
                'entry_price': price,
                'size': size,
                'risk_pct': risk_pct,
                'applied_leverage': applied_leverage,
                'trade_class': trade_class,
                'tp1': tp1,
                'tp2': tp2,
                'stop_loss': sl_price,
                'runner_size': runner_size,
                'tp2_status': tp2_status,
                'atr': atr,
                'sl_placed': False,
                'entry_time': time.time(),
                'breakeven_set': False,
                'trailing_set': False
            })

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
    
    bot = SentinelLiveTradingBot(symbols=pairs)
    bot.run()

if __name__ == "__main__":
    main()
