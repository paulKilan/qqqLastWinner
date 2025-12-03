"""
SMA Generator Script

This script reads QQQ.csv and generates Simple Moving Averages (SMA) for 20 and 60 periods.
The output will be saved as QQQ_with_SMA_20_60.csv for review before manual conversion.

Usage:
    python dataGenerator/generate_sma.py
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys
import os

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

def calculate_sma(prices: pd.Series, window: int) -> pd.Series:
    """
    Calculate Simple Moving Average for given window.
    
    Args:
        prices: Series of price data
        window: Number of periods for SMA calculation
        
    Returns:
        Series with SMA values (NaN for insufficient data points)
    """
    return prices.rolling(window=window, min_periods=window).mean()

def generate_sma_data():
    """
    Main function to generate SMA data from QQQ.csv
    """
    # File paths
    input_file = project_root / "data" / "QQQ.csv"
    output_file = project_root / "data" / "QQQ_with_SMA_20_60.csv"
    
    print("SMA Generator Starting...")
    print(f"Input file: {input_file}")
    print(f"Output file: {output_file}")
    
    # Check if input file exists
    if not input_file.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")
    
    # Read the CSV file
    print("\nReading QQQ.csv...")
    df = pd.read_csv(input_file)
    
    # Display basic info
    print(f"Loaded {len(df)} rows of data")
    print(f"Date range: {df['Date'].iloc[-1]} to {df['Date'].iloc[0]}")  # Note: data is newest first
    print(f"Columns: {list(df.columns)}")
    
    # Convert Date column to datetime and sort chronologically (oldest first)
    df['Date'] = pd.to_datetime(df['Date'], format='%m/%d/%Y')
    df = df.sort_values('Date').reset_index(drop=True)
    
    print(f"After sorting - Date range: {df['Date'].iloc[0]} to {df['Date'].iloc[-1]}")
    
    # Clean the Price column (handle any comma formatting)
    df['Price'] = pd.to_numeric(df['Price'].astype(str).str.replace(',', ''), errors='coerce')
    
    # Check for any NaN values in Price
    nan_count = df['Price'].isna().sum()
    if nan_count > 0:
        print(f"Warning: Found {nan_count} NaN values in Price column")
        # Remove rows with NaN prices
        df = df.dropna(subset=['Price']).reset_index(drop=True)
        print(f"Cleaned data: {len(df)} rows remaining")
    
    # Calculate SMAs
    print("\nCalculating SMAs...")
    print("   - SMA 20 (20-day Simple Moving Average)")
    print("   - SMA 60 (60-day Simple Moving Average)")
    
    df['SMA_20'] = calculate_sma(df['Price'], 20)
    df['SMA_60'] = calculate_sma(df['Price'], 60)
    
    # Count valid SMA values
    sma_20_valid = df['SMA_20'].notna().sum()
    sma_60_valid = df['SMA_60'].notna().sum()
    
    print(f"SMA 20: {sma_20_valid} valid values (first 19 rows will be NaN)")
    print(f"SMA 60: {sma_60_valid} valid values (first 59 rows will be NaN)")
    
    # Sort back to newest first (to match original QQQ.csv format)
    df = df.sort_values('Date', ascending=False).reset_index(drop=True)
    
    # Format Date back to original format (MM/DD/YYYY)
    df['Date'] = df['Date'].dt.strftime('%m/%d/%Y')
    
    # Round SMA values to reasonable precision
    df['SMA_20'] = df['SMA_20'].round(5)
    df['SMA_60'] = df['SMA_60'].round(5)
    
    # Create output directory if it doesn't exist
    output_file.parent.mkdir(exist_ok=True)
    
    # Save to CSV
    print(f"\nSaving to {output_file}...")
    df.to_csv(output_file, index=False)
    
    # Display sample of results
    print("\nSample of generated data (first 10 rows):")
    print("=" * 80)
    sample_cols = ['Date', 'Price', 'SMA_20', 'SMA_60']
    print(df[sample_cols].head(10).to_string(index=False))
    
    print("\nSample with valid SMA data (around row 60):")
    print("=" * 80)
    # Find first row where both SMAs are valid
    valid_sma_idx = df[df['SMA_60'].notna()].index[0] if df['SMA_60'].notna().any() else 60
    sample_start = max(0, valid_sma_idx - 2)
    sample_end = min(len(df), valid_sma_idx + 8)
    print(df[sample_cols].iloc[sample_start:sample_end].to_string(index=False))
    
    # Summary statistics
    print(f"\nSummary Statistics:")
    print("=" * 50)
    print(f"Total rows: {len(df)}")
    print(f"Price range: ${df['Price'].min():.2f} - ${df['Price'].max():.2f}")
    print(f"SMA 20 range: ${df['SMA_20'].min():.2f} - ${df['SMA_20'].max():.2f}")
    print(f"SMA 60 range: ${df['SMA_60'].min():.2f} - ${df['SMA_60'].max():.2f}")
    print(f"SMA 20 valid values: {sma_20_valid}/{len(df)} ({sma_20_valid/len(df)*100:.1f}%)")
    print(f"SMA 60 valid values: {sma_60_valid}/{len(df)} ({sma_60_valid/len(df)*100:.1f}%)")
    
    print(f"\nSMA generation complete!")
    print(f"Output saved to: {output_file}")
    print("\nPlease review the generated file before manually converting to QQQ_with_SMAs.csv")
    
    return output_file

def main():
    """Main entry point"""
    try:
        output_file = generate_sma_data()
        print(f"\nSuccess! Generated SMA data saved to:")
        print(f"   {output_file}")
        
    except Exception as e:
        print(f"\nError: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
