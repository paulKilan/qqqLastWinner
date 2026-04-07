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
        super().__init__(allow_short=True)

    def _calculate_positions(self, data: pd.DataFrame, contextData=None) -> pd.DataFrame:
        # Donchian Channels: use previous 20-day high/low (shift(1) excludes today)
        donchian_high = data['close'].rolling(window=20).max().shift(1)
        donchian_low = data['close'].rolling(window=20).min().shift(1)

        result_df = self._make_result_df(data)

        # Breakout above upper channel -> Long; below lower channel -> Short
        result_df.loc[data['close'] > donchian_high, 'longPositionPct'] = 1.0
        result_df.loc[data['close'] < donchian_low, 'shortPositionPct'] = 1.0

        return self._apply_regime_filter(data, result_df)
