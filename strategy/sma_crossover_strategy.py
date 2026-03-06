'''
Backtest Results:
- Start Date: 2013-01-02
- End Date: 2024-12-31
- Initial Capital: $10,000.00
- Final Equity: $256,004.64
- Total Trades: 10
- Return: 2460.05%
'''
from .base_strategy import BaseStrategy
import pandas as pd
import numpy as np

class SmaCrossoverStrategy(BaseStrategy):
    def __init__(self):
        super().__init__()
        self.data_file = 'QQQ.csv'  # Override to use raw QQQ data

    def _calculate_positions(self, data: pd.DataFrame, contextData=None) -> pd.DataFrame:
        # Calculate indicators
        data['SMA_50'] = data['close'].rolling(window=50).mean()
        data['SMA_200'] = data['close'].rolling(window=200).mean()

        # Create result DataFrame
        result_df = pd.DataFrame(index=data.index)
        result_df.index.name = 'date'
        
        # Initialize columns
        result_df['longPositionPct'] = 0.0
        result_df['shortPositionPct'] = 0.0
        result_df['error'] = None

        # Generate signals
        # Long when SMA 50 > SMA 200
        long_condition = data['SMA_50'] > data['SMA_200']
        
        # Short when SMA 50 < SMA 200
        short_condition = data['SMA_50'] < data['SMA_200']

        # Apply signals
        result_df.loc[long_condition, 'longPositionPct'] = 1.0
        result_df.loc[short_condition, 'shortPositionPct'] = 1.0
        
        # Handle NaN at the beginning (due to rolling window)
        # We can just leave them as 0.0 (Cash) or forward fill if we had a previous state.
        # For simplicity, we stay in Cash until we have enough data.
        
        result_df = result_df.reset_index()
        result_df.set_index('date', inplace=True)

        return result_df
