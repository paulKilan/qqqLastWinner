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
        super().__init__(allow_short=True)

    def _calculate_positions(self, data: pd.DataFrame, contextData=None) -> pd.DataFrame:
        # 12-day Rate of Change (ROC)
        roc = ((data['close'] - data['close'].shift(12)) / data['close'].shift(12)) * 100

        result_df = self._make_result_df(data)

        # ROC > 0 -> Bullish (Long); ROC < 0 -> Bearish (Short)
        result_df.loc[roc > 0, 'longPositionPct'] = 1.0
        result_df.loc[roc < 0, 'shortPositionPct'] = 1.0

        return self._apply_regime_filter(data, result_df)
