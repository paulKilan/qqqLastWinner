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
        super().__init__(allow_short=True) # Explicitly enable shorting
        self.data_file = 'QQQ.csv'

    def _calculate_positions(self, data: pd.DataFrame, contextData=None) -> pd.DataFrame:
        # Calculate SMAs
        data['SMA_50'] = data['close'].rolling(window=50).mean()
        data['SMA_200'] = data['close'].rolling(window=200).mean()
        
        # Calculate ADX (Average Directional Index) for Neutral filter
        # ADX requires High, Low, Close
        # BaseStrategy loads raw data so High/Low should be there, but let's ensure numeric
        for col in ['High', 'Low', 'close']:
             if col in data.columns and data[col].dtype == 'object':
                data[col] = pd.to_numeric(data[col].astype(str).str.replace(',', ''), errors='coerce')
        
        # Simple ADX calculation (14 period)
        high = data['High']
        low = data['Low']
        close = data['close']
        
        plus_dm = high.diff()
        minus_dm = low.diff()
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm > 0] = 0
        
        tr1 = pd.DataFrame(high - low)
        tr2 = pd.DataFrame(abs(high - close.shift(1)))
        tr3 = pd.DataFrame(abs(low - close.shift(1)))
        frames = [tr1, tr2, tr3]
        tr = pd.concat(frames, axis=1, join='outer').max(axis=1)
        atr = tr.rolling(14).mean()
        
        plus_di = 100 * (plus_dm.ewm(alpha=1/14).mean() / atr)
        minus_di = 100 * (abs(minus_dm).ewm(alpha=1/14).mean() / atr)
        dx = (abs(plus_di - minus_di) / abs(plus_di + minus_di)) * 100
        adx = dx.rolling(14).mean()
        
        data['ADX'] = adx

        # Initialize signals with 0 (Neutral)
        signals = pd.Series(0, index=data.index)
        
        # Define Conditions
        bullish = data['SMA_50'] > data['SMA_200']
        bearish = data['SMA_50'] < data['SMA_200']
        strong_trend = data['ADX'] > 20
        
        # Apply Logic
        # Long: Bullish AND Strong Trend
        signals[bullish & strong_trend] = 1
        
        # Short: Bearish AND Strong Trend
        signals[bearish & strong_trend] = -1
        
        # Neutral: Weak Trend (ADX <= 20) -> remains 0
        # Also Bullish/Bearish but Weak Trend -> remains 0
        
        # Create result DataFrame
        # Create result DataFrame
        # We'll just use the standard init
        result_df = pd.DataFrame(index=data.index)
        result_df.index.name = 'date'
        result_df['longPositionPct'] = 0.0
        result_df['shortPositionPct'] = 0.0
        result_df['error'] = None
        
        # Use new helper
        result_df = self.apply_signals(result_df, signals)
        
        result_df = result_df.reset_index()
        result_df.set_index('date', inplace=True)

        return result_df
