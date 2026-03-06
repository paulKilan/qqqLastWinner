'''
Backtest Results:
- Start Date: 2013-01-02
- End Date: 2024-12-31
- Initial Capital: $10,000.00
- Final Equity: $6,346.97
- Total Trades: 247
- Return: -36.53%
'''
from .base_strategy import BaseStrategy
import pandas as pd
import numpy as np

class MomentumStrategy(BaseStrategy):
    def __init__(self):
        super().__init__(allow_short=True, use_regime_filter=True)
        self.data_file = 'QQQ.csv'

    def _calculate_positions(self, data: pd.DataFrame, contextData=None) -> pd.DataFrame:
        # Calculate Rate of Change (ROC)
        n = 12 # 12-day ROC
        data['ROC'] = ((data['close'] - data['close'].shift(n)) / data['close'].shift(n)) * 100

        # Create result DataFrame
        result_df = pd.DataFrame(index=data.index)
        result_df.index.name = 'date'
        
        # Initialize columns
        result_df['longPositionPct'] = 0.0
        result_df['shortPositionPct'] = 0.0
        result_df['error'] = None

        # Generate signals
        # ROC > 0 -> Bullish (Long)
        long_condition = data['ROC'] > 0
        
        # ROC < 0 -> Bearish (Short)
        short_condition = data['ROC'] < 0

        # Apply signals
        result_df.loc[long_condition, 'longPositionPct'] = 1.0
        result_df.loc[short_condition, 'shortPositionPct'] = 1.0
        
        result_df = result_df.reset_index()
        result_df.set_index('date', inplace=True)

        return result_df
