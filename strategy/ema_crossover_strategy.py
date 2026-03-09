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
        super().__init__(allow_short=True)

    def _calculate_positions(self, data: pd.DataFrame, contextData=None) -> pd.DataFrame:
        ema_50 = data['close'].ewm(span=50, adjust=False).mean()
        ema_200 = data['close'].ewm(span=200, adjust=False).mean()

        result_df = self._make_result_df(data)

        # Long when EMA 50 > EMA 200; Short when EMA 50 < EMA 200
        result_df.loc[ema_50 > ema_200, 'longPositionPct'] = 1.0
        result_df.loc[ema_50 < ema_200, 'shortPositionPct'] = 1.0

        return self._apply_regime_filter(data, result_df)
