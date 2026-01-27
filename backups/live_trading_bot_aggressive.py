#!/usr/bin/env python3
"""
Sentinel Alpha - AGGRESSIVE Multi-Pair Live Trading Bot
Optimized for WEEX AI Wars Competition - Ensures trades are executed

Features:
- Trades ALL 8 approved WEEX pairs
- Confidence threshold: 0.65 (system-wide standard)
- Aggressive regime detection
- Forces at least 1 trade in first 24 hours
- Better opportunity detection
"""

import os
import time
import yaml
import pandas as pd
from datetime import datetime, timezone
from dotenv import load_dotenv

# Import core modules
from execution.weex_adapter import WeexExecutionAdapter
from execution.execution_guard import ExecutionGuard
from risk.pnl_guard import PnLGuard
from strategy.position_sizer import PositionSizer
from utils.logger import JsonLogger, log_signal, log_trade, get_learning_state_hash

# Import LLM integration
try:
    from models.llm_integration import get_llm
    from config.model_config import get_model_config
    LLM_AVAILABLE = True
except Exception as e:
    print(f"⚠️  LLM integration not available: {e}")
    LLM_AVAILABLE = False

# Load credentials
load_dotenv()

# All approved WEEX pairs
APPROVED_PAIRS = [
    'cmt_btcusdt',
    'cmt_ethusdt',
    'cmt_solusdt',
    'cmt_dogeusdt',
    'cmt_xrpusdt',
    'cmt_adausdt',
    'cmt_bnbusdt',
    'cmt_ltcusdt'
]

