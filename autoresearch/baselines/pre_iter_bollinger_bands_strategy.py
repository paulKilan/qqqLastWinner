'''
Backtest Results:
- Start Date: 2013-01-02
- End Date: 2024-12-31
- Initial Capital: $10,000.00
- Final Equity: $25,441.19
- Total Trades: 106
- Return: 154.41%
'''
from .base_strategy import BaseStrategy
import pandas as pd
import numpy as np

class BollingerBandsStrategy(BaseStrategy):
    def __init__(self):
        super().__init__(allow_short=True)

    def _calculate_positions(self, data: pd.DataFrame, contextData=None) -> pd.DataFrame:
        # Calculate Bollinger Bands (20-day, 2 std dev)
        sma = data['close'].rolling(window=20).mean()
        std = data['close'].rolling(window=20).std()
        upper = sma + (std * 2)
        lower = sma - (std * 2)

        result_df = self._make_result_df(data)

        # Price < Lower Band -> Buy (Long); Price > Upper Band -> Sell (Short)
        result_df.loc[data['close'] < lower, 'longPositionPct'] = 1.0
        result_df.loc[data['close'] > upper, 'shortPositionPct'] = 1.0

        return self._apply_regime_filter(data, result_df)
