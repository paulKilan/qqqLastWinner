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
        super().__init__(allow_short=True, use_regime_filter=True)
        self.data_file = 'QQQ.csv'

    def _calculate_positions(self, data: pd.DataFrame, contextData=None) -> pd.DataFrame:
        # Calculate Stochastic Oscillator
        # %K = (Current Close - Lowest Low) / (Highest High - Lowest Low) * 100
        # %D = 3-day SMA of %K
        
        window = 14
        data['L14'] = data['close'].rolling(window=window).min()
        data['H14'] = data['close'].rolling(window=window).max()
        
        data['%K'] = 100 * ((data['close'] - data['L14']) / (data['H14'] - data['L14']))
        data['%D'] = data['%K'].rolling(window=3).mean()

        # Create result DataFrame
        result_df = pd.DataFrame(index=data.index)
        result_df.index.name = 'date'
        
        # Initialize columns
        result_df['longPositionPct'] = 0.0
        result_df['shortPositionPct'] = 0.0
        result_df['error'] = None

        # Generate signals
        # Oversold (<20) and %K crosses above %D -> Buy
        # Overbought (>80) and %K crosses below %D -> Sell
        
        # We use simple thresholds for simplicity as requested "avoid complicated position"
        # Buy when %K < 20
        # Sell when %K > 80
        
        long_condition = data['%K'] < 20
        short_condition = data['%K'] > 80

        # Apply signals
        result_df.loc[long_condition, 'longPositionPct'] = 1.0
        result_df.loc[short_condition, 'shortPositionPct'] = 1.0
        
        result_df = result_df.reset_index()
        result_df.set_index('date', inplace=True)

        return result_df
