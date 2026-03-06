'''
Backtest Results:
- Start Date: 2013-01-02
- End Date: 2024-12-31
- Initial Capital: $10,000.00
- Final Equity: $2,420.33
- Total Trades: 184
- Return: -75.80%
'''
from .base_strategy import BaseStrategy
import pandas as pd
import numpy as np

class MacdStrategy(BaseStrategy):
    def __init__(self):
        super().__init__(allow_short=True, use_regime_filter=True)
        self.data_file = 'QQQ.csv'

    def _calculate_positions(self, data: pd.DataFrame, contextData=None) -> pd.DataFrame:
        # Calculate MACD
        # MACD Line: 12-day EMA - 26-day EMA
        exp1 = data['close'].ewm(span=12, adjust=False).mean()
        exp2 = data['close'].ewm(span=26, adjust=False).mean()
        data['MACD'] = exp1 - exp2
        
        # Signal Line: 9-day EMA of MACD Line
        data['Signal'] = data['MACD'].ewm(span=9, adjust=False).mean()

        # Create result DataFrame
        result_df = pd.DataFrame(index=data.index)
        result_df.index.name = 'date'
        
        # Initialize columns
        result_df['longPositionPct'] = 0.0
        result_df['shortPositionPct'] = 0.0
        result_df['error'] = None

        # Generate signals
        # MACD > Signal -> Bullish (Long)
        long_condition = data['MACD'] > data['Signal']
        
        # MACD < Signal -> Bearish (Short)
        short_condition = data['MACD'] < data['Signal']

        # Apply signals
        result_df.loc[long_condition, 'longPositionPct'] = 1.0
        result_df.loc[short_condition, 'shortPositionPct'] = 1.0
        
        result_df = result_df.reset_index()
        result_df.set_index('date', inplace=True)

        return result_df
