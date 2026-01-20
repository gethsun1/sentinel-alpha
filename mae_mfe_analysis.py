
import os
import sys
import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import bisect

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

plt.switch_backend('Agg')

class HighResMAEMFEAnalyzer:
    def __init__(self, 
                 historical_data_path="logs/weex_historical_data.json", 
                 ai_logs_path="logs/ai_logs_submitted.jsonl",
                 live_signals_path="logs/live_signals.jsonl"):
        self.historical_data_path = historical_data_path
        self.ai_logs_path = ai_logs_path
        self.live_signals_path = live_signals_path
        
    def load_order_history(self):
        print(f"Loading order history from {self.historical_data_path}...")
        with open(self.historical_data_path, "r") as f:
            data = json.load(f)
        return data.get("orders", [])

    def load_ai_logs(self):
        print(f"Loading AI logs from {self.ai_logs_path}...")
        ai_map = {}
        with open(self.ai_logs_path, "r") as f:
            for line in f:
                try:
                    log = json.loads(line)
                    oid = str(log.get('order_id') or log.get('orderId'))
                    if oid:
                        payload = log.get('payload', {})
                        input_data = payload.get('input', {})
                        output_data = payload.get('output', {})
                        ai_map[oid] = {
                            'atr': input_data.get('parameters', {}).get('atr') or output_data.get('tpsl', {}).get('atr'),
                            'regime': output_data.get('regime'),
                            'confidence': output_data.get('confidence'),
                            'signal': output_data.get('signal')
                        }
                except:
                    continue
        return ai_map

    def load_price_data(self):
        """Load live signals as a high-resolution price series"""
        print(f"Loading price series from {self.live_signals_path} (this may take a few seconds)...")
        price_series = {} # symbol -> [(timestamp, price)]
        
        count = 0
        with open(self.live_signals_path, "r") as f:
            for line in f:
                try:
                    log = json.loads(line)
                    symbol = log.get('symbol')
                    ts = log.get('timestamp')
                    price = log.get('price')
                    
                    if not symbol or not ts or not price:
                        continue
                        
                    # Handle both ISO strings and millisecond timestamps
                    if isinstance(ts, str):
                        try:
                            ts = int(datetime.fromisoformat(ts.replace('Z', '+00:00')).timestamp() * 1000)
                        except:
                            continue
                            
                    if symbol not in price_series:
                        price_series[symbol] = []
                    
                    price_series[symbol].append((ts, float(price)))
                    count += 1
                except:
                    continue
        
        # Sort each series by timestamp for bisect
        for sym in price_series:
            price_series[sym].sort()
            
        print(f"Loaded {count} price points for {len(price_series)} symbols.")
        return price_series

    def pair_trades(self, orders):
        print("Pairing orders into trades...")
        df_orders = pd.DataFrame(orders)
        if df_orders.empty:
            return []
            
        df_orders['createTime'] = pd.to_numeric(df_orders['createTime'])
        df_orders = df_orders.sort_values('createTime')
        
        trades = []
        active_positions = {}

        for _, row in df_orders.iterrows():
            symbol = row['symbol']
            otype = row['type']
            status = row['status']
            
            if status not in ['filled', 'partially_filled']:
                continue

            if otype in ['open_long', 'open_short']:
                active_positions[symbol] = row
            elif otype in ['close_long', 'close_short']:
                if symbol in active_positions:
                    open_order = active_positions.pop(symbol)
                    trades.append({
                        'symbol': symbol,
                        'entry_time': int(open_order['createTime']),
                        'exit_time': int(row['createTime']),
                        'entry_price': float(open_order['price_avg']),
                        'exit_price': float(row['price_avg']),
                        'side': 'LONG' if otype == 'close_long' else 'SHORT',
                        'entry_oid': str(open_order['order_id']),
                        'exit_oid': str(row['order_id']),
                        'pnl': float(row.get('totalProfits', 0))
                    })
        print(f"Paired {len(trades)} trades.")
        return trades

    def get_prices_for_range(self, price_series, symbol, start_ts, end_ts):
        """Retrieve all price points between start and end using binary search"""
        series = price_series.get(symbol, [])
        if not series:
            return []
            
        # Timestamps only for bisect
        ts_list = [x[0] for x in series]
        
        idx_start = bisect.bisect_left(ts_list, start_ts)
        idx_end = bisect.bisect_right(ts_list, end_ts)
        
        return [x[1] for x in series[idx_start:idx_end]]

    def run_analysis(self):
        orders = self.load_order_history()
        ai_map = self.load_ai_logs()
        price_series = self.load_price_data()
        raw_trades = self.pair_trades(orders)
        
        processed_trades = []
        print("Analyzing excursions for matched trades...")
        
        for trade in raw_trades:
            ai_info = ai_map.get(trade['entry_oid'])
            if not ai_info:
                continue
                
            atr = ai_info['atr']
            if not atr or atr <= 0:
                continue
                
            prices = self.get_prices_for_range(price_series, trade['symbol'], trade['entry_time'], trade['exit_time'])
            
            # If no mid-trade logs, use entry and exit prices as the range
            if not prices:
                prices = [trade['entry_price'], trade['exit_price']]
            else:
                # Include entry and exit prices in the range for completeness
                prices = [trade['entry_price']] + prices + [trade['exit_price']]
                
            entry_price = trade['entry_price']
            max_price = max(prices)
            min_price = min(prices)
            
            if trade['side'] == 'LONG':
                mfe = max_price - entry_price
                mae = entry_price - min_price
            else: # SHORT
                mfe = entry_price - min_price
                mae = max_price - entry_price
                
            trade.update({
                'atr': atr,
                'mae': mae,
                'mfe': mfe,
                'mae_atr': mae / atr,
                'mfe_atr': mfe / atr,
                'regime': ai_info['regime'],
                'confidence': ai_info['confidence'],
                'duration_sec': (trade['exit_time'] - trade['entry_time']) / 1000
            })
            processed_trades.append(trade)
            
        return pd.DataFrame(processed_trades)

    def generate_report(self, df):
        if df.empty:
            print("No data analyzed.")
            return

        print("\n" + "="*50)
        print("MAE / MFE ANALYSIS REPORT")
        print("="*50)
        
        # Overall stats
        print(f"\nTotal Analyzed Trades: {len(df)}")
        print(f"Average MAE/ATR: {df['mae_atr'].mean():.2f}")
        print(f"Average MFE/ATR: {df['mfe_atr'].mean():.2f}")
        print(f"Average Win Duration: {df[df['pnl'] > 0]['duration_sec'].mean():.1f}s")
        print(f"Average Loss Duration: {df[df['pnl'] <= 0]['duration_sec'].mean():.1f}s")

        # Premature Stop Analysis
        # Defined as trades where MAE/ATR was close to the limit (e.g. 0.7-1.5) and then MFE improved
        # Since we only have exit, we check if they hit SL but had some MFE
        print("\n--- Potential Premature Stops ---")
        stoppped_out = df[df['pnl'] <= 0]
        likely_premature = stoppped_out[stoppped_out['mae_atr'] > 0.5]
        print(f"Losses with MAE/ATR > 0.5: {len(likely_premature)} ({len(likely_premature)/len(df)*100:.1f}% of all trades)")
        
        # Plotting
        plt.figure(figsize=(15, 6))
        
        plt.subplot(1, 2, 1)
        plt.scatter(df['mae_atr'], df['pnl'], c=(df['pnl'] > 0), cmap='RdYlGn', alpha=0.6)
        plt.axvline(x=0.8, color='red', linestyle='--', label='Typical SL (0.8x)')
        plt.axvline(x=1.2, color='orange', linestyle='--', label='Proposed SL (1.2x)')
        plt.title('PnL vs. MAE/ATR')
        plt.xlabel('Max Adverse Excursion (Units of ATR)')
        plt.ylabel('PnL (USD)')
        plt.legend()
        plt.grid(True, alpha=0.3)

        plt.subplot(1, 2, 2)
        plt.scatter(df['mfe_atr'], df['pnl'], c=(df['pnl'] > 0), cmap='RdYlGn', alpha=0.6)
        plt.title('PnL vs. MFE/ATR')
        plt.xlabel('Max Favorable Excursion (Units of ATR)')
        plt.ylabel('PnL (USD)')
        plt.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig('logs/mae_mfe_highres_report.png')
        print(f"\nVisualization saved to: logs/mae_mfe_highres_report.png")
        
        # Summary by Regime
        print("\n--- Stats by Regime ---")
        regime_stats = df.groupby('regime').agg({
            'mae_atr': 'mean',
            'mfe_atr': 'mean',
            'pnl': 'mean',
            'symbol': 'count'
        }).rename(columns={'symbol': 'count'})
        print(regime_stats)

        # Recommendation Logic
        avg_mae = df['mae_atr'].mean()
        if avg_mae > 0.7:
            print("\nRECOMMENDATION: Evidence strongly suggests widening stop losses.")
            print(f"Average adverse move is {avg_mae:.2f}x ATR, while current stops are often 0.7-0.8x ATR.")
        
        df.to_json("logs/mae_mfe_highres_data.json", orient="records")

if __name__ == "__main__":
    analyzer = HighResMAEMFEAnalyzer()
    df = analyzer.run_analysis()
    analyzer.generate_report(df)
