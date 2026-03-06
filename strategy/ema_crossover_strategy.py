'''
Backtest Results:
- Start Date: 2013-01-02
- End Date: 2024-12-31
- Initial Capital: $10,000.00
- Final Equity: $201,953.12
- Total Trades: 21
- Return: 1919.53%
'''
from .base_strategy import BaseStrategy
import pandas as pd
import numpy as np

class EmaCrossoverStrategy(BaseStrategy):
    def __init__(self):
        super().__init__(allow_short=True, use_regime_filter=True)
        self.data_file = 'QQQ.csv'

    def _calculate_positions(self, data: pd.DataFrame, contextData=None) -> pd.DataFrame:
        # Calculate indicators
        data['EMA_50'] = data['close'].ewm(span=50, adjust=False).mean()
        data['EMA_200'] = data['close'].ewm(span=200, adjust=False).mean()

        # Create result DataFrame
        result_df = pd.DataFrame(index=data.index)
        result_df.index.name = 'date'
        
        # Initialize columns
        result_df['longPositionPct'] = 0.0
        result_df['shortPositionPct'] = 0.0
        result_df['error'] = None

        # Generate signals
        # Long when EMA 50 > EMA 200
        long_condition = data['EMA_50'] > data['EMA_200']
        
        # Short when EMA 50 < EMA 200
        short_condition = data['EMA_50'] < data['EMA_200']

        # Apply signals
        result_df.loc[long_condition, 'longPositionPct'] = 1.0
        result_df.loc[short_condition, 'shortPositionPct'] = 1.0
        
        result_df = result_df.reset_index()
        result_df.set_index('date', inplace=True)

        return result_df
