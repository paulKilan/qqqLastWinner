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

    def __init__(self, allow_short: bool = True):
        """
        Initialize the BaseStrategy.

        Args:
            allow_short (bool): If False, short signals will be converted to Cash (0.0).
        """
        self.data_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
        self.data_file = 'QQQ.csv'
        self._data = None
        self.allow_short = allow_short

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
        """
        try:
            if self._data is None:
                self._load_data()

            start_dt, end_dt = self._validate_and_parse_dates(startDate, endDate)
            filtered_data = self._filter_data_by_date_range(start_dt, end_dt)

            if filtered_data.empty:
                return self._create_error_dataframe(
                    start_dt, end_dt,
                    f"ERROR: No data available for date range {startDate} to {endDate}"
                )

            result_df = self._calculate_positions(filtered_data, contextData)

            if not self.allow_short:
                result_df['shortPositionPct'] = 0.0

            return result_df

        except Exception as e:
            return self._create_error_dataframe(
                datetime.strptime(startDate.replace('/', '-'), '%Y-%m-%d' if '-' in startDate else '%m-%d-%Y'),
                datetime.strptime(endDate.replace('/', '-'), '%Y-%m-%d' if '-' in endDate else '%m-%d-%Y'),
                f"ERROR: {str(e)}"
            )

    def _load_data(self) -> None:
        """Load data from CSV file."""
        file_path = os.path.join(self.data_path, self.data_file)

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Unable to read data from {file_path}")

        try:
            self._data = pd.read_csv(file_path)

            self._data['Date'] = pd.to_datetime(self._data['Date'], format='%m/%d/%Y', errors='coerce')
            if self._data['Date'].isna().any():
                self._data['Date'] = pd.to_datetime(self._data['Date'], errors='coerce')
            if self._data['Date'].isna().any():
                raise ValueError("Unable to parse dates in the data file")

            self._data.set_index('Date', inplace=True)
            self._data.sort_index(inplace=True)

            # Normalize column names
            if 'Price' in self._data.columns:
                self._data.rename(columns={'Price': 'close'}, inplace=True)
            if 'Open' in self._data.columns:
                self._data.rename(columns={'Open': 'open'}, inplace=True)
            if 'High' in self._data.columns:
                self._data.rename(columns={'High': 'high'}, inplace=True)
            if 'Low' in self._data.columns:
                self._data.rename(columns={'Low': 'low'}, inplace=True)

            # Ensure numeric columns (handle comma-separated numbers)
            for col in ['open', 'close', 'high', 'low']:
                if col in self._data.columns and self._data[col].dtype == 'object':
                    self._data[col] = pd.to_numeric(
                        self._data[col].astype(str).str.replace(',', ''), errors='coerce'
                    )

        except Exception as e:
            raise Exception(f"Unable to read data: {str(e)}")

    def _validate_and_parse_dates(self, startDate: str, endDate: str) -> tuple:
        """Validate and parse input dates, supporting YYYY-MM-DD and MM/DD/YYYY formats."""
        try:
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
        Filter data by date range. If exact dates don't exist, use nearest trading days.
        """
        if self._data is None:
            raise Exception("Data not loaded")

        available_dates = self._data.index

        if start_dt in available_dates:
            actual_start = start_dt
        else:
            future_dates = available_dates[available_dates >= start_dt]
            if len(future_dates) == 0:
                raise ValueError(f"No trading data available on or after {start_dt.strftime('%Y-%m-%d')}")
            actual_start = future_dates[0]
            print(f"Warning: Start date {start_dt.strftime('%Y-%m-%d')} is not a trading day. Using {actual_start.strftime('%Y-%m-%d')} instead.")

        if end_dt in available_dates:
            actual_end = end_dt
        else:
            past_dates = available_dates[available_dates <= end_dt]
            if len(past_dates) == 0:
                raise ValueError(f"No trading data available on or before {end_dt.strftime('%Y-%m-%d')}")
            actual_end = past_dates[-1]
            print(f"Warning: End date {end_dt.strftime('%Y-%m-%d')} is not a trading day. Using {actual_end.strftime('%Y-%m-%d')} instead.")

        mask = (self._data.index >= actual_start) & (self._data.index <= actual_end)
        return self._data.loc[mask].copy()

    def _calculate_positions(self, data: pd.DataFrame, contextData: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
        """
        Calculate position allocations. Override in derived classes.
        Base implementation returns all-zero positions (Cash).
        """
        return self._make_result_df(data)

    def _make_result_df(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Create the standard result DataFrame for _calculate_positions implementations.
        Replaces the boilerplate present in every concrete strategy.
        """
        result_df = pd.DataFrame(
            {'longPositionPct': 0.0, 'shortPositionPct': 0.0, 'error': None},
            index=data.index,
        )
        result_df.index.name = 'date'
        return result_df

    def _apply_regime_filter(self, data: pd.DataFrame, result_df: pd.DataFrame) -> pd.DataFrame:
        """
        Zero out longPositionPct on days where close is below SMA-200.
        Call this explicitly at the end of _calculate_positions() for strategies that want it.
        Note: The first 199 rows will suppress longs due to SMA warmup (NaN coerced to False).
        """
        sma_200 = data['close'].rolling(window=200).mean()
        is_bullish = (data['close'] > sma_200).fillna(False)
        result_df.loc[~is_bullish, 'longPositionPct'] = 0.0
        return result_df

    def apply_signals(self, result_df: pd.DataFrame, signals: pd.Series) -> pd.DataFrame:
        """
        Apply trading signals to the result DataFrame.

        Args:
            result_df (pd.DataFrame): The DataFrame to update
            signals (pd.Series): Series of signals:
                1  -> Long (100% long ETF)
                -1 -> Short (100% short ETF)
                0  -> Neutral (100% Cash)

        Returns:
            pd.DataFrame: Updated result_df
        """
        aligned_signals = signals.reindex(result_df.index).fillna(0)

        result_df.loc[aligned_signals == 1, 'longPositionPct'] = 1.0
        result_df.loc[aligned_signals == 1, 'shortPositionPct'] = 0.0
        result_df.loc[aligned_signals == -1, 'longPositionPct'] = 0.0
        result_df.loc[aligned_signals == -1, 'shortPositionPct'] = 1.0
        result_df.loc[aligned_signals == 0, 'longPositionPct'] = 0.0
        result_df.loc[aligned_signals == 0, 'shortPositionPct'] = 0.0

        return result_df

    def _create_error_dataframe(self, start_dt: datetime, end_dt: datetime, error_msg: str) -> pd.DataFrame:
        """Create an error DataFrame when data is not available."""
        error_df = pd.DataFrame({
            'date': [start_dt],
            'longPositionPct': [None],
            'shortPositionPct': [None],
            'error': [error_msg]
        })
        error_df.set_index('date', inplace=True)
        return error_df

    def get_available_date_range(self) -> tuple:
        """Get the available date range in the loaded data."""
        if self._data is None:
            self._load_data()
        return self._data.index.min(), self._data.index.max()

    def get_data_info(self) -> Dict[str, Any]:
        """Get information about the loaded data."""
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
