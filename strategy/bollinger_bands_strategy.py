'''
Backtest Results:
- Start Date: 2013-01-02
- End Date: 2024-12-31
- Initial Capital: $10,000.00
- Final Equity: $25,441.19
- Total Trades: 106
- Return: 154.41%
'''
from .base_strategy import BaseStrategy
import pandas as pd
import numpy as np

class BollingerBandsStrategy(BaseStrategy):
    def __init__(self):
        super().__init__(allow_short=True, use_regime_filter=True)
        self.data_file = 'QQQ.csv'

    def _calculate_positions(self, data: pd.DataFrame, contextData=None) -> pd.DataFrame:
        # Calculate Bollinger Bands
        data['SMA_20'] = data['close'].rolling(window=20).mean()
        data['STD_20'] = data['close'].rolling(window=20).std()
        data['Upper'] = data['SMA_20'] + (data['STD_20'] * 2)
        data['Lower'] = data['SMA_20'] - (data['STD_20'] * 2)

        # Create result DataFrame
        result_df = pd.DataFrame(index=data.index)
        result_df.index.name = 'date'
        
        # Initialize columns
        result_df['longPositionPct'] = 0.0
        result_df['shortPositionPct'] = 0.0
        result_df['error'] = None

        # Generate signals
        # Price < Lower Band -> Buy (Long)
        long_condition = data['close'] < data['Lower']
        
        # Price > Upper Band -> Sell (Short)
        short_condition = data['close'] > data['Upper']

        # Apply signals
        result_df.loc[long_condition, 'longPositionPct'] = 1.0
        result_df.loc[short_condition, 'shortPositionPct'] = 1.0
        
        result_df = result_df.reset_index()
        result_df.set_index('date', inplace=True)

        return result_df
