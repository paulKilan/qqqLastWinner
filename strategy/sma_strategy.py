"""
SMA50/250 Crossover Trading Strategy

This strategy implements a classic golden cross/death cross trading system:
- Golden Cross (SMA50 > SMA250): 100% TQQQ (3x leveraged QQQ)
- Death Cross (SMA50 < SMA250): 100% SQQQ (3x inverse QQQ)
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict, Any
from .base_strategy import BaseStrategy


class SMA50250Strategy(BaseStrategy):
    """
    SMA50/250 crossover trading strategy.
    
    Trading Rules:
    - When SMA50 crosses above SMA250 (Golden Cross): 100% TQQQ, 0% SQQQ
    - When SMA50 crosses below SMA250 (Death Cross): 0% TQQQ, 100% SQQQ
    
    Position Allocation:
    - longPositionPct: Percentage allocated to TQQQ (3x leveraged QQQ)
    - shortPositionPct: Percentage allocated to SQQQ (3x inverse QQQ)
    """
    
    def __init__(self):
        """Initialize the SMA50/250 crossover strategy."""
        super().__init__()
    
    def _calculate_positions(self, data: pd.DataFrame, contextData: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
        """
        Calculate position allocations based on SMA50/250 crossover signals.
        
        Args:
            data (pd.DataFrame): Filtered market data with SMA_50 and SMA_250 columns
            contextData (dict, optional): Additional context data (unused in this strategy)
            
        Returns:
            pd.DataFrame: DataFrame with TQQQ/SQQQ position allocations
        """
        # Create result DataFrame
        result_df = pd.DataFrame(index=data.index)
        result_df.index.name = 'date'
        
        # Initialize columns
        result_df['longPositionPct'] = 0.0    # TQQQ allocation
        result_df['shortPositionPct'] = 0.0   # SQQQ allocation
        result_df['error'] = None
        
        # Check for missing SMA data and calculate positions
        for idx, row in data.iterrows():
            sma_50 = row['SMA_50']
            sma_250 = row['SMA_250']
            
            # Handle missing SMA data
            if pd.isna(sma_50) or pd.isna(sma_250):
                result_df.loc[idx, 'longPositionPct'] = None
                result_df.loc[idx, 'shortPositionPct'] = None
                result_df.loc[idx, 'error'] = "missing historical data"
                continue
            
            # Apply SMA crossover logic
            if sma_50 > sma_250:
                # Golden Cross: SMA50 above SMA250 -> Bullish -> 100% TQQQ
                result_df.loc[idx, 'longPositionPct'] = 1.0   # 100% TQQQ
                result_df.loc[idx, 'shortPositionPct'] = 0.0  # 0% SQQQ
            else:
                # Death Cross: SMA50 below SMA250 -> Bearish -> 100% SQQQ  
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
        analysis_df['SMA_50'] = filtered_data['SMA_50']
        analysis_df['SMA_250'] = filtered_data['SMA_250']
        analysis_df['Price'] = filtered_data['Price']
        
        # Calculate crossover signals
        analysis_df['SMA50_above_SMA250'] = analysis_df['SMA_50'] > analysis_df['SMA_250']
        analysis_df['Signal_Change'] = analysis_df['SMA50_above_SMA250'].diff()
        
        # Mark crossover points
        analysis_df['Golden_Cross'] = analysis_df['Signal_Change'] == True   # False to True
        analysis_df['Death_Cross'] = analysis_df['Signal_Change'] == False   # True to False
        
        return analysis_df
