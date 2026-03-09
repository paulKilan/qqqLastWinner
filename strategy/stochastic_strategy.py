'''
Backtest Results:
- Start Date: 2013-01-02
- End Date: 2024-12-31
- Initial Capital: $10,000.00
- Final Equity: $7,045.47
- Total Trades: 296
- Return: -29.55%
'''
from .base_strategy import BaseStrategy
import pandas as pd
import numpy as np

class StochasticStrategy(BaseStrategy):
    def __init__(self):
        super().__init__(allow_short=True)

    def _calculate_positions(self, data: pd.DataFrame, contextData=None) -> pd.DataFrame:
        # Stochastic %K = (Close - 14-day Low) / (14-day High - 14-day Low) * 100
        low_14 = data['close'].rolling(window=14).min()
        high_14 = data['close'].rolling(window=14).max()
        pct_k = 100 * ((data['close'] - low_14) / (high_14 - low_14))

        result_df = self._make_result_df(data)

        # %K < 20 -> Oversold -> Buy; %K > 80 -> Overbought -> Sell
        result_df.loc[pct_k < 20, 'longPositionPct'] = 1.0
        result_df.loc[pct_k > 80, 'shortPositionPct'] = 1.0

        return self._apply_regime_filter(data, result_df)
