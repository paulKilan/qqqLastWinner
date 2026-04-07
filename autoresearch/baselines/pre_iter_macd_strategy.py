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
        super().__init__(allow_short=True)

    def _calculate_positions(self, data: pd.DataFrame, contextData=None) -> pd.DataFrame:
        # MACD Line: 12-day EMA - 26-day EMA
        exp1 = data['close'].ewm(span=12, adjust=False).mean()
        exp2 = data['close'].ewm(span=26, adjust=False).mean()
        data['MACD'] = exp1 - exp2

        # Signal Line: 9-day EMA of MACD Line
        data['Signal'] = data['MACD'].ewm(span=9, adjust=False).mean()

        result_df = self._make_result_df(data)

        # MACD > Signal -> Bullish (Long); MACD < Signal -> Bearish (Short)
        result_df.loc[data['MACD'] > data['Signal'], 'longPositionPct'] = 1.0
        result_df.loc[data['MACD'] < data['Signal'], 'shortPositionPct'] = 1.0

        return self._apply_regime_filter(data, result_df)