class AggressiveLiveTradingBot:
    """
    Aggressive multi-pair trading bot optimized for competition qualification
    """
    
    def __init__(self, config_path='competition.yaml', dry_run=False):
        """Initialize aggressive bot with multiple pairs"""
        
        # Load config (check both locations)
        if not os.path.exists(config_path):
            config_path = 'competition.yaml'  # Try root directory
        
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.dry_run = dry_run
        self.trading_pairs = APPROVED_PAIRS
        self.current_positions = {pair: 0.0 for pair in self.trading_pairs}
        self.entry_prices = {pair: 0.0 for pair in self.trading_pairs}  # Track entry prices
        # Track TP/SL placement status to prevent missing risk controls
        self.tpsl_status = {
            pair: {'entry_price': None, 'last_set_ts': 0.0, 'last_success': False}
            for pair in self.trading_pairs
        }
        self.tpsl_retry_seconds = 120  # throttle TP/SL retries per symbol
        self.start_time = time.time()
        self.trades_executed = 0
        self.winning_trades = 0
        self.total_pnl = 0.0
        self.peak_equity = 1000.0
        self.initial_balance = 1000.0
        self.force_trade_threshold = 6 * 3600  # Force trade after 6 hours if none executed
        
        # AGGRESSIVE SETTINGS
        self.leverage = 4  # Keep leverage reasonable
        self.max_position_size = 0.001  # BTC equivalent
        self.max_notional_usd = 150  # tighter cap to prevent margin failures
        self.min_confidence = 0.65  # Updated to match system-wide threshold
        self.cooldown_seconds = 120  # REDUCED from 180
        self.max_drawdown_pct = 0.03  # Increased to 3% for more room
        self.data_window = 50  # REDUCED for faster signals
        self.check_interval = 45  # Check every 45s (more frequent)
        
        # Initialize components per pair
        print("\nInitializing WEEX Connection for all pairs...")
        self.adapters = {}
        self.engines = {}
        self.guards = {}
        
        for pair in self.trading_pairs[:]:  # Use slice to avoid modifying during iteration
            try:
                # WEEX adapter
                adapter = WeexExecutionAdapter(
                    api_key=os.getenv('WEEX_API_KEY'),
                    secret_key=os.getenv('WEEX_SECRET_KEY'),
                    passphrase=os.getenv('WEEX_PASSPHRASE'),
                    default_symbol=pair,  # FIXED: Use default_symbol not symbol
                    dry_run=self.dry_run
                )
                
                # Test adapter with a simple call
                try:
                    adapter.set_leverage()  # FIXED: No parameters needed
                except Exception as lev_err:
                    print(f"⚠️  Could not set leverage for {pair}: {lev_err}")
                    # Continue anyway - some pairs might not support leverage changes
                
                self.adapters[pair] = adapter
                
                # AI Engine - simplified, no parameters
                # We'll generate signals differently without AIEnhancedSignalEngine
                self.engines[pair] = None  # Placeholder
                
                # Execution guard
                self.guards[pair] = ExecutionGuard(
                    cooldown_seconds=self.cooldown_seconds,
                    max_notional_usd=self.max_notional_usd
                )
                
                print(f"✓ {pair} initialized")
                
            except Exception as e:
                print(f"✗ Failed to initialize {pair}: {e}")
                import traceback
                traceback.print_exc()
                if pair in self.trading_pairs:
                    self.trading_pairs.remove(pair)
        
        if not self.trading_pairs:
            raise RuntimeError("Failed to initialize any trading pairs!")
        
        print(f"\n✓ {len(self.trading_pairs)} pairs ready for trading")
        
        # Initialize risk management
        print("\nInitializing Risk Management...")
        self.pnl_guard = PnLGuard(max_drawdown_pct=self.max_drawdown_pct)
        self.position_sizer = PositionSizer()
        print("✓ Risk guards active")
        
        # Initialize logging
        print("\n✓ Logging initialized")
        self.signal_logger = JsonLogger('logs/aggressive_signals.jsonl')
        self.trade_logger = JsonLogger('logs/aggressive_trades.jsonl')
        self.performance_logger = JsonLogger('logs/aggressive_performance.jsonl')
        
        # Initialize LLM integration
        print("\nInitializing LLM Integration...")
        self.llm = None
        self.llm_enabled = False
        if LLM_AVAILABLE:
            try:
                model_config = get_model_config()
                self.llm_enabled = model_config.llm_enabled
                if self.llm_enabled:
                    self.llm = get_llm()
                    llm_status = self.llm.get_status()
                    if llm_status['loaded']:
                        print("✅ LLM loaded and ready")
                    elif llm_status['load_failed']:
                        print(f"⚠️  LLM failed to load, continuing without LLM enhancement")
                    else:
                        print("✅ LLM ready (will load on first use)")
                else:
                    print("ℹ️  LLM disabled in config")
            except Exception as e:
                print(f"⚠️  LLM initialization failed: {e}")
                print("   Continuing without LLM enhancement")
                self.llm_enabled = False
        else:
            print("ℹ️  LLM integration not available")
        
        # Sync existing positions from WEEX (critical for restarts!)
        self.sync_positions_from_weex()
        
        print("\n✓ Aggressive bot initialized successfully")
    
    def sync_positions_from_weex(self):
        """
        Query WEEX for existing positions and sync internal state
        Critical for handling bot restarts without losing position tracking
        """
        print("\nSyncing existing positions from WEEX...")
        
        try:
            # Query positions from any adapter (they all use the same account)
            adapter = list(self.adapters.values())[0]
            response = adapter.get_positions()
            
            if not response or 'data' not in response:
                print("✓ No existing positions found")
                return
            
            positions_data = response.get('data', [])
            if not positions_data:
                print("✓ No existing positions found")
                return
            
            # Parse and sync positions
            synced_count = 0
            for pos in positions_data:
                symbol = pos.get('symbol', '')
                size = float(pos.get('size', 0))
                side = pos.get('side', '')  # LONG or SHORT
                entry_price = float(pos.get('avgPrice', 0)) if pos.get('avgPrice') is not None else 0.0
                
                if symbol in self.trading_pairs and size > 0:
                    # Update position tracking
                    if side == 'LONG':
                        self.current_positions[symbol] = size
                    else:  # SHORT
                        self.current_positions[symbol] = -size
                    
                    # Fallback if avgPrice missing
                    if entry_price <= 0:
                        try:
                            ticker = self.adapters[symbol].get_ticker()
                            entry_price = float(ticker.get('last'))
                        except Exception:
                            entry_price = 0.0
                    self.entry_prices[symbol] = entry_price

                    # Mark TP/SL as missing for synced positions to ensure reconciliation
                    status = self.tpsl_status.get(symbol)
                    if not status or status.get('entry_price') != entry_price:
                        self.tpsl_status[symbol] = {
                            'entry_price': entry_price,
                            'last_set_ts': 0.0,
                            'last_success': False
                        }
                    synced_count += 1
                    print(f"   ✓ Synced {symbol}: {side} {size} @ ${entry_price}")
            
            if synced_count > 0:
                print(f"\n⚠️  WARNING: Found {synced_count} existing positions!")
                print(f"   These positions are using account margin.")
                print(f"   Bot will respect these positions and avoid opening duplicates.")
            else:
                print("✓ No existing positions found")
                
        except Exception as e:
            print(f"⚠️  Could not sync positions from WEEX: {e}")
            print("   Continuing with empty position tracking...")
    
    
    def should_force_trade(self):
        """
        Determine if we should force a trade to ensure qualification
        """
        elapsed = time.time() - self.start_time
        
        # Force trade after 6 hours if no trades yet
        if self.trades_executed == 0 and elapsed > self.force_trade_threshold:
            return True
        
        return False
    
    def execute_forced_trade(self):
        """
        Execute a forced trade on the most favorable pair to ensure qualification
        """
        print("\n" + "="*70)
        print("⚠️  FORCING TRADE TO ENSURE QUALIFICATION")
        print("="*70)
        
        # Find pair with best conditions
        best_pair = None
        best_confidence = 0.0
        best_signal = None
        
        for pair in self.trading_pairs:
            if self.current_positions[pair] != 0:
                continue  # Skip if already have position
            
            try:
                # Get latest data directly from WEEX
                df = self.get_market_data(pair, limit=self.data_window)
                if len(df) < 20:
                    continue
                
                # Simple signal generation
                prices = df['price'].values
                recent_avg = prices[-10:].mean()
                prev_avg = prices[-20:-10].mean()
                momentum = (recent_avg - prev_avg) / prev_avg
                
                signal = 'LONG' if momentum > 0 else 'SHORT'
                confidence = min(0.65 + abs(momentum) * 100, 0.9)  # Base updated to 0.65
                
                latest = {
                    'signal': signal,
                    'confidence': confidence,
                    'regime': 'FORCED'
                }
                
                signal = latest['signal']
                confidence = latest['confidence']
                
                if signal in ['LONG', 'SHORT'] and confidence > best_confidence:
                    best_confidence = confidence
                    best_pair = pair
                    best_signal = latest
                    
            except Exception as e:
                print(f"Error checking {pair}: {e}")
                continue
        
        # Execute on best pair, or force on BTC if no good signals
        if best_pair:
            target_pair = best_pair
            signal = best_signal['signal']
            confidence = best_confidence
            print(f"\n✓ Selected {target_pair}: {signal} @ {confidence:.2%} confidence")
        else:
            # Force trade on BTC with minimal size
            target_pair = 'cmt_btcusdt'
            signal = 'LONG'  # Default to LONG for BTC
            confidence = 0.65  # Updated to match system-wide threshold
            print(f"\n⚠️  No strong signals - forcing conservative LONG on {target_pair}")
        
        # Execute the trade
        try:
            adapter = self.adapters[target_pair]
            
            # Get current price
            ticker = adapter.get_ticker()
            current_price = float(ticker['last'])
            
            # Use minimum safe size
            size_btc = 0.0001  # Minimum allowed
            
            # Place order
            result = adapter.place_order(
                direction=signal,  # Use 'direction' not 'side', pass 'LONG' or 'SHORT'
                size=size_btc,
                price=current_price
            )
            
            if result and 'order_id' in result:
                self.trades_executed += 1
                self.current_positions[target_pair] = size_btc if signal == 'LONG' else -size_btc
                
                # Log trade
                self.trade_logger.log({
                    'timestamp': int(time.time() * 1000),
                    'pair': target_pair,
                    'signal': signal,
                    'confidence': confidence,
                    'size': size_btc,
                    'price': current_price,
                    'order_id': result['order_id'],
                    'forced': True,
                    'reason': 'Qualification requirement'
                })
                
                print(f"\n✅ FORCED TRADE EXECUTED")
                print(f"   Pair: {target_pair}")
                print(f"   Signal: {signal}")
                print(f"   Size: {size_btc} BTC")
                print(f"   Price: ${current_price:,.2f}")
                print(f"   Order ID: {result['order_id']}")
                print(f"\n🎯 QUALIFICATION REQUIREMENT MET!")
                
                return True
            else:
                print(f"✗ Failed to execute forced trade")
                return False
                
        except Exception as e:
            print(f"✗ Error executing forced trade: {e}")
            return False
    
    def get_market_data(self, pair, limit=50):
        """
        Get market data for a pair using WEEX adapter
        Returns DataFrame with timestamp, price, quantity
        """
        try:
            # Check if adapter exists for this pair
            if pair not in self.adapters:
                raise KeyError(f"No adapter initialized for {pair}")
            
            adapter = self.adapters[pair]
            
            # Store historical prices for this pair
            if not hasattr(self, 'price_history'):
                self.price_history = {}
            
            if pair not in self.price_history:
                self.price_history[pair] = []
            
            # Get current ticker
            ticker = adapter.get_ticker()
            current_price = float(ticker['last'])
            current_time = int(time.time() * 1000)
            
            # Add to history
            self.price_history[pair].append({
                'timestamp': current_time,
                'price': current_price,
                'quantity': float(ticker.get('base_volume', 0.01))
            })
            
            # Keep only recent history
            if len(self.price_history[pair]) > limit:
                self.price_history[pair] = self.price_history[pair][-limit:]
            
            # If we don't have enough history yet, pad with current price
            # (This is only for the first few iterations)
            if len(self.price_history[pair]) < limit:
                padding_needed = limit - len(self.price_history[pair])
                for i in range(padding_needed):
                    self.price_history[pair].insert(0, {
                        'timestamp': current_time - (padding_needed - i) * 1000,
                        'price': current_price,
                        'quantity': 0.01
                    })
            
            # Convert to DataFrame
            df = pd.DataFrame(self.price_history[pair])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            return df
            
        except KeyError as ke:
            # Adapter doesn't exist - this pair failed initialization
            raise ke
        except Exception as e:
            print(f"Error fetching data for {pair}: {e}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()
    
    def scan_all_pairs(self):
        """
        Scan all pairs for trading opportunities
        Returns: List of (pair, signal_data) tuples sorted by confidence
        """
        opportunities = []
        
        # Only scan pairs that were successfully initialized
        active_pairs = [p for p in self.trading_pairs if p in self.adapters]
        
        for pair in active_pairs:
            try:
                # Get market data directly from WEEX
                df = self.get_market_data(pair, limit=self.data_window)
                
                if len(df) < 20:
                    continue
                
                # Simple signal generation without AIEnhancedSignalEngine
                # Calculate basic momentum
                prices = df['price'].values
                current_price = prices[-1]
                
                # Recent momentum (last 10 vs previous 10)
                recent_avg = prices[-10:].mean()
                prev_avg = prices[-20:-10].mean()
                momentum = (recent_avg - prev_avg) / prev_avg
                
                # Volatility
                volatility = prices[-20:].std() / prices[-20:].mean()
                
                # Generate signal based on momentum - ULTRA-AGGRESSIVE MODE FOR COMPETITION
                signal = 'NO-TRADE'
                confidence = 0.5
                regime = 'RANGE'
                
                # ULTRA-AGGRESSIVE: Trade on ANY detectable movement
                # Market is very stable, so we need to catch micro-movements
                # With 4x leverage, even 0.05% moves are profitable
                
                if momentum > 0.00005:  # ULTRA-SENSITIVE: Any upward tick
                    signal = 'LONG'
                    # Base confidence 0.48, scales up with momentum
                    confidence = min(0.48 + abs(momentum) * 300, 0.85)
                    regime = 'TREND_UP' if momentum > 0.001 else 'RANGE'
                elif momentum < -0.00005:  # ULTRA-SENSITIVE: Any downward tick
                    signal = 'SHORT'
                    confidence = min(0.48 + abs(momentum) * 300, 0.85)
                    regime = 'TREND_DOWN' if momentum < -0.001 else 'RANGE'
                
                # BOOST confidence if volatility is present (any movement is good)
                if volatility > 0.0001:  # Any volatility at all
                    confidence = min(confidence + 0.05, 0.9)
                
                # BOOST for consistent direction (last 5 vs last 10)
                if len(prices) >= 10:
                    very_recent = prices[-5:].mean()
                    less_recent = prices[-10:-5].mean()
                    if (very_recent > less_recent and signal == 'LONG') or \
                       (very_recent < less_recent and signal == 'SHORT'):
                        confidence = min(confidence + 0.03, 0.9)  # Direction confirmed
                
                # LLM Enhancement: Get regime interpretation and confidence adjustments
                llm_reasoning = "LLM disabled"
                regime_probabilities = {regime: 1.0}  # Default
                
                if self.llm_enabled and self.llm:
                    try:
                        # Market data for LLM
                        market_data = {
                            'price': float(current_price),
                            'momentum': float(momentum),
                            'volatility': float(volatility)
                        }
                        
                        # Get LLM regime interpretation
                        llm_regime = self.llm.interpret_regime(regime, market_data)
                        
                        # Get confidence calibration
                        patterns = {
                            'momentum_strength': min(abs(momentum) * 100, 1.0),
                            'continuation_probability': 0.5 + (abs(momentum) * 50)
                        }
                        calibration = self.llm.calibrate_confidence(
                            confidence, regime, signal, patterns
                        )
                        
                        # Apply LLM adjustment to confidence
                        original_confidence = confidence
                        confidence = max(0.0, min(1.0, confidence + calibration['adjustment']))
                        
                        # Build comprehensive reasoning
                        llm_reasoning = f"{llm_regime}. {calibration['reasoning']}"
                        if calibration['adjustment'] != 0:
                            llm_reasoning += f" (Adjusted confidence {original_confidence:.2%} → {confidence:.2%})"
                        
                        # Estimate regime probabilities (simplified for now)
                        if regime == 'TREND_UP':
                            regime_probabilities = {'TREND_UP': 0.7, 'RANGE': 0.2, 'TREND_DOWN': 0.1}
                        elif regime == 'TREND_DOWN':
                            regime_probabilities = {'TREND_UP': 0.1, 'RANGE': 0.2, 'TREND_DOWN': 0.7}
                        else:
                            regime_probabilities = {'TREND_UP': 0.25, 'RANGE': 0.5, 'TREND_DOWN': 0.25}
                    except Exception as llm_err:
                        llm_reasoning = f"LLM error: {str(llm_err)[:50]}"
                
                # Create signal data structure
                latest = {
                    'signal': signal,
                    'confidence': confidence,
                    'regime': regime,
                    'reasoning': f"Momentum: {momentum:.4f}, Volatility: {volatility:.4f}",
                    'llm_reasoning': llm_reasoning,
                    'regime_probabilities': regime_probabilities
                }
                current_price = df.iloc[-1]['price']
                
                # Log signal with all required competition fields
                log_signal(
                    logger=self.signal_logger,
                    pair=pair,
                    price=current_price,
                    signal=latest['signal'],
                    confidence=latest['confidence'],
                    regime=latest['regime'],
                    regime_probabilities=regime_probabilities,
                    learning_state_hash="N/A",  # No adaptive agent in current simplified version
                    llm_reasoning=llm_reasoning,
                    reasoning=latest['reasoning'],
                    momentum=float(momentum),
                    volatility=float(volatility)
                )
                
                # Check if tradeable
                if latest['signal'] in ['LONG', 'SHORT'] and latest['confidence'] >= self.min_confidence:
                    opportunities.append((pair, latest, current_price))
                    
            except Exception as e:
                print(f"Error scanning {pair}: {e}")
                continue
        
        # Sort by confidence (highest first)
        opportunities.sort(key=lambda x: x[1]['confidence'], reverse=True)
        
        return opportunities
    
    def execute_trade(self, pair, signal_data, current_price):
        """
        Execute trade on specific pair
        """
        signal = signal_data['signal']
        confidence = signal_data['confidence']
        
        # CRITICAL: Check if we already have too many open positions (margin limit)
        active_positions = sum(1 for p in self.current_positions.values() if abs(p) > 0.00001)
        if active_positions >= 5:  # Max 5 concurrent positions for $1000 account
            print(f"   ⚠️ Skipping {pair}: Already at max positions ({active_positions}/5)")
            return False
        
        # Check execution guard
        if not self.guards[pair].can_trade(size=self.max_position_size, symbol=pair, price=current_price):
            return False
        
        # Check if we already have a position on this pair
        if abs(self.current_positions[pair]) > 0.00001:
            print(f"   ⚠️ Skipping {pair}: Already have position ({self.current_positions[pair]})")
            return False
        
        # Calculate position size (symbol-aware)
        size_btc = self.position_sizer.size(
            confidence=confidence,
            adaptive_factor=1.0,
            symbol=pair,
            account_balance=1000.0,  # TODO: Get from account query
            max_risk_pct=1.0
        )
        
        # Get position sizing rationale from LLM
        position_sizing_rationale = f"Confidence-based sizing: {confidence:.1%} confidence, 2% max risk"
        if self.llm_enabled and self.llm:
            try:
                llm_rationale = self.llm.explain_position_size(
                    confidence=confidence,
                    signal=signal,
                    account_balance=1000.0,
                    proposed_size=size_btc
                )
                position_sizing_rationale = llm_rationale
            except Exception as e:
                pass  # Use default rationale
        
        # Get risk assessment from LLM
        active_positions = sum(1 for p in self.current_positions.values() if abs(p) > 0.00001)
        risk_assessment = "Standard risk parameters"
        if self.llm_enabled and self.llm:
            try:
                market_data = {'price': float(current_price), 'momentum': 0.001, 'volatility': 0.01}
                risk_assessment = self.llm.assess_risk(signal, market_data, active_positions)
            except Exception as e:
                pass
        
        # LLM reasoning from signal_data
        llm_reasoning = signal_data.get('llm_reasoning', 'LLM disabled')
        
        # Execute order
        try:
            adapter = self.adapters[pair]
            
            result = adapter.place_order(
                direction=signal,  # Use 'direction' not 'side', pass 'LONG' or 'SHORT'
                size=size_btc,
                price=current_price
            )
            
            if result and 'order_id' in result:
                # Update state
                self.trades_executed += 1
                self.guards[pair].register_trade(size_btc)  # Correct method name
                
                # Track entry price for P&L calculation
                self.entry_prices[pair] = current_price
                
                if signal == 'LONG':
                    self.current_positions[pair] += size_btc
                else:
                    self.current_positions[pair] -= size_btc
                
                # Set TP/SL orders for risk management (retry once if needed)
                tp_ok, sl_ok = self.set_tp_sl_orders(pair, signal, size_btc, current_price, confidence)
                if not (tp_ok and sl_ok):
                    print(f"   ⚠️  TP/SL incomplete for {pair}, retrying once...")
                    tp_ok, sl_ok = self.set_tp_sl_orders(pair, signal, size_btc, current_price, confidence)
                # Record TP/SL status for reconciliation
                self.tpsl_status[pair] = {
                    'entry_price': current_price,
                    'last_set_ts': time.time(),
                    'last_success': bool(tp_ok and sl_ok)
                }
                
                # Log trade with enhanced logging helper
                log_trade(
                    logger=self.trade_logger,
                    pair=pair,
                    signal=signal,
                    confidence=confidence,
                    size=size_btc,
                    price=current_price,
                    order_id=result['order_id'],
                    position_sizing_rationale=position_sizing_rationale,
                    risk_filter_result="PASSED",
                    llm_reasoning=llm_reasoning,
                    forced=False,
                    risk_assessment=risk_assessment,
                    active_positions=active_positions
                )
                
                print(f"\n✅ TRADE EXECUTED: {pair}")
                print(f"   {signal} @ ${current_price:,.2f}")
                print(f"   Size: {size_btc} BTC")
                print(f"   Confidence: {confidence:.2%}")
                print(f"   Order ID: {result['order_id']}")
                
                return True
            
        except Exception as e:
            print(f"✗ Trade execution failed for {pair}: {e}")
        
        return False
    
    def set_tp_sl_orders(self, pair: str, signal: str, size: float, entry_price: float, confidence: float):
        """
        Set Take-Profit and Stop-Loss orders for a position
        
        TP/SL levels based on confidence:
        - High confidence (>0.7): Wider TP (3%), Tighter SL (1%)
        - Medium confidence (0.6-0.7): Standard TP (2%), Standard SL (1.5%)
        - Lower confidence (<0.6): Conservative TP (1.5%), Wider SL (2%)
        """
        try:
            adapter = self.adapters[pair]
            
            # Symbol-specific price precision (tick size)
            PRICE_PRECISION = {
                'cmt_btcusdt': 1,      # $96500.0
                'cmt_ethusdt': 2,      # $3450.50
                'cmt_solusdt': 2,      # $123.45
                'cmt_dogeusdt': 5,     # $0.12345
                'cmt_xrpusdt': 4,      # $1.8566
                'cmt_adausdt': 4,      # $0.3626
                'cmt_bnbusdt': 2,      # $862.50
                'cmt_ltcusdt': 2,      # $105.50
            }
            
            precision = PRICE_PRECISION.get(pair, 4)
            
            # Calculate TP/SL levels based on confidence
            if confidence > 0.7:
                tp_percent = 0.03  # 3%
                sl_percent = 0.01  # 1%
            elif confidence > 0.6:
                tp_percent = 0.02  # 2%
                sl_percent = 0.015  # 1.5%
            else:
                tp_percent = 0.015  # 1.5%
                sl_percent = 0.02  # 2%
            
            # Calculate trigger prices and round to correct precision
            if signal == 'LONG':
                tp_trigger = round(entry_price * (1 + tp_percent), precision)
                sl_trigger = round(entry_price * (1 - sl_percent), precision)
                position_side = 'long'
            else:  # SHORT
                tp_trigger = round(entry_price * (1 - tp_percent), precision)
                sl_trigger = round(entry_price * (1 + sl_percent), precision)
                position_side = 'short'
            
            # Place TP order
            tp_result = adapter.place_tp_sl_order(
                plan_type='profit_plan',
                trigger_price=tp_trigger,
                size=size,
                position_side=position_side,
                execute_price=0,  # Market order
                margin_mode=1  # Cross margin
            )
            
            tp_ok = False
            if tp_result and isinstance(tp_result, list) and len(tp_result) > 0:
                tp_ok = bool(tp_result[0].get('success'))
                if tp_ok:
                    print(f"   ✓ TP set @ ${tp_trigger:.{precision}f} (-{tp_percent*100:.1f}%)" if signal == 'SHORT' else f"   ✓ TP set @ ${tp_trigger:.{precision}f} (+{tp_percent*100:.1f}%)")
                else:
                    print(f"   ⚠️  TP order failed")
            
            # Place SL order
            sl_result = adapter.place_tp_sl_order(
                plan_type='loss_plan',
                trigger_price=sl_trigger,
                size=size,
                position_side=position_side,
                execute_price=0,  # Market order
                margin_mode=1  # Cross margin
            )
            
            sl_ok = False
            if sl_result and isinstance(sl_result, list) and len(sl_result) > 0:
                sl_ok = bool(sl_result[0].get('success'))
                if sl_ok:
                    print(f"   ✓ SL set @ ${sl_trigger:.{precision}f} (+{sl_percent*100:.1f}%)" if signal == 'SHORT' else f"   ✓ SL set @ ${sl_trigger:.{precision}f} (-{sl_percent*100:.1f}%)")
                else:
                    print(f"   ⚠️  SL order failed")

            return tp_ok, sl_ok
        
        except Exception as e:
            print(f"   ⚠️  Could not set TP/SL: {e}")
            return False, False

    def ensure_tpsl_for_open_positions(self):
        """
        Ensure all live positions have TP/SL set.
        Uses throttling to avoid duplicate orders.
        """
        try:
            adapter = list(self.adapters.values())[0]
            positions = adapter.get_positions()
            if not isinstance(positions, list):
                return

            now = time.time()
            for pos in positions:
                symbol = pos.get('symbol')
                if symbol not in self.trading_pairs:
                    continue
                size = float(pos.get('size', 0) or 0)
                if size <= 0:
                    continue

                side = pos.get('side', '').upper()
                signal = 'LONG' if side == 'LONG' else 'SHORT'

                status = self.tpsl_status.get(symbol, {'entry_price': None, 'last_set_ts': 0.0, 'last_success': False})
                if status.get('last_success') and (now - status.get('last_set_ts', 0)) < self.tpsl_retry_seconds:
                    continue
                if (now - status.get('last_set_ts', 0)) < self.tpsl_retry_seconds:
                    continue

                # Use current price for TP/SL placement if avgPrice unavailable
                try:
                    ticker = self.adapters[symbol].get_ticker()
                    entry_price = float(ticker.get('last'))
                except Exception:
                    entry_price = status.get('entry_price') or 0.0

                if entry_price <= 0:
                    continue

                print(f"   ⚠️  Ensuring TP/SL for live position: {symbol} {signal} size={size}")
                tp_ok, sl_ok = self.set_tp_sl_orders(symbol, signal, size, entry_price, confidence=0.55)
                self.tpsl_status[symbol] = {
                    'entry_price': entry_price,
                    'last_set_ts': now,
                    'last_success': bool(tp_ok and sl_ok)
                }
        except Exception as e:
            print(f"   ⚠️  TP/SL reconciliation error: {e}")
    
    def update_performance(self):
        """Log current performance metrics with real account balance"""
        # Query real account balance from WEEX
        try:
            adapter = list(self.adapters.values())[0]
            assets_response = adapter.get_account_assets()
            
            if assets_response and isinstance(assets_response, list) and len(assets_response) > 0:
                usdt_asset = assets_response[0]  # USDT is usually first
                current_equity = float(usdt_asset.get('equity', self.initial_balance))
                available_balance = float(usdt_asset.get('available', 0))
                unrealized_pnl = float(usdt_asset.get('unrealizePnl', 0))
            else:
                current_equity = self.initial_balance + self.total_pnl
                available_balance = current_equity
                unrealized_pnl = 0.0
        except Exception as e:
            # Fallback to calculated values
            current_equity = self.initial_balance + self.total_pnl
            available_balance = current_equity
            unrealized_pnl = 0.0
        
        # Update peak equity for drawdown calculation
        if current_equity > self.peak_equity:
            self.peak_equity = current_equity
        
        # Calculate drawdown
        drawdown_pct = ((self.peak_equity - current_equity) / self.peak_equity) if self.peak_equity > 0 else 0.0
        
        # Calculate ROI
        roi_pct = ((current_equity - self.initial_balance) / self.initial_balance) if self.initial_balance > 0 else 0.0
        
        # Calculate win rate
        win_rate = (self.winning_trades / self.trades_executed) if self.trades_executed > 0 else 0.0
        
        self.performance_logger.log({
            'timestamp': int(time.time() * 1000),
            'equity': round(current_equity, 2),
            'available': round(available_balance, 2),
            'unrealized_pnl': round(unrealized_pnl, 2),
            'total_pnl': round(self.total_pnl, 2),
            'roi': round(roi_pct, 4),
            'drawdown': round(drawdown_pct, 4),
            'win_rate': round(win_rate, 4),
            'trades': self.trades_executed,
            'winning_trades': self.winning_trades,
            'active_pairs': sum(1 for p in self.current_positions.values() if abs(p) > 0.00001),
            'positions': self.current_positions
        })
    
    def run(self):
        """Main trading loop"""
        
        print("\n" + "="*70)
        print("SENTINEL ALPHA - AGGRESSIVE MULTI-PAIR BOT STARTED")
        print("="*70)
        print(f"\nConfiguration:")
        print(f"  Trading Pairs: {len(self.trading_pairs)}")
        print(f"  Leverage: {self.leverage}×")
        print(f"  Min Confidence: {self.min_confidence:.2%}")
        print(f"  Cooldown: {self.cooldown_seconds}s")
        print(f"  Check Interval: {self.check_interval}s")
        print(f"  Dry Run: {self.dry_run}")
        print(f"\n⚠️  AGGRESSIVE MODE: Will force trade after 6 hours if needed")
        print("="*70)
        
        iteration = 0
        
        try:
            while True:
                iteration += 1
                
                print(f"\n[{iteration}] Scanning {len(self.trading_pairs)} pairs...")
                
                # Check if we need to force a trade
                if self.should_force_trade():
                    self.execute_forced_trade()

                # Reconcile TP/SL on existing positions to avoid unprotected exposure
                self.ensure_tpsl_for_open_positions()
                
                # Scan all pairs for opportunities
                opportunities = self.scan_all_pairs()
                
                if opportunities:
                    print(f"\n📊 Found {len(opportunities)} opportunities:")
                    for pair, signal_data, price in opportunities[:3]:  # Show top 3
                        print(f"   {pair}: {signal_data['signal']} @ {signal_data['confidence']:.2%}")
                    
                    # Execute best opportunity
                    best_pair, best_signal, best_price = opportunities[0]
                    self.execute_trade(best_pair, best_signal, best_price)
                else:
                    print("   No opportunities above threshold")
                
                # Update performance
                self.update_performance()
                
                # Status update
                if iteration % 10 == 0:
                    print(f"\n📈 STATUS UPDATE")
                    print(f"   Runtime: {(time.time() - self.start_time) / 3600:.1f} hours")
                    print(f"   Total Trades: {self.trades_executed}")
                    print(f"   Active Positions: {sum(1 for p in self.current_positions.values() if p != 0)}")
                
                # Wait before next iteration
                time.sleep(self.check_interval)
                
        except KeyboardInterrupt:
            print("\n\n⚠️  Bot stopped by user")
        except Exception as e:
            print(f"\n\n✗ Fatal error: {e}")
            raise

def main():
    """Main entry point"""
    
    print("="*70)
    print("SENTINEL ALPHA - AGGRESSIVE MULTI-PAIR LIVE TRADING BOT")
    print("WEEX AI Wars Competition - Qualification Mode")
    print("="*70)
    
    # Configuration
    config_path = 'competition.yaml'
    dry_run = False  # LIVE TRADING
    
    print(f"\nConfiguration:")
    print(f"  Trading Pairs: 8 (ALL APPROVED PAIRS)")
    print(f"  Min Confidence: 0.65 (System-wide standard)")
    print(f"  Leverage: 4×")
    print(f"  Dry Run: {dry_run}")
    print(f"\n⚠️  This will place REAL orders on multiple pairs!")
    print(f"⚠️  Will force at least 1 trade within 6 hours to ensure qualification")
    
    # Auto-confirm when running as background process
    import sys
    if not sys.stdin.isatty():
        print("\n[Auto-confirmed: Running as background process]")
        response = 'yes'
    else:
        # Confirm
        response = input("\nStart aggressive multi-pair trading? (yes/no): ").strip().lower()
    
    if response != 'yes':
        print("Aborted by user")
        return
    
    # Initialize and run bot
    bot = AggressiveLiveTradingBot(
        config_path=config_path,
        dry_run=dry_run
    )
    
    bot.run()

if __name__ == '__main__':
    main()

