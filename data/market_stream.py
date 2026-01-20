import pandas as pd
import datetime
from typing import Dict, Any

# Placeholder for Binance API client
class BinanceClientMock:
    """
    This is a demo placeholder for Binance API client.
    Replace with actual 'python-binance' client for real testing.
    """
    def get_recent_trades(self, symbol: str, limit: int = 100) -> list:
        """
        Returns a list of recent trades.
        Each trade is a dict: { 'price': float, 'qty': float, 'timestamp': int }
        """
        # Demo / static data
        now = int(datetime.datetime.utcnow().timestamp() * 1000)
        trades = [{
            'price': 50000 + i * 10,
            'qty': 0.01 + 0.01 * i,
            'timestamp': now - i*1000
        } for i in range(limit)]
        return trades

class MarketStream:
    def __init__(self, client: Any, symbol: str):
        self.client = client
        self.symbol = symbol

    def fetch_tick(self) -> pd.DataFrame:
        """
        Fetches recent market trades and returns as a normalized DataFrame.
        Columns: timestamp, price, quantity
        """
        trades = self.client.get_recent_trades(self.symbol)
        df = pd.DataFrame(trades)
        # Convert timestamp to datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        # Normalize price and quantity
        df['price'] = pd.to_numeric(df['price'])
        df['quantity'] = pd.to_numeric(df['qty'])
        df = df[['timestamp', 'price', 'quantity']]
        return df

if __name__ == "__main__":
    # Demo run
    client = BinanceClientMock()
    stream = MarketStream(client, symbol="BTCUSDT")
    df = stream.fetch_tick()
    print(df.head())
