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
        super().__init__(allow_short=True)

    def _calculate_positions(self, data: pd.DataFrame, contextData=None) -> pd.DataFrame:
        # Williams %R = (14-day High - Close) / (14-day High - 14-day Low) * -100
        # Uses 'high'/'low' columns normalized by BaseStrategy._load_data()
        high_col = data['high'] if 'high' in data.columns else data['close']
        low_col = data['low'] if 'low' in data.columns else data['close']

        high_n = high_col.rolling(window=14).max()
        low_n = low_col.rolling(window=14).min()
        pct_r = ((high_n - data['close']) / (high_n - low_n)) * -100

        result_df = self._make_result_df(data)

        # %R < -80 -> Oversold -> Buy (Long); %R > -20 -> Overbought -> Sell (Short)
        result_df.loc[pct_r < -80, 'longPositionPct'] = 1.0
        result_df.loc[pct_r > -20, 'shortPositionPct'] = 1.0

        return self._apply_regime_filter(data, result_df)
