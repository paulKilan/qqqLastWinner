'''
Backtest Results:
- Start Date: 2013-01-02
- End Date: 2024-12-31
- Initial Capital: $10,000.00
- Final Equity: $5,812.10
- Total Trades: 332
- Return: -41.88%
'''
from .base_strategy import BaseStrategy
import pandas as pd
import numpy as np

class DonchianChannelStrategy(BaseStrategy):
    def __init__(self):
        super().__init__(allow_short=True, use_regime_filter=True)
        self.data_file = 'QQQ.csv'

    def _calculate_positions(self, data: pd.DataFrame, contextData=None) -> pd.DataFrame:
        # Calculate Donchian Channels (20-day)
        window = 20
        data['High_20'] = data['close'].rolling(window=window).max()
        data['Low_20'] = data['close'].rolling(window=window).min()
        
        # Shift by 1 because we trade based on YESTERDAY's breakout
        # Actually, if we use today's close to decide, we trade tomorrow.
        # The backtester handles the shift.
        # But for Donchian, usually:
        # Buy if Price > High of previous 20 days.
        # Sell if Price < Low of previous 20 days.
        
        # We need the high/low of the *previous* window days, excluding today.
        # So we shift the rolling max/min by 1.
        data['Donchian_High'] = data['close'].rolling(window=window).max().shift(1)
        data['Donchian_Low'] = data['close'].rolling(window=window).min().shift(1)

        # Create result DataFrame
        result_df = pd.DataFrame(index=data.index)
        result_df.index.name = 'date'
        
        # Initialize columns
        result_df['longPositionPct'] = 0.0
        result_df['shortPositionPct'] = 0.0
        result_df['error'] = None

        # Generate signals
        # Breakout above upper channel -> Long
        long_condition = data['close'] > data['Donchian_High']
        
        # Breakout below lower channel -> Short
        short_condition = data['close'] < data['Donchian_Low']

        # Apply signals
        result_df.loc[long_condition, 'longPositionPct'] = 1.0
        result_df.loc[short_condition, 'shortPositionPct'] = 1.0
        
        result_df = result_df.reset_index()
        result_df.set_index('date', inplace=True)

        return result_df
