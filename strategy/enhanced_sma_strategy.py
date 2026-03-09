'''
Backtest Results:
- Start Date: 2013-01-02
- End Date: 2024-12-31
- Initial Capital: $10,000.00
- Final Equity: $73,756.13
- Total Trades: 65
- Return: 637.56%
'''
from .base_strategy import BaseStrategy
import pandas as pd
import numpy as np

class EnhancedSmaStrategy(BaseStrategy):
    """
    Enhanced SMA Strategy demonstrating Long, Short, and Neutral positions.
    
    Logic:
    - Long (1): SMA 50 > SMA 200 (Golden Cross)
    - Short (-1): SMA 50 < SMA 200 (Death Cross)
    - Neutral (0): If ADX < 20 (Trend is weak), stay in Cash regardless of Cross.
    """
    
    def __init__(self):
        super().__init__(allow_short=True)

    def _calculate_positions(self, data: pd.DataFrame, contextData=None) -> pd.DataFrame:
        sma_50 = data['close'].rolling(window=50).mean()
        sma_200 = data['close'].rolling(window=200).mean()

        # ADX (Average Directional Index) for trend-strength filter
        # Uses 'high'/'low' normalized by BaseStrategy._load_data()
        high = data['high'] if 'high' in data.columns else data['close']
        low = data['low'] if 'low' in data.columns else data['close']
        close = data['close']

        up_move = high.diff()
        down_move = -low.diff()
        plus_dm = pd.Series(
            np.where((up_move > down_move) & (up_move > 0), up_move, 0.0),
            index=data.index,
        )
        minus_dm = pd.Series(
            np.where((down_move > up_move) & (down_move > 0), down_move, 0.0),
            index=data.index,
        )

        tr = pd.concat([
            high - low,
            (high - close.shift(1)).abs(),
            (low - close.shift(1)).abs(),
        ], axis=1).max(axis=1)
        atr = tr.rolling(14).mean()

        plus_di = 100 * (plus_dm.ewm(alpha=1/14).mean() / atr)
        minus_di = 100 * (minus_dm.ewm(alpha=1/14).mean() / atr)
        dx = (abs(plus_di - minus_di) / abs(plus_di + minus_di)) * 100
        adx = dx.rolling(14).mean()

        # Long: Golden Cross + strong trend; Short: Death Cross + strong trend; else Cash
        strong_trend = adx > 20
        signals = pd.Series(0, index=data.index)
        signals[(sma_50 > sma_200) & strong_trend] = 1
        signals[(sma_50 < sma_200) & strong_trend] = -1

        result_df = self._make_result_df(data)
        return self.apply_signals(result_df, signals)
