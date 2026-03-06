"""
BaseStrategy class for QQQ trading strategies.

This strategy reads data from the data folder and provides a foundation
for implementing specific trading strategies.
"""

import pandas as pd
import os
from datetime import datetime
from typing import Optional, Dict, Any


class BaseStrategy:
    """
    Base strategy class that reads QQQ data and provides extensible framework
    for implementing specific trading strategies.
    
    This strategy assumes data is always available. If data is missing,
    the output will clearly mention it with "ERROR".
    """
    
    def __init__(self, allow_short: bool = True, use_regime_filter: bool = False):
        """
        Initialize the BaseStrategy.
        
        Args:
            allow_short (bool): If False, short signals will be converted to Cash (0.0).
            use_regime_filter (bool): If True, only allow Long trades when Price > SMA 200.
        """
        self.data_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
        self.data_file = 'QQQ_with_SMAs.csv'  # Default file, can be overridden by derived classes
        self._data = None
        self.allow_short = allow_short
        self.use_regime_filter = use_regime_filter
        
    def execute(self, startDate: str, endDate: str, contextData: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
        """
        Execute the strategy for the given date range.
        
        Args:
            startDate (str): Inclusive start date in format 'YYYY-MM-DD' or 'MM/DD/YYYY'
                           Must exist in the QQQ CSV data
            endDate (str): Inclusive end date in format 'YYYY-MM-DD' or 'MM/DD/YYYY'
            contextData (dict, optional): Free-form JSON for other strategies that need 
                                        additional input parameters
        
        Returns:
            pd.DataFrame: DataFrame with columns:
                - date (index): Trading date
                - longPositionPct: Percentage for long position (to be implemented by derived classes)
                - shortPositionPct: Percentage for short position (to be implemented by derived classes)  
                - error: Error message if positions can't be derived
        
        Example:
            >>> strategy = BaseStrategy()
            >>> result = strategy.execute("2022-01-01", "2022-01-10")
            >>> print(result)
        """
        try:
            # Load data if not already loaded
            if self._data is None:
                self._load_data()
            
            # Validate and parse dates
            start_dt, end_dt = self._validate_and_parse_dates(startDate, endDate)
            
            # Filter data for the date range
            # Note: We need enough history for indicators (like SMA 200) even if start_date is recent.
            # However, _filter_data_by_date_range cuts the data.
            # The derived classes usually calculate indicators on the filtered data, which is a problem for early dates.
            # But for now, we assume the user provides a start_date that allows for warmup if they handle it,
            # OR we calculate indicators on the full dataset before filtering.
            # BaseStrategy structure calls _calculate_positions on filtered data.
            # To support regime filter (SMA 200), we need 200 days prior.
            
            # For this implementation, we will calculate regime filter on the filtered data
            # which means the first 200 days of the backtest might have no regime filter value (NaN).
            
            filtered_data = self._filter_data_by_date_range(start_dt, end_dt)
            
            if filtered_data.empty:
                # Return error DataFrame if no data in range
                return self._create_error_dataframe(
                    start_dt, end_dt, 
                    f"ERROR: No data available for date range {startDate} to {endDate}"
                )
            
            # Calculate positions (to be overridden by derived classes)
            result_df = self._calculate_positions(filtered_data, contextData)
            
            # --- Apply Improvements ---
            
            # 1. Regime Filter (SMA 200)
            if self.use_regime_filter:
                # Calculate SMA 200 on the close price
                # Note: This is calculated on the 'filtered_data' passed to _calculate_positions.
                # If the strategy calculated indicators, they are in result_df? No, result_df is just positions.
                # We need to calculate SMA 200 on filtered_data.
                sma_200 = filtered_data['close'].rolling(window=200).mean()
                
                # Condition: Price > SMA 200 -> Bullish Regime
                is_bullish = filtered_data['close'] > sma_200
                
                # Apply filter: If NOT bullish, force Long to 0.0
                # We align indices just in case
                result_df.loc[~is_bullish, 'longPositionPct'] = 0.0
                
                # Optional: Could also force Short to 0.0 if we only want to short in downtrends?
                # Usually regime filter is "Long only in uptrend".
            
            # 2. Long-Only Mode
            if not self.allow_short:
                result_df['shortPositionPct'] = 0.0
            
            return result_df
            
        except Exception as e:
            # Return error DataFrame for any unexpected errors
            return self._create_error_dataframe(
                datetime.strptime(startDate.replace('/', '-'), '%Y-%m-%d' if '-' in startDate else '%m-%d-%Y'),
                datetime.strptime(endDate.replace('/', '-'), '%Y-%m-%d' if '-' in endDate else '%m-%d-%Y'),
                f"ERROR: {str(e)}"
            )
    
    def _load_data(self) -> None:
        """Load QQQ data from CSV file."""
        file_path = os.path.join(self.data_path, self.data_file)
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Unable to read QQQ data from {file_path}")
        
        try:
            # Load the CSV data
            self._data = pd.read_csv(file_path)
            
            # Parse the Date column - handle both MM/DD/YYYY and YYYY-MM-DD formats
            self._data['Date'] = pd.to_datetime(self._data['Date'], format='%m/%d/%Y', errors='coerce')
            
            # If parsing failed, try alternative format
            if self._data['Date'].isna().any():
                self._data['Date'] = pd.to_datetime(self._data['Date'], errors='coerce')
            
            # Check if we still have NaT values
            if self._data['Date'].isna().any():
                raise ValueError("Unable to parse dates in the data file")
            
            # Set Date as index and sort
            self._data.set_index('Date', inplace=True)
            self._data.sort_index(inplace=True)

            # Normalize columns: 'Price' -> 'close', 'Open' -> 'open'
            if 'Price' in self._data.columns:
                self._data.rename(columns={'Price': 'close'}, inplace=True)
            if 'Open' in self._data.columns:
                self._data.rename(columns={'Open': 'open'}, inplace=True)
            
            # Ensure open and close are numeric (handle commas if present)
            for col in ['open', 'close']:
                if col in self._data.columns and self._data[col].dtype == 'object':
                    self._data[col] = pd.to_numeric(self._data[col].astype(str).str.replace(',', ''), errors='coerce')
            
        except Exception as e:
            raise Exception(f"Unable to read QQQ data: {str(e)}")
    
    def _validate_and_parse_dates(self, startDate: str, endDate: str) -> tuple:
        """
        Validate and parse input dates.
        
        Args:
            startDate (str): Start date string
            endDate (str): End date string
            
        Returns:
            tuple: (start_datetime, end_datetime)
        """
        try:
            # Try to parse dates - support both YYYY-MM-DD and MM/DD/YYYY formats
            if '/' in startDate:
                start_dt = datetime.strptime(startDate, '%m/%d/%Y')
                end_dt = datetime.strptime(endDate, '%m/%d/%Y')
            else:
                start_dt = datetime.strptime(startDate, '%Y-%m-%d')
                end_dt = datetime.strptime(endDate, '%Y-%m-%d')
            
            if start_dt > end_dt:
                raise ValueError("Start date must be before or equal to end date")
            
            return start_dt, end_dt
            
        except ValueError as e:
            raise ValueError(f"Invalid date format. Use 'YYYY-MM-DD' or 'MM/DD/YYYY': {str(e)}")
    
    def _filter_data_by_date_range(self, start_dt: datetime, end_dt: datetime) -> pd.DataFrame:
        """
        Filter data by date range and validate availability.
        If exact dates don't exist, find the nearest trading days.
        
        Args:
            start_dt (datetime): Start date
            end_dt (datetime): End date
            
        Returns:
            pd.DataFrame: Filtered data for the date range
        """
        if self._data is None:
            raise Exception("Data not loaded")
        
        # Find the nearest trading days if exact dates don't exist
        available_dates = self._data.index
        
        # For start date: find the first trading day >= start_dt
        if start_dt in available_dates:
            actual_start = start_dt
        else:
            # Find first trading day on or after start_dt
            future_dates = available_dates[available_dates >= start_dt]
            if len(future_dates) == 0:
                raise ValueError(f"No trading data available on or after {start_dt.strftime('%Y-%m-%d')}")
            actual_start = future_dates[0]
            print(f"Warning: Start date {start_dt.strftime('%Y-%m-%d')} is not a trading day. Using {actual_start.strftime('%Y-%m-%d')} instead.")
        
        # For end date: find the last trading day <= end_dt
        if end_dt in available_dates:
            actual_end = end_dt
        else:
            # Find last trading day on or before end_dt
            past_dates = available_dates[available_dates <= end_dt]
            if len(past_dates) == 0:
                raise ValueError(f"No trading data available on or before {end_dt.strftime('%Y-%m-%d')}")
            actual_end = past_dates[-1]
            print(f"Warning: End date {end_dt.strftime('%Y-%m-%d')} is not a trading day. Using {actual_end.strftime('%Y-%m-%d')} instead.")
        
        # Filter data for the date range (inclusive)
        mask = (self._data.index >= actual_start) & (self._data.index <= actual_end)
        filtered_data = self._data.loc[mask].copy()
        
        return filtered_data
    
    def _calculate_positions(self, data: pd.DataFrame, contextData: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
        """
        Calculate position allocations. This is the method that derived classes should override.
        
        The base implementation returns None for positions, indicating that derived classes
        must implement the actual position calculation logic.
        
        Args:
            data (pd.DataFrame): Filtered market data for the date range
            contextData (dict, optional): Additional context data
            
        Returns:
            pd.DataFrame: DataFrame with position allocations
        """
        # Create result DataFrame with the required structure
        result_df = pd.DataFrame(index=data.index)
        result_df.index.name = 'date'
        
        # Base implementation returns None - derived classes should override this
        result_df['longPositionPct'] = None
        result_df['shortPositionPct'] = None
        result_df['error'] = None
        
        # Reset index to make date a column, then set it back as index
        result_df = result_df.reset_index()
        result_df.set_index('date', inplace=True)
        
        return result_df
    
    def apply_signals(self, result_df: pd.DataFrame, signals: pd.Series) -> pd.DataFrame:
        """
        Apply trading signals to the result DataFrame.
        
        Args:
            result_df (pd.DataFrame): The DataFrame to update (must have 'longPositionPct' and 'shortPositionPct')
            signals (pd.Series): Series of signals:
                1  -> Long (100% TQQQ)
                -1 -> Short (100% SQQQ)
                0  -> Neutral (100% Cash)
                
        Returns:
            pd.DataFrame: Updated result_df
        """
        # Ensure signals align with result_df
        aligned_signals = signals.reindex(result_df.index).fillna(0)
        
        # Long: Signal == 1
        result_df.loc[aligned_signals == 1, 'longPositionPct'] = 1.0
        result_df.loc[aligned_signals == 1, 'shortPositionPct'] = 0.0
        
        # Short: Signal == -1
        result_df.loc[aligned_signals == -1, 'longPositionPct'] = 0.0
        result_df.loc[aligned_signals == -1, 'shortPositionPct'] = 1.0
        
        # Neutral: Signal == 0
        result_df.loc[aligned_signals == 0, 'longPositionPct'] = 0.0
        result_df.loc[aligned_signals == 0, 'shortPositionPct'] = 0.0
        
        return result_df
    
    def _create_error_dataframe(self, start_dt: datetime, end_dt: datetime, error_msg: str) -> pd.DataFrame:
        """
        Create an error DataFrame when data is not available.
        
        Args:
            start_dt (datetime): Start date
            end_dt (datetime): End date  
            error_msg (str): Error message
            
        Returns:
            pd.DataFrame: Error DataFrame
        """
        # Create a single row with the error
        error_df = pd.DataFrame({
            'date': [start_dt],
            'longPositionPct': [None],
            'shortPositionPct': [None], 
            'error': [error_msg]
        })
        error_df.set_index('date', inplace=True)
        
        return error_df
    
    def get_available_date_range(self) -> tuple:
        """
        Get the available date range in the loaded data.
        
        Returns:
            tuple: (start_date, end_date) as datetime objects
        """
        if self._data is None:
            self._load_data()
        
        return self._data.index.min(), self._data.index.max()
    
    def get_data_info(self) -> Dict[str, Any]:
        """
        Get information about the loaded data.
        
        Returns:
            dict: Information about the data including columns, date range, and row count
        """
        if self._data is None:
            self._load_data()
        
        start_date, end_date = self.get_available_date_range()
        
        return {
            'columns': list(self._data.columns),
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d'),
            'total_rows': len(self._data),
            'data_file': self.data_file
        }
