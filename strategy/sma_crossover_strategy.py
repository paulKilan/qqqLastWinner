'''
Backtest Results:
- Start Date: 2013-01-02
- End Date: 2024-12-31
- Initial Capital: $10,000.00
- Final Equity: $256,004.64
- Total Trades: 10
- Return: 2460.05%
'''
from .base_strategy import BaseStrategy
import pandas as pd
import numpy as np

class SmaCrossoverStrategy(BaseStrategy):
    def __init__(self):
        super().__init__()

    def _calculate_positions(self, data: pd.DataFrame, contextData=None) -> pd.DataFrame:
        sma_50 = data['close'].rolling(window=50).mean()
        sma_200 = data['close'].rolling(window=200).mean()

        result_df = self._make_result_df(data)

        # Long when SMA 50 > SMA 200; Short when SMA 50 < SMA 200
        # NaN rows (first 200 days of warmup) stay at 0.0 (Cash)
        result_df.loc[sma_50 > sma_200, 'longPositionPct'] = 1.0
        result_df.loc[sma_50 < sma_200, 'shortPositionPct'] = 1.0

        return result_df
