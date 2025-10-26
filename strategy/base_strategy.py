"""
BaseStrategy class for QQQ trading strategies.

This strategy reads data from the data folder and provides a foundation
for implementing specific trading strategies.
"""

import pandas as pd
import os
from datetime import datetime
from typing import Optional, Dict, Any
import warnings


class BaseStrategy:
    """
    Base strategy class that reads QQQ data and provides extensible framework
    for implementing specific trading strategies.
    
    This strategy assumes data is always available. If data is missing,
    the output will clearly mention it with "ERROR".
    """
    
    def __init__(self):
        """Initialize the BaseStrategy with default data path."""
        self.data_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
        self.data_file = 'QQQ_with_SMAs.csv'
        self._data = None
        
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
            filtered_data = self._filter_data_by_date_range(start_dt, end_dt)
            
            if filtered_data.empty:
                # Return error DataFrame if no data in range
                return self._create_error_dataframe(
                    start_dt, end_dt, 
                    f"ERROR: No data available for date range {startDate} to {endDate}"
                )
            
            # Calculate positions (to be overridden by derived classes)
            result_df = self._calculate_positions(filtered_data, contextData)
            
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
