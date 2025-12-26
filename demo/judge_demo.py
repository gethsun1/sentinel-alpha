from data.market_stream import BinanceClientMock, MarketStream
from strategy.signal_engine import SignalEngine

CONFIG = "config/competition.yaml"

def run_demo():
    print("\n=== Sentinel Alpha | Judge Demo ===\n")

    client = BinanceClientMock()
    stream = MarketStream(client, symbol="BTCUSDT")

    market_data = stream.fetch_tick(limit=120)

    engine = SignalEngine(market_data, config_path=CONFIG)

    signals = engine.generate_signals()
    print("AI Signals:")
    print(signals.tail(3))

    print("\nExecuting (simulation mode)...")
    engine.execute_signals(signals.tail(1))

    print("\nDemo complete — audit logs generated.\n")

if __name__ == "__main__":
    run_demo()
