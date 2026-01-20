"""
Test Signal Generation After Fixes
Verify that signals are now being generated properly
"""

import sys
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta

# Import the AI engine
from ai_enhanced_engine import AIEnhancedSignalEngine

def create_sample_market_data(n_points=100, price_start=87500):
    """
    Create realistic sample market data with various patterns
    """
    timestamps = []
    prices = []
    quantities = []
    
    base_time = datetime.now(timezone.utc) - timedelta(seconds=n_points*60)
    
    # Simulate realistic BTC price movement
    current_price = price_start
    
    for i in range(n_points):
        timestamps.append(base_time + timedelta(seconds=i*60))
        
        # Add some realistic price movement (Brownian motion + trend)
        trend = 0.0002 if i > 50 else -0.0001  # Trend changes midway
        noise = np.random.normal(0, 0.0005)  # Random volatility
        price_change = current_price * (trend + noise)
        current_price += price_change
        
        prices.append(current_price)
        quantities.append(np.random.uniform(0.1, 2.0))  # Random volume
    
    return pd.DataFrame({
        'timestamp': timestamps,
        'price': prices,
        'quantity': quantities
    })


def test_signal_generation():
    """Test the AI signal engine with sample data"""
    
    print("="*70)
    print("TESTING SIGNAL GENERATION AFTER FIXES")
    print("="*70)
    print()
    
    # Create sample data
    print("Creating sample market data (100 ticks)...")
    market_data = create_sample_market_data(100)
    print(f"✓ Generated {len(market_data)} data points")
    print(f"  Price range: ${market_data['price'].min():.2f} - ${market_data['price'].max():.2f}")
    print(f"  Price change: {((market_data['price'].iloc[-1] / market_data['price'].iloc[0]) - 1) * 100:.2f}%")
    print()
    
    # Generate signals
    print("Generating signals with AI-Enhanced Engine...")
    engine = AIEnhancedSignalEngine(market_data)
    signals = engine.generate_signals()
    print(f"✓ Generated {len(signals)} signals")
    print()
    
    # Analyze results
    print("SIGNAL DISTRIBUTION:")
    print("-"*70)
    signal_counts = signals['signal'].value_counts()
    total = len(signals)
    
    for signal_type in ['LONG', 'SHORT', 'NO-TRADE']:
        count = signal_counts.get(signal_type, 0)
        pct = (count / total) * 100
        print(f"  {signal_type:12s}: {count:4d} ({pct:5.1f}%)")
    
    print()
    print("CONFIDENCE STATISTICS:")
    print("-"*70)
    print(f"  Mean confidence:   {signals['calibrated_confidence'].mean():.3f}")
    print(f"  Median confidence: {signals['calibrated_confidence'].median():.3f}")
    print(f"  Min confidence:    {signals['calibrated_confidence'].min():.3f}")
    print(f"  Max confidence:    {signals['calibrated_confidence'].max():.3f}")
    
    print()
    print("REGIME DISTRIBUTION:")
    print("-"*70)
    regime_counts = signals['regime'].value_counts()
    for regime, count in regime_counts.items():
        pct = (count / total) * 100
        print(f"  {regime:25s}: {count:4d} ({pct:5.1f}%)")
    
    print()
    print("TRADEABLE SIGNALS (Confidence >= 0.45):")
    print("-"*70)
    tradeable = signals[
        (signals['signal'].isin(['LONG', 'SHORT'])) & 
        (signals['calibrated_confidence'] >= 0.45)
    ]
    print(f"  Total tradeable signals: {len(tradeable)}")
    if len(tradeable) > 0:
        print(f"  LONG signals:  {(tradeable['signal'] == 'LONG').sum()}")
        print(f"  SHORT signals: {(tradeable['signal'] == 'SHORT').sum()}")
        print(f"  Avg confidence: {tradeable['calibrated_confidence'].mean():.3f}")
    
    print()
    print("SAMPLE SIGNALS (Last 10):")
    print("-"*70)
    for idx in range(max(0, len(signals)-10), len(signals)):
        row = signals.iloc[idx]
        signal_str = f"{row['signal']:8s}"
        conf_str = f"{row['calibrated_confidence']:.3f}"
        regime_str = f"{row['regime']:25s}"
        
        # Color coding
        if row['signal'] == 'LONG':
            signal_color = '\033[92m'  # Green
        elif row['signal'] == 'SHORT':
            signal_color = '\033[91m'  # Red
        else:
            signal_color = '\033[93m'  # Yellow
        
        print(f"  [{idx:3d}] {signal_color}{signal_str}\033[0m | Conf: {conf_str} | {regime_str}")
    
    print()
    print("="*70)
    
    # Check if fixes worked
    long_count = (signals['signal'] == 'LONG').sum()
    short_count = (signals['signal'] == 'SHORT').sum()
    total_trades = long_count + short_count
    
    print()
    if total_trades > 0:
        print(f"\033[92m✓ SUCCESS! Bot is now generating {total_trades} trade signals!\033[0m")
        print(f"  Previous issue: 0% trade signals")
        print(f"  After fixes:    {(total_trades/total)*100:.1f}% trade signals")
    else:
        print(f"\033[91m✗ ISSUE: Still generating 0 trade signals\033[0m")
        print(f"  Need further adjustments")
    
    print()
    
    return signals


if __name__ == "__main__":
    signals = test_signal_generation()

