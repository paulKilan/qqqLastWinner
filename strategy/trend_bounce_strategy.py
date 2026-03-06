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
        self.data_file = 'QQQ.csv' # Use raw QQQ data and calculate indicators here
        print("Trend Bounce Strategy initialized")

    def _calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calculate technical indicators needed for the strategy."""
        df = data.copy()
        
        # Calculate EMAs
        # Note: The formula uses EMA of HIGH and LOW, not CLOSE
        df['short_bull'] = df['High'].ewm(span=25, adjust=False).mean() # 短线多
        df['short_bear'] = df['Low'].ewm(span=25, adjust=False).mean()  # 短线空
        df['long_bull'] = df['High'].ewm(span=90, adjust=False).mean()  # 长线多
        df['long_bear'] = df['Low'].ewm(span=90, adjust=False).mean()   # 长线空
        
        return df

    def _calculate_positions(self, data: pd.DataFrame, contextData: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
        """
        Calculate position allocations.
        """
        # Calculate indicators on the FULL dataset to avoid warmup bias
        # We use self._data which is loaded in BaseStrategy
        if self._data is None:
             self._load_data()
             
        full_df_with_indicators = self._calculate_indicators(self._data)
        
        # Now slice to the requested date range (matching 'data' index)
        # We use reindex to ensure we have exactly the rows requested, 
        # but since 'data' is a subset of 'self._data', simple loc slicing works too if indices match.
        # Ideally, 'data' passed here is exactly what we want to trade on.
        
        # Filter to match the index of the passed 'data' DataFrame
        df = full_df_with_indicators.loc[data.index].copy()
        
        # Create result DataFrame
        result_df = pd.DataFrame(index=df.index)
        result_df.index.name = 'date'
        result_df['longPositionPct'] = 0.0
        result_df['shortPositionPct'] = 0.0
        result_df['error'] = None
        
        # Pre-calculate conditions for speed
        # C > 短线多
        c_gt_short_bull = df['close'] > df['short_bull']
        # C < 长线多
        c_lt_long_bull = df['close'] < df['long_bull']
        
        # Rolling counts for "COUNT(..., 5) > 0"
        # We need to check if condition happened in LAST 5 days (including today? Formula usually implies window)
        # COUNT(X, 5) means sum of X over last 5 periods.
        
        # COUNT(C>短线多,5)>0
        count_c_gt_short_bull = c_gt_short_bull.rolling(window=5).sum() > 0
        
        # COUNT(C<长线多,5)>0
        count_c_lt_long_bull = c_lt_long_bull.rolling(window=5).sum() > 0
        
        # Shifted values for REF(..., 1)
        prev_close = df['close'].shift(1)
        prev_short_bull = df['short_bull'].shift(1)
        prev_short_bear = df['short_bear'].shift(1)
        
        # Bull Signal (多)
        # REF(C,1)<REF(短线多,1) AND C>短线多 AND C>REF(C,1) AND COUNT(C<长线多,5)>0
        bull_signal = (
            (prev_close < prev_short_bull) & 
            (df['close'] > df['short_bull']) & 
            (df['close'] > prev_close) & 
            count_c_lt_long_bull
        )
        
        # Bear Signal (空)
        # REF(C,1)>REF(短线空,1) AND C<短线空 AND C<REF(C,1) AND COUNT(C>短线多,5)>0
        bear_signal = (
            (prev_close > prev_short_bear) & 
            (df['close'] < df['short_bear']) & 
            (df['close'] < prev_close) & 
            count_c_gt_short_bull
        )
        
        # Iterate to set positions based on signals
        # We maintain position until signal changes
        current_pos = 0 # 0: None, 1: Long, -1: Short
        
        for i in range(len(df)):
            idx = df.index[i]
            
            if bull_signal.iloc[i]:
                current_pos = 1
            elif bear_signal.iloc[i]:
                current_pos = -1
            
            if current_pos == 1:
                result_df.loc[idx, 'longPositionPct'] = 1.0
                result_df.loc[idx, 'shortPositionPct'] = 0.0
            elif current_pos == -1:
                result_df.loc[idx, 'longPositionPct'] = 0.0
                result_df.loc[idx, 'shortPositionPct'] = 1.0
            else:
                # Default to cash or previous state? 
                # Strategy usually implies holding until switch. 
                # If we start with 0, we stay 0 until first signal.
                pass

        # Reset index to make date a column, then set it back as index
        result_df = result_df.reset_index()
        result_df.set_index('date', inplace=True)
        
        return result_df
