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
        super().__init__(allow_short=True, use_regime_filter=True)
        self.data_file = 'QQQ.csv'

    def _calculate_positions(self, data: pd.DataFrame, contextData=None) -> pd.DataFrame:
        # Calculate ATR (Average True Range)
        # TR = Max(High - Low, Abs(High - PrevClose), Abs(Low - PrevClose))
        # Since we only have Open/Close in normalized data (unless BaseStrategy loads High/Low)
        # BaseStrategy loads raw data, so we might have High/Low if we check self._data columns.
        # But _calculate_positions receives 'data' which is filtered.
        # Let's check if 'High' and 'Low' are preserved in filtered data.
        
        # BaseStrategy._filter_data_by_date_range returns a copy of self._data.
        # self._data has all columns from CSV.
        # So 'High' and 'Low' should be available.
        # But we need to ensure they are numeric.
        
        # We need to handle potential string columns for High/Low if they weren't converted in BaseStrategy.
        # BaseStrategy only converted 'open' and 'close'.
        
        # Let's try to convert High/Low here just in case.
        for col in ['High', 'Low']:
            if col in data.columns and data[col].dtype == 'object':
                data[col] = pd.to_numeric(data[col].astype(str).str.replace(',', ''), errors='coerce')
        
        if 'High' not in data.columns or 'Low' not in data.columns:
             # Fallback if High/Low missing: use High=Close, Low=Close (ATR will be small, strategy might fail)
             data['High'] = data['close']
             data['Low'] = data['close']

        high = data['High']
        low = data['Low']
        close = data['close']
        prev_close = close.shift(1)
        
        tr1 = high - low
        tr2 = (high - prev_close).abs()
        tr3 = (low - prev_close).abs()
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        data['ATR'] = tr.rolling(window=14).mean()
        
        # Strategy:
        # Buy if Price > Close + k * ATR
        # Sell if Price < Close - k * ATR
        # Wait, this is usually "Breakout from open" or "Breakout from previous close".
        # Let's use: Buy if Close > Previous Close + 1 * ATR
        # Sell if Close < Previous Close - 1 * ATR
        
        k = 1.0
        upper_band = prev_close + (k * data['ATR'])
        lower_band = prev_close - (k * data['ATR'])
        
        # Create result DataFrame
        result_df = pd.DataFrame(index=data.index)
        result_df.index.name = 'date'
        
        # Initialize columns
        result_df['longPositionPct'] = 0.0
        result_df['shortPositionPct'] = 0.0
        result_df['error'] = None

        # Generate signals
        long_condition = data['close'] > upper_band
        short_condition = data['close'] < lower_band

        # Apply signals
        result_df.loc[long_condition, 'longPositionPct'] = 1.0
        result_df.loc[short_condition, 'shortPositionPct'] = 1.0
        
        result_df = result_df.reset_index()
        result_df.set_index('date', inplace=True)

        return result_df
