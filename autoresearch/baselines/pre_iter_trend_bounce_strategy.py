'''
Backtest Results:
- Start Date: 2013-01-02
- End Date: 2024-12-31
- Initial Capital: $10,000.00
- Final Equity: $7,283.78
- Total Trades: 76
- Return: -27.16%
'''
"""
Trend Bounce Trading Strategy

Based on the user's formula:
短线多:EMA(HIGH,25),COLORRED;
短线空:EMA(LOW,25),COLORGREEN;
长线多:EMA(H,90),COLORMAGENTA;
长线空:EMA(L,90),COLORBLUE;

Signals:
空 (Bear): REF(C,1)>REF(短线空,1) AND C<短线空 AND C<REF(C,1) AND COUNT(C>短线多,5)>0
多 (Bull): REF(C,1)<REF(短线多,1) AND C>短线多 AND C>REF(C,1) AND COUNT(C<长线多,5)>0
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict, Any
from .base_strategy import BaseStrategy

class TrendBounceStrategy(BaseStrategy):
    """
    Trend Bounce strategy based on EMA channels.
    """
    
    def __init__(self):
        super().__init__()

    def _calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calculate EMA channel indicators on the full dataset to avoid warmup bias."""
        df = data.copy()
        # EMA of High/Low (not Close) per the original formula
        high = df['high'] if 'high' in df.columns else df['close']
        low = df['low'] if 'low' in df.columns else df['close']
        df['short_bull'] = high.ewm(span=25, adjust=False).mean()  # 短线多
        df['short_bear'] = low.ewm(span=25, adjust=False).mean()   # 短线空
        df['long_bull'] = high.ewm(span=90, adjust=False).mean()   # 长线多
        df['long_bear'] = low.ewm(span=90, adjust=False).mean()    # 长线空
        return df

    def _calculate_positions(self, data: pd.DataFrame, contextData: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
        # Calculate indicators on the FULL dataset to avoid EMA warmup bias,
        # then slice to the requested date range.
        if self._data is None:
            self._load_data()

        df = self._calculate_indicators(self._data).loc[data.index].copy()

        result_df = self._make_result_df(df)

        prev_close = df['close'].shift(1)
        prev_short_bull = df['short_bull'].shift(1)
        prev_short_bear = df['short_bear'].shift(1)

        count_c_gt_short_bull = (df['close'] > df['short_bull']).rolling(window=5).sum() > 0
        count_c_lt_long_bull = (df['close'] < df['long_bull']).rolling(window=5).sum() > 0

        # Bull Signal (多): REF(C,1)<REF(短线多,1) AND C>短线多 AND C>REF(C,1) AND COUNT(C<长线多,5)>0
        bull_signal = (
            (prev_close < prev_short_bull) &
            (df['close'] > df['short_bull']) &
            (df['close'] > prev_close) &
            count_c_lt_long_bull
        )

        # Bear Signal (空): REF(C,1)>REF(短线空,1) AND C<短线空 AND C<REF(C,1) AND COUNT(C>短线多,5)>0
        bear_signal = (
            (prev_close > prev_short_bear) &
            (df['close'] < df['short_bear']) &
            (df['close'] < prev_close) &
            count_c_gt_short_bull
        )

        # Maintain position until a new signal fires (stateful — cannot be vectorized)
        current_pos = 0  # 0: Cash, 1: Long, -1: Short
        for i in range(len(df)):
            if bull_signal.iloc[i]:
                current_pos = 1
            elif bear_signal.iloc[i]:
                current_pos = -1

            idx = df.index[i]
            if current_pos == 1:
                result_df.loc[idx, 'longPositionPct'] = 1.0
            elif current_pos == -1:
                result_df.loc[idx, 'shortPositionPct'] = 1.0

        return result_df
