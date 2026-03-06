'''
Backtest Results:
- Start Date: 2013-01-02
- End Date: 2024-12-31
- Initial Capital: $10,000.00
- Final Equity: $1,414.31
- Total Trades: 45
- Return: -85.86%
'''
"""
SMA Crossover Trading Strategy

This strategy implements a configurable golden cross/death cross trading system:
- Golden Cross (Fast SMA > Slow SMA): 100% TQQQ (3x leveraged QQQ)
- Death Cross (Fast SMA < Slow SMA): 100% SQQQ (3x inverse QQQ)
"""

import pandas as pd
from typing import Optional, Dict, Any
from .base_strategy import BaseStrategy

# =============================================================================
# CONFIGURATION - Change these values to switch SMA periods
# =============================================================================
FAST_SMA_PERIOD = 20    # Fast SMA period (e.g., 20, 50)
SLOW_SMA_PERIOD = 60    # Slow SMA period (e.g., 60, 250)

# Expected column names in the data (update if your CSV has different names)
FAST_SMA_COLUMN = f'SMA_{FAST_SMA_PERIOD}'  # e.g., 'SMA_50' or 'SMA_20'
SLOW_SMA_COLUMN = f'SMA_{SLOW_SMA_PERIOD}'  # e.g., 'SMA_250' or 'SMA_60'

# Data file configuration (automatically switches based on SMA periods)
DATA_FILE = f'QQQ_with_SMAs_{FAST_SMA_PERIOD}_{SLOW_SMA_PERIOD}.csv'  # e.g., 'QQQ_with_SMAs_20_60.csv'
# =============================================================================


class SMAStrategy(BaseStrategy):
    """
    Configurable SMA crossover trading strategy.
    
    Trading Rules:
    - When Fast SMA crosses above Slow SMA (Golden Cross): 100% TQQQ, 0% SQQQ
    - When Fast SMA crosses below Slow SMA (Death Cross): 0% TQQQ, 100% SQQQ
    
    Position Allocation:
    - longPositionPct: Percentage allocated to TQQQ (3x leveraged QQQ)
    - shortPositionPct: Percentage allocated to SQQQ (3x inverse QQQ)
    
    Current Configuration:
    - Fast SMA: {FAST_SMA_PERIOD} periods
    - Slow SMA: {SLOW_SMA_PERIOD} periods
    """
    
    def __init__(self):
        """Initialize the SMA crossover strategy."""
        super().__init__()
        self.fast_sma_period = FAST_SMA_PERIOD
        self.slow_sma_period = SLOW_SMA_PERIOD
        self.fast_sma_column = FAST_SMA_COLUMN
        self.slow_sma_column = SLOW_SMA_COLUMN
        
        # Override the data file from base strategy
        self.data_file = DATA_FILE
        
        print(f"SMA Strategy initialized with {self.fast_sma_period}/{self.slow_sma_period} crossover")
        print(f"Using data file: {self.data_file}")
    
    def _calculate_positions(self, data: pd.DataFrame, contextData: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
        """
        Calculate position allocations based on configurable SMA crossover signals.
        
        Args:
            data (pd.DataFrame): Filtered market data with SMA columns
            contextData (dict, optional): Additional context data (unused in this strategy)
            
        Returns:
            pd.DataFrame: DataFrame with TQQQ/SQQQ position allocations
        """
        # Validate that required SMA columns exist
        if self.fast_sma_column not in data.columns:
            raise ValueError(f"Required column '{self.fast_sma_column}' not found in data. Available columns: {list(data.columns)}")
        if self.slow_sma_column not in data.columns:
            raise ValueError(f"Required column '{self.slow_sma_column}' not found in data. Available columns: {list(data.columns)}")
        
        # Create result DataFrame
        result_df = pd.DataFrame(index=data.index)
        result_df.index.name = 'date'
        
        # Initialize columns
        result_df['longPositionPct'] = 0.0    # TQQQ allocation
        result_df['shortPositionPct'] = 0.0   # SQQQ allocation
        result_df['error'] = None
        
        # Check for missing SMA data and calculate positions
        for idx, row in data.iterrows():
            fast_sma = row[self.fast_sma_column]
            slow_sma = row[self.slow_sma_column]
            
            # Handle missing SMA data
            if pd.isna(fast_sma) or pd.isna(slow_sma):
                result_df.loc[idx, 'longPositionPct'] = None
                result_df.loc[idx, 'shortPositionPct'] = None
                result_df.loc[idx, 'error'] = "missing historical data"
                continue
            
            # Apply SMA crossover logic
            if fast_sma > slow_sma:
                # Golden Cross: Fast SMA above Slow SMA -> Bullish -> 100% TQQQ
                result_df.loc[idx, 'longPositionPct'] = 1.0   # 100% TQQQ
                result_df.loc[idx, 'shortPositionPct'] = 0.0  # 0% SQQQ
            else:
                # Death Cross: Fast SMA below Slow SMA -> Bearish -> 100% SQQQ  
                result_df.loc[idx, 'longPositionPct'] = 0.0   # 0% TQQQ
                result_df.loc[idx, 'shortPositionPct'] = 1.0  # 100% SQQQ
        
        # Reset index to make date a column, then set it back as index
        result_df = result_df.reset_index()
        result_df.set_index('date', inplace=True)
        
        return result_df
    
    def get_crossover_signals(self, startDate: str, endDate: str) -> pd.DataFrame:
        """
        Get crossover signals for analysis.
        
        Args:
            startDate (str): Start date for analysis
            endDate (str): End date for analysis
            
        Returns:
            pd.DataFrame: DataFrame with crossover signals and SMA values
        """
        # Load data if not already loaded
        if self._data is None:
            self._load_data()
        
        # Validate and parse dates
        start_dt, end_dt = self._validate_and_parse_dates(startDate, endDate)
        
        # Filter data for the date range
        filtered_data = self._filter_data_by_date_range(start_dt, end_dt)
        
        if filtered_data.empty:
            return pd.DataFrame()
        
        # Create analysis DataFrame
        analysis_df = pd.DataFrame(index=filtered_data.index)
        analysis_df[f'SMA_{self.fast_sma_period}'] = filtered_data[self.fast_sma_column]
        analysis_df[f'SMA_{self.slow_sma_period}'] = filtered_data[self.slow_sma_column]
        analysis_df['Price'] = filtered_data['Price']
        
        # Calculate crossover signals
        analysis_df[f'SMA{self.fast_sma_period}_above_SMA{self.slow_sma_period}'] = (
            analysis_df[f'SMA_{self.fast_sma_period}'] > analysis_df[f'SMA_{self.slow_sma_period}']
        )
        analysis_df['Signal_Change'] = analysis_df[f'SMA{self.fast_sma_period}_above_SMA{self.slow_sma_period}'].diff()
        
        # Mark crossover points
        analysis_df['Golden_Cross'] = analysis_df['Signal_Change'] == True   # False to True
        analysis_df['Death_Cross'] = analysis_df['Signal_Change'] == False   # True to False
        
        return analysis_df
