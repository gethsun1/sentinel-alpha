import matplotlib.pyplot as plt
import pandas as pd

class VisualReports:
    """
    Produces charts for demo or submission purposes.
    """

    def __init__(self, df_signals: pd.DataFrame):
        self.df = df_signals.copy()

    def plot_price_with_signals(self):
        plt.figure(figsize=(12,6))
        plt.plot(self.df['timestamp'], self.df['price'], label='Price', color='black')
        
        long_signals = self.df[self.df['signal']=='LONG']
        short_signals = self.df[self.df['signal']=='SHORT']

        plt.scatter(long_signals['timestamp'], long_signals['price'], color='green', marker='^', label='LONG')
        plt.scatter(short_signals['timestamp'], short_signals['price'], color='red', marker='v', label='SHORT')

        plt.title("Sentinel Alpha Price & Signals")
        plt.xlabel("Timestamp")
        plt.ylabel("Price")
        plt.legend()
        plt.tight_layout()
        plt.show()

    def plot_regimes(self):
        plt.figure(figsize=(12,4))
        self.df['regime'].value_counts().plot(kind='bar', color='blue')
        plt.title("Regime Distribution")
        plt.ylabel("Count")
        plt.tight_layout()
        plt.show()

    def plot_confidence(self):
        plt.figure(figsize=(12,4))
        plt.plot(self.df['timestamp'], self.df['confidence'], color='purple')
        plt.title("Signal Confidence Over Time")
        plt.xlabel("Timestamp")
        plt.ylabel("Confidence")
        plt.tight_layout()
        plt.show()

if __name__ == "__main__":
    from demo.historical_replay import HistoricalReplay

    df_demo = HistoricalReplay().simulate()
    reports = VisualReports(df_demo)
    reports.plot_price_with_signals()
    reports.plot_regimes()
    reports.plot_confidence()
