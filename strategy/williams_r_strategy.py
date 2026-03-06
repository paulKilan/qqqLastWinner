'''
Backtest Results:
- Start Date: 2013-01-02
- End Date: 2024-12-31
- Initial Capital: $10,000.00
- Final Equity: $8,516.81
- Total Trades: 278
- Return: -14.83%
'''
from .base_strategy import BaseStrategy
import pandas as pd
import numpy as np

class WilliamsRStrategy(BaseStrategy):
    def __init__(self):
        super().__init__(allow_short=True, use_regime_filter=True)
        self.data_file = 'QQQ.csv'

    def _calculate_positions(self, data: pd.DataFrame, contextData=None) -> pd.DataFrame:
        # Calculate Williams %R
        # %R = (Highest High - Close) / (Highest High - Lowest Low) * -100
        
        window = 14
        
        # Ensure High/Low are numeric
        for col in ['High', 'Low']:
            if col in data.columns and data[col].dtype == 'object':
                data[col] = pd.to_numeric(data[col].astype(str).str.replace(',', ''), errors='coerce')
        
        if 'High' not in data.columns or 'Low' not in data.columns:
             data['High'] = data['close']
             data['Low'] = data['close']

        high_n = data['High'].rolling(window=window).max()
        low_n = data['Low'].rolling(window=window).min()
        
        data['%R'] = ((high_n - data['close']) / (high_n - low_n)) * -100

        # Create result DataFrame
        result_df = pd.DataFrame(index=data.index)
        result_df.index.name = 'date'
        
        # Initialize columns
        result_df['longPositionPct'] = 0.0
        result_df['shortPositionPct'] = 0.0
        result_df['error'] = None

        # Generate signals
        # %R < -80 -> Oversold -> Buy (Long)
        # %R > -20 -> Overbought -> Sell (Short)
        
        long_condition = data['%R'] < -80
        short_condition = data['%R'] > -20

        # Apply signals
        result_df.loc[long_condition, 'longPositionPct'] = 1.0
        result_df.loc[short_condition, 'shortPositionPct'] = 1.0
        
        result_df = result_df.reset_index()
        result_df.set_index('date', inplace=True)

        return result_df
