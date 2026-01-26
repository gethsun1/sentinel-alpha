#!/usr/bin/env python3
"""
Comprehensive 24-hour performance analysis for Sentinel Alpha.
Analyzes post-fix period: Jan 25 16:40 UTC → Jan 26 13:25 UTC
"""

import json
import sys
from datetime import datetime, timedelta, timezone
from collections import defaultdict

def analyze_24h():
    """Analyze the last 24 hours of bot performance"""
    
    # Define analysis window
    now = datetime(2026, 1, 26, 13, 25, tzinfo=timezone.utc)
    fix_deployment = datetime(2026, 1, 25, 16, 40, tzinfo=timezone.utc)
    one_day_ago = now - timedelta(hours=24)
    
    print("=" * 80)
    print("SENTINEL ALPHA - 24 HOUR PERFORMANCE ANALYSIS")
    print("=" * 80)
    print(f"Analysis Window: {one_day_ago} → {now}")
    print(f"Fix Deployed: {fix_deployment}")
    print()
    
    # Load all trades
    all_trades = []
    with open('/root/sentinel-alpha/logs/live_trades.jsonl', 'r') as f:
        for line in f:
            try:
                trade = json.loads(line)
                ts_str = trade.get('timestamp')
                dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                trade['parsed_dt'] = dt
                all_trades.append(trade)
            except Exception as e:
                continue
    
    # Filter to analysis window
    window_trades = [t for t in all_trades if t['parsed_dt'] >= one_day_ago]
    post_fix_trades = [t for t in all_trades if t['parsed_dt'] >= fix_deployment]
    
    print(f"📊 TRADE VOLUME")
    print(f"   Total trades (all time): {len(all_trades)}")
    print(f"   Trades in last 24h: {len(window_trades)}")
    print(f"   Trades since fix (Jan 25 16:40): {len(post_fix_trades)}")
    print()
    
    if len(post_fix_trades) == 0:
        print("⚠️  CRITICAL: No trades executed since fix deployment!")
        print()
        print("Investigating signal generation...")
        analyze_signals()
        return
    
    # Analyze trade details
    print(f"📈 TRADE BREAKDOWN (Last 24h)")
    by_symbol = defaultdict(int)
    by_direction = defaultdict(int)
    by_class = defaultdict(int)
    
    for trade in window_trades:
        by_symbol[trade['symbol']] += 1
        by_direction[trade['signal']] += 1
        by_class[trade.get('trade_class', 'UNKNOWN')] += 1
    
    print(f"\n   By Symbol:")
    for sym, count in sorted(by_symbol.items(), key=lambda x: x[1], reverse=True):
        print(f"      {sym}: {count}")
    
    print(f"\n   By Direction:")
    for dir, count in by_direction.items():
        print(f"      {dir}: {count}")
    
    print(f"\n   By Trade Class:")
    for cls, count in by_class.items():
        print(f"      {cls}: {count}")
    
    # Analyze performance.jsonl for win rate
    print(f"\n💰 PERFORMANCE METRICS")
    try:
        with open('/root/sentinel-alpha/logs/performance.jsonl', 'r') as f:
            lines = f.readlines()
            latest = json.loads(lines[-1])
            print(f"   Current Equity: ${latest['equity']:.2f}")
            print(f"   Total PnL: ${latest['total_pnl']:.2f}")
            print(f"   ROI: {latest['roi']*100:.2f}%")
            print(f"   Trades Executed: {latest['trades']}")
            print(f"   Win Rate: {latest['win_rate']*100:.1f}%")
    except Exception as e:
        print(f"   Error reading performance: {e}")
    
    print("\n" + "=" * 80)

def analyze_signals():
    """Analyze why no trades are being executed"""
    print("\n🔍 SIGNAL GENERATION ANALYSIS")
    
    # Check recent signals
    try:
        with open('/root/sentinel-alpha/logs/live_signals.jsonl', 'r') as f:
            lines = f.readlines()
            recent_signals = []
            for line in lines[-100:]:
                try:
                    sig = json.loads(line)
                    recent_signals.append(sig)
                except:
                    continue
        
        if not recent_signals:
            print("   ⚠️  No signals found in recent history!")
            return
        
        # Analyze confidence distribution
        confidences = [s.get('confidence', 0) for s in recent_signals]
        avg_conf = sum(confidences) / len(confidences) if confidences else 0
        max_conf = max(confidences) if confidences else 0
        
        # Count signals above threshold
        above_60 = sum(1 for c in confidences if c >= 0.60)
        
        print(f"   Recent Signals Analyzed: {len(recent_signals)}")
        print(f"   Average Confidence: {avg_conf:.3f}")
        print(f"   Max Confidence: {max_conf:.3f}")
        print(f"   Signals ≥ 60% threshold: {above_60} ({above_60/len(recent_signals)*100:.1f}%)")
        
        if above_60 == 0:
            print(f"\n   ❌ ROOT CAUSE: No signals meeting 60% confidence threshold!")
            print(f"   → AI model is not generating high-conviction signals")
            print(f"   → Current setup is too conservative for market conditions")
        
        # Check high conviction signals
        try:
            with open('/root/sentinel-alpha/logs/high_conviction_signals.jsonl', 'r') as f:
                hc_signals = f.readlines()
                print(f"\n   High Conviction Signals Logged: {len(hc_signals)}")
        except:
            print(f"\n   High Conviction Signals: 0")
            
    except FileNotFoundError:
        print("   ⚠️  live_signals.jsonl not found!")
    except Exception as e:
        print(f"   Error analyzing signals: {e}")

if __name__ == "__main__":
    analyze_24h()
