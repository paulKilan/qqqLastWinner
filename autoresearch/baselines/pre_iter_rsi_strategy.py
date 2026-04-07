'''
Backtest Results:
- Start Date: 2013-01-02
- End Date: 2024-12-31
- Initial Capital: $10,000.00
- Final Equity: $19,642.59
- Total Trades: 120
- Return: 96.43%
'''
from .base_strategy import BaseStrategy
import pandas as pd
import numpy as np

class RsiStrategy(BaseStrategy):
    def __init__(self):
        super().__init__(allow_short=True)

    def _calculate_positions(self, data: pd.DataFrame, contextData=None) -> pd.DataFrame:
        # Calculate RSI
        delta = data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()

        rs = gain / loss
        data['RSI'] = 100 - (100 / (1 + rs))

        result_df = self._make_result_df(data)

        # RSI < 30 -> Oversold -> Buy (Long)
        # RSI > 70 -> Overbought -> Sell (Short)
        result_df.loc[data['RSI'] < 30, 'longPositionPct'] = 1.0
        result_df.loc[data['RSI'] > 70, 'shortPositionPct'] = 1.0

        return self._apply_regime_filter(data, result_df)
