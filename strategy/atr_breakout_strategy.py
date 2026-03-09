'''
Backtest Results:
- Start Date: 2013-01-02
- End Date: 2024-12-31
- Initial Capital: $10,000.00
- Final Equity: $1,401.49
- Total Trades: 325
- Return: -85.99%
'''
from .base_strategy import BaseStrategy
import pandas as pd
import numpy as np

class AtrBreakoutStrategy(BaseStrategy):
    def __init__(self):
        super().__init__(allow_short=True)

    def _calculate_positions(self, data: pd.DataFrame, contextData=None) -> pd.DataFrame:
        # ATR (Average True Range) using 'high'/'low' normalized by BaseStrategy._load_data()
        high = data['high'] if 'high' in data.columns else data['close']
        low = data['low'] if 'low' in data.columns else data['close']
        prev_close = data['close'].shift(1)

        tr = pd.concat([
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ], axis=1).max(axis=1)
        atr = tr.rolling(window=14).mean()

        # Buy if Close > PrevClose + 1*ATR; Sell if Close < PrevClose - 1*ATR
        upper_band = prev_close + atr
        lower_band = prev_close - atr

        result_df = self._make_result_df(data)
        result_df.loc[data['close'] > upper_band, 'longPositionPct'] = 1.0
        result_df.loc[data['close'] < lower_band, 'shortPositionPct'] = 1.0

        return self._apply_regime_filter(data, result_df)
