#!/usr/bin/env python3
"""
Trade Performance Analysis Tool

Analyzes last 24 hours of trading data to identify patterns in win/loss performance
correlated with confidence levels, regimes, trade classes, and other key metrics.
"""

import os
import sys
import json
import time
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from execution.weex_adapter import WeexExecutionAdapter
from dotenv import load_dotenv

# Load credentials
load_dotenv()

class TradePerformanceAnalyzer:
    def __init__(self):
        self.adapter = WeexExecutionAdapter(
            api_key=os.getenv("WEEX_API_KEY"),
            secret_key=os.getenv("WEEX_SECRET_KEY"),
            passphrase=os.getenv("WEEX_PASSPHRASE"),
            default_symbol="cmt_btcusdt"
        )
        self.symbols = [
            "cmt_btcusdt", "cmt_ethusdt", "cmt_solusdt", 
            "cmt_dogeusdt", "cmt_xrpusdt", "cmt_adausdt", 
            "cmt_bnbusdt", "cmt_ltcusdt"
        ]
        
        # Analysis time window (24 hours)
        self.end_time = datetime.now(timezone.utc)
        self.start_time = self.end_time - timedelta(hours=24)
        self.start_timestamp_ms = int(self.start_time.timestamp() * 1000)
        self.end_timestamp_ms = int(self.end_time.timestamp() * 1000)
        
        # Data storage
        self.entry_trades = []
        self.exit_orders = []
        self.signals = []
        self.performance_data = []
        
    def fetch_trade_history(self) -> Dict:
        """Fetch trade history from WEEX API for last 24 hours, with fallback to existing data"""
        print("Fetching trade history from WEEX API...")
        results = {
            "orders": [],
            "plan_orders": []
        }
        
        try:
            for sym in self.symbols:
                try:
                    print(f"  Fetching {sym}...")
                    self.adapter.symbol = sym
                    
                    # Fetch order history
                    path = "/capi/v2/order/history"
                    params = {
                        "symbol": sym,
                        "pageSize": 100,
                        "createDate": self.start_timestamp_ms
                    }
                    orders = self.adapter._get(path, params)
                    
                    if isinstance(orders, list):
                        results["orders"].extend(orders)
                    elif isinstance(orders, dict):
                        if "data" in orders:
                            results["orders"].extend(orders.get("data", []))
                        elif "list" in orders:
                            results["orders"].extend(orders.get("list", []))
                    
                    # Fetch plan orders (TP/SL)
                    path = "/capi/v2/order/historyPlan"
                    params = {
                        "symbol": sym,
                        "pageSize": 100,
                        "startTime": self.start_timestamp_ms,
                        "endTime": self.end_timestamp_ms
                    }
                    plans = self.adapter._get(path, params)
                    
                    if isinstance(plans, list):
                        results["plan_orders"].extend(plans)
                    elif isinstance(plans, dict):
                        if "data" in plans:
                            results["plan_orders"].extend(plans.get("data", []))
                        elif "list" in plans:
                            results["plan_orders"].extend(plans.get("list", []))
                    
                    time.sleep(0.3)  # Rate limiting
                except Exception as e:
                    print(f"  Error fetching {sym}: {e}")
                    continue
            
            print(f"  Fetched {len(results['orders'])} orders and {len(results['plan_orders'])} plan orders")
        except Exception as e:
            print(f"  API fetch failed: {e}")
            print("  Attempting to use existing historical data...")
            
            # Fallback to existing historical data
            hist_file = Path("logs/weex_historical_data.json")
            if hist_file.exists():
                try:
                    with open(hist_file, 'r') as f:
                        existing_data = json.load(f)
                    results = existing_data
                    print(f"  Loaded {len(results.get('orders', []))} orders from existing data")
                except Exception as e2:
                    print(f"  Failed to load existing data: {e2}")
        
        return results
    
    def parse_log_files(self):
        """Parse log files for last 24 hours"""
        print("\nParsing log files...")
        
        # Parse live_trades.jsonl
        trades_file = Path("logs/live_trades.jsonl")
        if trades_file.exists():
            print(f"  Parsing {trades_file}...")
            with open(trades_file, 'r') as f:
                for line in f:
                    try:
                        trade = json.loads(line.strip())
                        trade_time = datetime.fromisoformat(trade.get('timestamp', '').replace('Z', '+00:00'))
                        if trade_time >= self.start_time and trade_time <= self.end_time:
                            trade['parsed_timestamp'] = trade_time
                            self.entry_trades.append(trade)
                    except Exception as e:
                        continue
            print(f"    Found {len(self.entry_trades)} entry trades in last 24h")
        else:
            print(f"    {trades_file} not found")
        
        # Parse live_signals.jsonl
        signals_file = Path("logs/live_signals.jsonl")
        if signals_file.exists():
            print(f"  Parsing {signals_file}...")
            with open(signals_file, 'r') as f:
                for line in f:
                    try:
                        signal = json.loads(line.strip())
                        signal_time = datetime.fromisoformat(signal.get('timestamp', '').replace('Z', '+00:00'))
                        if signal_time >= self.start_time and signal_time <= self.end_time:
                            signal['parsed_timestamp'] = signal_time
                            self.signals.append(signal)
                    except Exception as e:
                        continue
            print(f"    Found {len(self.signals)} signals in last 24h")
        else:
            print(f"    {signals_file} not found")
        
        # Parse performance.jsonl
        perf_file = Path("logs/performance.jsonl")
        if perf_file.exists():
            print(f"  Parsing {perf_file}...")
            with open(perf_file, 'r') as f:
                for line in f:
                    try:
                        perf = json.loads(line.strip())
                        perf_time = datetime.fromtimestamp(perf.get('timestamp', 0) / 1000, tz=timezone.utc)
                        if perf_time >= self.start_time and perf_time <= self.end_time:
                            perf['parsed_timestamp'] = perf_time
                            self.performance_data.append(perf)
                    except Exception as e:
                        continue
            print(f"    Found {len(self.performance_data)} performance records in last 24h")
        else:
            print(f"    {perf_file} not found")
    
    def match_trades_with_outcomes(self, trade_history: Dict) -> List[Dict]:
        """Match entry trades with exit orders to determine win/loss"""
        print("\nMatching trades with outcomes...")
        
        # Convert trade history to DataFrame for easier processing
        orders_df = pd.DataFrame(trade_history.get('orders', []))
        if orders_df.empty:
            print("  No orders found in trade history")
            return []
        
        # Filter for filled orders in time window
        orders_df['createTime'] = pd.to_numeric(orders_df.get('createTime', 0), errors='coerce')
        orders_df = orders_df[
            (orders_df['createTime'] >= self.start_timestamp_ms) &
            (orders_df['createTime'] <= self.end_timestamp_ms) &
            (orders_df.get('status', '') == 'filled')
        ].copy()
        
        if orders_df.empty:
            print("  No filled orders in time window")
            return []
        
        # Separate entry and exit orders
        entry_orders = orders_df[
            orders_df.get('type', '').isin(['open_long', 'open_short'])
        ].copy()
        
        exit_orders = orders_df[
            orders_df.get('type', '').isin(['close_long', 'close_short'])
        ].copy()
        
        print(f"    Found {len(entry_orders)} entry orders and {len(exit_orders)} exit orders")
        
        # Match trades
        matched_trades = []
        
        # Extract regime from reasoning text helper
        def extract_regime_from_reasoning(reasoning_text):
            """Extract regime from TPSL reasoning text"""
            if not reasoning_text:
                return 'UNKNOWN'
            reasoning_lower = reasoning_text.lower()
            if 'upward trending' in reasoning_lower or 'trending up' in reasoning_lower:
                return 'TREND_UP'
            elif 'downward trending' in reasoning_lower or 'trending down' in reasoning_lower:
                return 'TREND_DOWN'
            elif 'low volatility' in reasoning_lower or 'volatility compression' in reasoning_lower:
                return 'VOLATILITY_COMPRESSION'
            elif 'range' in reasoning_lower or 'range-bound' in reasoning_lower:
                return 'RANGE'
            return 'UNKNOWN'
        
        # Match signals with trades for confidence/regime data
        # Use symbol + approximate timestamp (within 60 seconds)
        signal_map = {}
        for signal in self.signals:
            if signal.get('signal') in ['LONG', 'SHORT']:
                symbol = signal.get('symbol')
                sig_time = signal.get('parsed_timestamp')
                if symbol and sig_time:
                    # Store by symbol and timestamp (rounded to minute for matching)
                    key = (symbol, int(sig_time.timestamp() / 60))
                    signal_map[key] = signal
        
        # Create entry trades from log file
        for log_trade in self.entry_trades:
            symbol = log_trade.get('symbol')
            entry_time = log_trade.get('parsed_timestamp')
            entry_timestamp_ms = int(entry_time.timestamp() * 1000) if entry_time else 0
            
            # Try to find matching signal for confidence/regime (within 60 seconds)
            matched_signal = None
            if entry_time:
                entry_minute = int(entry_time.timestamp() / 60)
                signal_key = (symbol, entry_minute)
                matched_signal = signal_map.get(signal_key)
                
                # If exact match not found, try adjacent minutes
                if not matched_signal:
                    for offset in [-1, 1]:
                        alt_key = (symbol, entry_minute + offset)
                        if alt_key in signal_map:
                            matched_signal = signal_map[alt_key]
                            break
            
            # Extract regime
            regime = 'UNKNOWN'
            if matched_signal:
                regime = matched_signal.get('regime', 'UNKNOWN')
            elif isinstance(log_trade.get('tpsl'), dict):
                regime = log_trade.get('tpsl', {}).get('regime', 'UNKNOWN')
                if regime == 'UNKNOWN':
                    reasoning = log_trade.get('tpsl', {}).get('reasoning', '')
                    regime = extract_regime_from_reasoning(reasoning)
            
            # Extract confidence
            confidence = log_trade.get('confidence', 0)
            if confidence == 0 and matched_signal:
                confidence = matched_signal.get('confidence', 0)
            
            # Find matching exit orders (same symbol, after entry)
            symbol_exits = exit_orders[
                (exit_orders.get('symbol', '') == symbol) &
                (exit_orders['createTime'] >= entry_timestamp_ms)
            ]
            
            if not symbol_exits.empty:
                # Use first exit order (closest match)
                exit_order = symbol_exits.iloc[0]
                pnl = float(exit_order.get('totalProfits', 0))
                
                matched_trade = {
                    'symbol': symbol,
                    'entry_time': entry_time,
                    'exit_time': datetime.fromtimestamp(exit_order['createTime'] / 1000, tz=timezone.utc),
                    'entry_price': log_trade.get('price', 0),
                    'exit_price': float(exit_order.get('price_avg', 0)),
                    'signal': log_trade.get('signal', ''),
                    'confidence': confidence,
                    'regime': regime,
                    'trade_class': log_trade.get('trade_class', 'UNKNOWN'),
                    'applied_leverage': log_trade.get('applied_leverage', 0),
                    'risk_pct': log_trade.get('risk_pct', 0),
                    'size': log_trade.get('size', 0),
                    'pnl': pnl,
                    'is_win': pnl > 0,
                    'order_id': log_trade.get('order_id', ''),
                }
                matched_trades.append(matched_trade)
        
        print(f"    Matched {len(matched_trades)} trades with outcomes")
        return matched_trades
    
    def analyze_by_confidence(self, trades: List[Dict]) -> Dict:
        """Analyze performance by confidence buckets"""
        if not trades:
            return {}
        
        buckets = {
            '0.52-0.55': (0.52, 0.55),
            '0.55-0.60': (0.55, 0.60),
            '0.60-0.65': (0.60, 0.65),
            '0.65+': (0.65, 1.0)
        }
        
        results = {}
        for bucket_name, (min_conf, max_conf) in buckets.items():
            bucket_trades = [
                t for t in trades 
                if min_conf <= t.get('confidence', 0) < max_conf
            ]
            
            if bucket_trades:
                wins = [t for t in bucket_trades if t.get('is_win', False)]
                losses = [t for t in bucket_trades if not t.get('is_win', False)]
                
                total_pnl = sum(t.get('pnl', 0) for t in bucket_trades)
                win_pnl = sum(t.get('pnl', 0) for t in wins)
                loss_pnl = sum(t.get('pnl', 0) for t in losses)
                
                results[bucket_name] = {
                    'total_trades': len(bucket_trades),
                    'wins': len(wins),
                    'losses': len(losses),
                    'win_rate': len(wins) / len(bucket_trades) * 100 if bucket_trades else 0,
                    'total_pnl': total_pnl,
                    'avg_pnl': total_pnl / len(bucket_trades) if bucket_trades else 0,
                    'avg_win': win_pnl / len(wins) if wins else 0,
                    'avg_loss': loss_pnl / len(losses) if losses else 0,
                    'profit_factor': abs(win_pnl / loss_pnl) if loss_pnl != 0 else float('inf'),
                    'risk_reward': abs(win_pnl / len(wins) / loss_pnl * len(losses)) if losses and win_pnl != 0 else 0
                }
        
        return results
    
    def analyze_by_regime(self, trades: List[Dict]) -> Dict:
        """Analyze performance by market regime"""
        if not trades:
            return {}
        
        regimes = defaultdict(list)
        for trade in trades:
            regime = trade.get('regime', 'UNKNOWN')
            regimes[regime].append(trade)
        
        results = {}
        for regime, regime_trades in regimes.items():
            wins = [t for t in regime_trades if t.get('is_win', False)]
            losses = [t for t in regime_trades if not t.get('is_win', False)]
            
            total_pnl = sum(t.get('pnl', 0) for t in regime_trades)
            win_pnl = sum(t.get('pnl', 0) for t in wins)
            loss_pnl = sum(t.get('pnl', 0) for t in losses)
            
            results[regime] = {
                'total_trades': len(regime_trades),
                'wins': len(wins),
                'losses': len(losses),
                'win_rate': len(wins) / len(regime_trades) * 100 if regime_trades else 0,
                'total_pnl': total_pnl,
                'avg_pnl': total_pnl / len(regime_trades) if regime_trades else 0,
                'avg_win': win_pnl / len(wins) if wins else 0,
                'avg_loss': loss_pnl / len(losses) if losses else 0,
                'profit_factor': abs(win_pnl / loss_pnl) if loss_pnl != 0 else float('inf'),
            }
        
        return results
    
    def analyze_by_trade_class(self, trades: List[Dict]) -> Dict:
        """Analyze performance by trade class"""
        if not trades:
            return {}
        
        classes = defaultdict(list)
        for trade in trades:
            trade_class = trade.get('trade_class', 'UNKNOWN')
            classes[trade_class].append(trade)
        
        results = {}
        for trade_class, class_trades in classes.items():
            wins = [t for t in class_trades if t.get('is_win', False)]
            losses = [t for t in class_trades if not t.get('is_win', False)]
            
            total_pnl = sum(t.get('pnl', 0) for t in class_trades)
            win_pnl = sum(t.get('pnl', 0) for t in wins)
            loss_pnl = sum(t.get('pnl', 0) for t in losses)
            
            results[trade_class] = {
                'total_trades': len(class_trades),
                'wins': len(wins),
                'losses': len(losses),
                'win_rate': len(wins) / len(class_trades) * 100 if class_trades else 0,
                'total_pnl': total_pnl,
                'avg_pnl': total_pnl / len(class_trades) if class_trades else 0,
                'avg_win': win_pnl / len(wins) if wins else 0,
                'avg_loss': loss_pnl / len(losses) if losses else 0,
                'profit_factor': abs(win_pnl / loss_pnl) if loss_pnl != 0 else float('inf'),
            }
        
        return results
    
    def analyze_by_symbol(self, trades: List[Dict]) -> Dict:
        """Analyze performance by trading symbol"""
        if not trades:
            return {}
        
        symbols = defaultdict(list)
        for trade in trades:
            symbol = trade.get('symbol', 'UNKNOWN')
            symbols[symbol].append(trade)
        
        results = {}
        for symbol, symbol_trades in symbols.items():
            wins = [t for t in symbol_trades if t.get('is_win', False)]
            losses = [t for t in symbol_trades if not t.get('is_win', False)]
            
            total_pnl = sum(t.get('pnl', 0) for t in symbol_trades)
            win_pnl = sum(t.get('pnl', 0) for t in wins)
            loss_pnl = sum(t.get('pnl', 0) for t in losses)
            
            results[symbol] = {
                'total_trades': len(symbol_trades),
                'wins': len(wins),
                'losses': len(losses),
                'win_rate': len(wins) / len(symbol_trades) * 100 if symbol_trades else 0,
                'total_pnl': total_pnl,
                'avg_pnl': total_pnl / len(symbol_trades) if symbol_trades else 0,
                'avg_win': win_pnl / len(wins) if wins else 0,
                'avg_loss': loss_pnl / len(losses) if losses else 0,
                'profit_factor': abs(win_pnl / loss_pnl) if loss_pnl != 0 else float('inf'),
            }
        
        return results
    
    def analyze_by_leverage(self, trades: List[Dict]) -> Dict:
        """Analyze performance by leverage"""
        if not trades:
            return {}
        
        leverage_buckets = {
            '10x': (10, 12),
            '15x': (15, 17),
            '20x': (20, 25)
        }
        
        results = {}
        for bucket_name, (min_lev, max_lev) in leverage_buckets.items():
            bucket_trades = [
                t for t in trades 
                if min_lev <= t.get('applied_leverage', 0) < max_lev
            ]
            
            if bucket_trades:
                wins = [t for t in bucket_trades if t.get('is_win', False)]
                losses = [t for t in bucket_trades if not t.get('is_win', False)]
                
                total_pnl = sum(t.get('pnl', 0) for t in bucket_trades)
                win_pnl = sum(t.get('pnl', 0) for t in wins)
                loss_pnl = sum(t.get('pnl', 0) for t in losses)
                
                results[bucket_name] = {
                    'total_trades': len(bucket_trades),
                    'wins': len(wins),
                    'losses': len(losses),
                    'win_rate': len(wins) / len(bucket_trades) * 100 if bucket_trades else 0,
                    'total_pnl': total_pnl,
                    'avg_pnl': total_pnl / len(bucket_trades) if bucket_trades else 0,
                    'avg_win': win_pnl / len(wins) if wins else 0,
                    'avg_loss': loss_pnl / len(losses) if losses else 0,
                    'profit_factor': abs(win_pnl / loss_pnl) if loss_pnl != 0 else float('inf'),
                }
        
        return results
    
    def analyze_by_risk_pct(self, trades: List[Dict]) -> Dict:
        """Analyze performance by risk percentage"""
        if not trades:
            return {}
        
        risk_buckets = {
            '0.5%': (0.004, 0.006),
            '0.8%': (0.007, 0.009),
            '1.0%': (0.009, 0.011)
        }
        
        results = {}
        for bucket_name, (min_risk, max_risk) in risk_buckets.items():
            bucket_trades = [
                t for t in trades 
                if min_risk <= t.get('risk_pct', 0) < max_risk
            ]
            
            if bucket_trades:
                wins = [t for t in bucket_trades if t.get('is_win', False)]
                losses = [t for t in bucket_trades if not t.get('is_win', False)]
                
                total_pnl = sum(t.get('pnl', 0) for t in bucket_trades)
                win_pnl = sum(t.get('pnl', 0) for t in wins)
                loss_pnl = sum(t.get('pnl', 0) for t in losses)
                
                results[bucket_name] = {
                    'total_trades': len(bucket_trades),
                    'wins': len(wins),
                    'losses': len(losses),
                    'win_rate': len(wins) / len(bucket_trades) * 100 if bucket_trades else 0,
                    'total_pnl': total_pnl,
                    'avg_pnl': total_pnl / len(bucket_trades) if bucket_trades else 0,
                    'avg_win': win_pnl / len(wins) if wins else 0,
                    'avg_loss': loss_pnl / len(losses) if losses else 0,
                    'profit_factor': abs(win_pnl / loss_pnl) if loss_pnl != 0 else float('inf'),
                }
        
        return results
    
    def analyze_signals(self) -> Dict:
        """Analyze signal generation and conversion"""
        if not self.signals:
            return {}
        
        total_signals = len(self.signals)
        executed_signals = len([s for s in self.signals if s.get('signal') in ['LONG', 'SHORT']])
        no_trade_signals = len([s for s in self.signals if s.get('signal') == 'NO-TRADE'])
        
        # Confidence distribution
        executed_confidences = [s.get('confidence', 0) for s in self.signals if s.get('signal') in ['LONG', 'SHORT']]
        skipped_confidences = [s.get('confidence', 0) for s in self.signals if s.get('signal') == 'NO-TRADE']
        
        # Regime distribution
        regimes = defaultdict(int)
        for signal in self.signals:
            regimes[signal.get('regime', 'UNKNOWN')] += 1
        
        return {
            'total_signals': total_signals,
            'executed_signals': executed_signals,
            'no_trade_signals': no_trade_signals,
            'conversion_rate': executed_signals / total_signals * 100 if total_signals > 0 else 0,
            'avg_confidence_executed': np.mean(executed_confidences) if executed_confidences else 0,
            'avg_confidence_skipped': np.mean(skipped_confidences) if skipped_confidences else 0,
            'regime_distribution': dict(regimes)
        }
    
    def generate_insights(self, trades: List[Dict], analysis_results: Dict) -> List[str]:
        """Generate actionable insights and recommendations"""
        insights = []
        
        if not trades:
            insights.append("⚠️  No trades found in last 24 hours - cannot generate insights")
            return insights
        
        # Overall performance
        total_trades = len(trades)
        wins = [t for t in trades if t.get('is_win', False)]
        losses = [t for t in trades if not t.get('is_win', False)]
        win_rate = len(wins) / total_trades * 100 if total_trades > 0 else 0
        total_pnl = sum(t.get('pnl', 0) for t in trades)
        
        # Confidence insights
        conf_analysis = analysis_results.get('by_confidence', {})
        if conf_analysis:
            best_conf_bucket = max(conf_analysis.items(), key=lambda x: x[1].get('win_rate', 0))
            worst_conf_bucket = min(conf_analysis.items(), key=lambda x: x[1].get('win_rate', 100))
            
            if best_conf_bucket[1].get('win_rate', 0) > win_rate + 10:
                insights.append(f"✅ Confidence bucket {best_conf_bucket[0]} performs best ({best_conf_bucket[1]['win_rate']:.1f}% win rate) - consider focusing on this range")
            
            if worst_conf_bucket[1].get('win_rate', 0) < win_rate - 10:
                insights.append(f"⚠️  Confidence bucket {worst_conf_bucket[0]} underperforms ({worst_conf_bucket[1]['win_rate']:.1f}% win rate) - consider raising threshold or avoiding")
        
        # Regime insights
        regime_analysis = analysis_results.get('by_regime', {})
        if regime_analysis:
            best_regime = max(regime_analysis.items(), key=lambda x: x[1].get('win_rate', 0))
            worst_regime = min(regime_analysis.items(), key=lambda x: x[1].get('win_rate', 100))
            
            if best_regime[1].get('win_rate', 0) > 60:
                insights.append(f"✅ Regime {best_regime[0]} is highly profitable ({best_regime[1]['win_rate']:.1f}% win rate, ${best_regime[1]['total_pnl']:.2f} PnL) - prioritize this regime")
            
            if worst_regime[1].get('win_rate', 0) < 40 and worst_regime[1].get('total_pnl', 0) < 0:
                insights.append(f"⚠️  Regime {worst_regime[0]} is underperforming ({worst_regime[1]['win_rate']:.1f}% win rate, ${worst_regime[1]['total_pnl']:.2f} PnL) - consider avoiding or reducing exposure")
        
        # Trade class insights
        class_analysis = analysis_results.get('by_trade_class', {})
        if class_analysis:
            best_class = max(class_analysis.items(), key=lambda x: x[1].get('win_rate', 0))
            if best_class[1].get('win_rate', 0) > win_rate + 5:
                insights.append(f"✅ Trade class {best_class[0]} performs best ({best_class[1]['win_rate']:.1f}% win rate) - consider increasing allocation")
        
        # Symbol insights
        symbol_analysis = analysis_results.get('by_symbol', {})
        if symbol_analysis:
            best_symbol = max(symbol_analysis.items(), key=lambda x: x[1].get('total_pnl', float('-inf')))
            worst_symbol = min(symbol_analysis.items(), key=lambda x: x[1].get('total_pnl', float('inf')))
            
            if best_symbol[1].get('total_pnl', 0) > 0:
                insights.append(f"✅ Symbol {best_symbol[0]} is most profitable (${best_symbol[1]['total_pnl']:.2f} PnL, {best_symbol[1]['win_rate']:.1f}% win rate)")
            
            if worst_symbol[1].get('total_pnl', 0) < -10:
                insights.append(f"⚠️  Symbol {worst_symbol[0]} is losing money (${worst_symbol[1]['total_pnl']:.2f} PnL, {worst_symbol[1]['win_rate']:.1f}% win rate) - review strategy")
        
        # Leverage insights
        leverage_analysis = analysis_results.get('by_leverage', {})
        if leverage_analysis:
            for lev, stats in leverage_analysis.items():
                if stats.get('win_rate', 0) < 40 and stats.get('total_pnl', 0) < 0:
                    insights.append(f"⚠️  {lev} leverage underperforming ({stats['win_rate']:.1f}% win rate) - consider reducing leverage for this confidence range")
        
        # Overall win rate recommendation
        if win_rate < 45:
            insights.append(f"⚠️  Overall win rate is low ({win_rate:.1f}%) - consider:")
            insights.append("   - Raising minimum confidence threshold (currently 0.52)")
            insights.append("   - Focusing on higher-performing regimes")
            insights.append("   - Reducing position sizes or leverage")
        elif win_rate > 55:
            insights.append(f"✅ Overall win rate is good ({win_rate:.1f}%) - current strategy is working well")
        
        # Profit factor
        total_wins = sum(t.get('pnl', 0) for t in wins)
        total_losses = abs(sum(t.get('pnl', 0) for t in losses))
        profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')
        
        if profit_factor < 1.0:
            insights.append(f"⚠️  Profit factor is below 1.0 ({profit_factor:.2f}) - losses exceed wins, review risk management")
        elif profit_factor > 2.0:
            insights.append(f"✅ Profit factor is excellent ({profit_factor:.2f}) - strong risk-adjusted returns")
        
        return insights
    
    def generate_report(self, trades: List[Dict], analysis_results: Dict) -> Dict:
        """Generate comprehensive analysis report"""
        wins = [t for t in trades if t.get('is_win', False)]
        losses = [t for t in trades if not t.get('is_win', False)]
        total_pnl = sum(t.get('pnl', 0) for t in trades)
        win_pnl = sum(t.get('pnl', 0) for t in wins)
        loss_pnl = abs(sum(t.get('pnl', 0) for t in losses))
        
        report = {
            'analysis_period': {
                'start': self.start_time.isoformat(),
                'end': self.end_time.isoformat(),
                'duration_hours': 24
            },
            'overall_performance': {
                'total_trades': len(trades),
                'wins': len(wins),
                'losses': len(losses),
                'win_rate': len(wins) / len(trades) * 100 if trades else 0,
                'total_pnl': total_pnl,
                'avg_pnl': total_pnl / len(trades) if trades else 0,
                'avg_win': win_pnl / len(wins) if wins else 0,
                'avg_loss': loss_pnl / len(losses) if losses else 0,
                'profit_factor': win_pnl / loss_pnl if loss_pnl > 0 else float('inf'),
                'risk_reward_ratio': (win_pnl / len(wins)) / (loss_pnl / len(losses)) if losses and wins else 0
            },
            'by_confidence': analysis_results.get('by_confidence', {}),
            'by_regime': analysis_results.get('by_regime', {}),
            'by_trade_class': analysis_results.get('by_trade_class', {}),
            'by_symbol': analysis_results.get('by_symbol', {}),
            'by_leverage': analysis_results.get('by_leverage', {}),
            'by_risk_pct': analysis_results.get('by_risk_pct', {}),
            'signal_analysis': analysis_results.get('signal_analysis', {}),
            'insights': analysis_results.get('insights', []),
            'raw_trades': trades
        }
        
        return report
    
    def print_report(self, report: Dict):
        """Print formatted console report"""
        print("\n" + "="*80)
        print("TRADE PERFORMANCE ANALYSIS - LAST 24 HOURS")
        print("="*80)
        
        overall = report.get('overall_performance', {})
        print(f"\n📊 OVERALL PERFORMANCE")
        print(f"  Total Trades:      {overall.get('total_trades', 0)}")
        print(f"  Wins:              {overall.get('wins', 0)}")
        print(f"  Losses:            {overall.get('losses', 0)}")
        print(f"  Win Rate:          {overall.get('win_rate', 0):.2f}%")
        print(f"  Total PnL:         ${overall.get('total_pnl', 0):.4f}")
        print(f"  Avg PnL/Trade:     ${overall.get('avg_pnl', 0):.4f}")
        print(f"  Avg Win:           ${overall.get('avg_win', 0):.4f}")
        print(f"  Avg Loss:          ${overall.get('avg_loss', 0):.4f}")
        print(f"  Profit Factor:     {overall.get('profit_factor', 0):.2f}")
        print(f"  Risk-Reward Ratio: {overall.get('risk_reward_ratio', 0):.2f}")
        
        # By Confidence
        conf_analysis = report.get('by_confidence', {})
        if conf_analysis:
            print(f"\n📈 PERFORMANCE BY CONFIDENCE LEVEL")
            print(f"{'Bucket':<12} {'Trades':<8} {'Win Rate':<10} {'Total PnL':<12} {'Profit Factor':<15}")
            print("-" * 60)
            for bucket, stats in sorted(conf_analysis.items()):
                print(f"{bucket:<12} {stats['total_trades']:<8} {stats['win_rate']:<9.1f}% ${stats['total_pnl']:<11.4f} {stats['profit_factor']:<15.2f}")
        
        # By Regime
        regime_analysis = report.get('by_regime', {})
        if regime_analysis:
            print(f"\n📊 PERFORMANCE BY REGIME")
            print(f"{'Regime':<25} {'Trades':<8} {'Win Rate':<10} {'Total PnL':<12} {'Profit Factor':<15}")
            print("-" * 75)
            for regime, stats in sorted(regime_analysis.items(), key=lambda x: x[1]['total_pnl'], reverse=True):
                print(f"{regime:<25} {stats['total_trades']:<8} {stats['win_rate']:<9.1f}% ${stats['total_pnl']:<11.4f} {stats['profit_factor']:<15.2f}")
        
        # By Trade Class
        class_analysis = report.get('by_trade_class', {})
        if class_analysis:
            print(f"\n🎯 PERFORMANCE BY TRADE CLASS")
            print(f"{'Class':<20} {'Trades':<8} {'Win Rate':<10} {'Total PnL':<12} {'Profit Factor':<15}")
            print("-" * 70)
            for trade_class, stats in sorted(class_analysis.items(), key=lambda x: x[1]['total_pnl'], reverse=True):
                print(f"{trade_class:<20} {stats['total_trades']:<8} {stats['win_rate']:<9.1f}% ${stats['total_pnl']:<11.4f} {stats['profit_factor']:<15.2f}")
        
        # By Symbol
        symbol_analysis = report.get('by_symbol', {})
        if symbol_analysis:
            print(f"\n💱 PERFORMANCE BY SYMBOL")
            print(f"{'Symbol':<15} {'Trades':<8} {'Win Rate':<10} {'Total PnL':<12} {'Profit Factor':<15}")
            print("-" * 65)
            for symbol, stats in sorted(symbol_analysis.items(), key=lambda x: x[1]['total_pnl'], reverse=True):
                print(f"{symbol:<15} {stats['total_trades']:<8} {stats['win_rate']:<9.1f}% ${stats['total_pnl']:<11.4f} {stats['profit_factor']:<15.2f}")
        
        # By Leverage
        leverage_analysis = report.get('by_leverage', {})
        if leverage_analysis:
            print(f"\n⚡ PERFORMANCE BY LEVERAGE")
            print(f"{'Leverage':<10} {'Trades':<8} {'Win Rate':<10} {'Total PnL':<12} {'Profit Factor':<15}")
            print("-" * 60)
            for leverage, stats in sorted(leverage_analysis.items()):
                print(f"{leverage:<10} {stats['total_trades']:<8} {stats['win_rate']:<9.1f}% ${stats['total_pnl']:<11.4f} {stats['profit_factor']:<15.2f}")
        
        # Signal Analysis
        signal_analysis = report.get('signal_analysis', {})
        if signal_analysis:
            print(f"\n📡 SIGNAL ANALYSIS")
            print(f"  Total Signals:        {signal_analysis.get('total_signals', 0)}")
            print(f"  Executed Signals:     {signal_analysis.get('executed_signals', 0)}")
            print(f"  No-Trade Signals:     {signal_analysis.get('no_trade_signals', 0)}")
            print(f"  Conversion Rate:      {signal_analysis.get('conversion_rate', 0):.2f}%")
            print(f"  Avg Confidence (Exec): {signal_analysis.get('avg_confidence_executed', 0):.3f}")
            print(f"  Avg Confidence (Skip): {signal_analysis.get('avg_confidence_skipped', 0):.3f}")
        
        # Insights
        insights = report.get('insights', [])
        if insights:
            print(f"\n💡 KEY INSIGHTS & RECOMMENDATIONS")
            for i, insight in enumerate(insights, 1):
                print(f"  {i}. {insight}")
        
        print("\n" + "="*80)
    
    def run(self):
        """Run complete analysis"""
        print("="*80)
        print("SENTINEL ALPHA - TRADE PERFORMANCE ANALYZER")
        print("="*80)
        print(f"Analysis Period: {self.start_time.strftime('%Y-%m-%d %H:%M:%S UTC')} to {self.end_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        
        # Step 1: Parse log files
        self.parse_log_files()
        
        # Step 2: Fetch trade history from API
        trade_history = self.fetch_trade_history()
        
        # Step 3: Match trades with outcomes
        matched_trades = self.match_trades_with_outcomes(trade_history)
        
        # Step 4: Run all analyses
        print("\nRunning performance analyses...")
        analysis_results = {
            'by_confidence': self.analyze_by_confidence(matched_trades),
            'by_regime': self.analyze_by_regime(matched_trades),
            'by_trade_class': self.analyze_by_trade_class(matched_trades),
            'by_symbol': self.analyze_by_symbol(matched_trades),
            'by_leverage': self.analyze_by_leverage(matched_trades),
            'by_risk_pct': self.analyze_by_risk_pct(matched_trades),
            'signal_analysis': self.analyze_signals()
        }
        
        # Step 5: Generate insights
        insights = self.generate_insights(matched_trades, analysis_results)
        analysis_results['insights'] = insights
        
        # Step 6: Generate report
        report = self.generate_report(matched_trades, analysis_results)
        
        # Step 7: Print console report
        self.print_report(report)
        
        # Step 8: Save JSON report
        output_file = Path("logs/trade_analysis_24h.json")
        output_file.parent.mkdir(exist_ok=True)
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"\n✅ Analysis complete! Report saved to {output_file}")
        
        return report

if __name__ == "__main__":
    analyzer = TradePerformanceAnalyzer()
    analyzer.run()
