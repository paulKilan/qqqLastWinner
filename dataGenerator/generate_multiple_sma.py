"""
Generate multiple SMA configurations for easy switching.

This script generates SMA files for common configurations:
- 20/60 (fast response)
- 50/250 (classic)
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
    """Calculate Simple Moving Average for given window."""
    return prices.rolling(window=window, min_periods=window).mean()

def generate_sma_file(fast_period: int, slow_period: int):
    """Generate SMA file for specific periods."""
    
    # File paths
    input_file = project_root / "data" / "QQQ.csv"
    output_file = project_root / "data" / f"QQQ_with_SMAs_{fast_period}_{slow_period}.csv"
    
    print(f"\nGenerating SMA {fast_period}/{slow_period} file...")
    print(f"Input: {input_file}")
    print(f"Output: {output_file}")
    
    # Check if input file exists
    if not input_file.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")
    
    # Read the CSV file
    df = pd.read_csv(input_file)
    
    # Convert Date column to datetime and sort chronologically (oldest first)
    df['Date'] = pd.to_datetime(df['Date'], format='%m/%d/%Y')
    df = df.sort_values('Date').reset_index(drop=True)
    
    # Clean the Price column (handle any comma formatting)
    df['Price'] = pd.to_numeric(df['Price'].astype(str).str.replace(',', ''), errors='coerce')
    
    # Remove rows with NaN prices
    df = df.dropna(subset=['Price']).reset_index(drop=True)
    
    # Calculate SMAs
    df[f'SMA_{fast_period}'] = calculate_sma(df['Price'], fast_period)
    df[f'SMA_{slow_period}'] = calculate_sma(df['Price'], slow_period)
    
    # Sort back to newest first (to match original QQQ.csv format)
    df = df.sort_values('Date', ascending=False).reset_index(drop=True)
    
    # Format Date back to original format (MM/DD/YYYY)
    df['Date'] = df['Date'].dt.strftime('%m/%d/%Y')
    
    # Round SMA values to reasonable precision
    df[f'SMA_{fast_period}'] = df[f'SMA_{fast_period}'].round(5)
    df[f'SMA_{slow_period}'] = df[f'SMA_{slow_period}'].round(5)
    
    # Save to CSV
    df.to_csv(output_file, index=False)
    
    # Count valid SMA values
    fast_valid = df[f'SMA_{fast_period}'].notna().sum()
    slow_valid = df[f'SMA_{slow_period}'].notna().sum()
    
    print(f"Generated {len(df)} rows")
    print(f"SMA {fast_period}: {fast_valid} valid values")
    print(f"SMA {slow_period}: {slow_valid} valid values")
    print(f"Saved to: {output_file}")
    
    return output_file

def main():
    """Generate multiple SMA configurations."""
    
    print("Multiple SMA Configuration Generator")
    print("=" * 50)
    
    # Common SMA configurations
    configurations = [
        (20, 60),   # Fast response
        (50, 250),  # Classic
    ]
    
    generated_files = []
    
    for fast, slow in configurations:
        try:
            output_file = generate_sma_file(fast, slow)
            generated_files.append(output_file)
        except Exception as e:
            print(f"Error generating SMA {fast}/{slow}: {e}")
    
    print(f"\n{'='*50}")
    print("Generation Summary:")
    print(f"{'='*50}")
    
    for i, file_path in enumerate(generated_files, 1):
        print(f"{i}. {file_path.name}")
        print(f"   Path: {file_path}")
    
    print(f"\nGenerated {len(generated_files)} SMA configuration files!")
    print("\nTo use these files:")
    print("1. Edit strategy/sma_strategy.py")
    print("2. Change FAST_SMA_PERIOD and SLOW_SMA_PERIOD")
    print("3. The DATA_FILE will automatically switch to the correct file")
    print("4. Run your backtest!")

if __name__ == "__main__":
    main()
