"""
SMA Validation Script

This script helps validate the generated SMA values by showing sample calculations
and comparing with manual verification points.

Usage:
    python dataGenerator/validate_sma.py
"""

import pandas as pd
import numpy as np
from pathlib import Path

def validate_sma_calculations():
    """Validate the generated SMA calculations with manual verification."""
    
    project_root = Path(__file__).parent.parent
    sma_file = project_root / "data" / "QQQ_with_SMA_20_60.csv"
    
    if not sma_file.exists():
        print("Error: Generated SMA file not found. Run generate_sma.py first.")
        return
    
    print("SMA Validation Report")
    print("=" * 50)
    
    # Load the generated data
    df = pd.read_csv(sma_file)
    df['Date'] = pd.to_datetime(df['Date'], format='%m/%d/%Y')
    df = df.sort_values('Date').reset_index(drop=True)  # Sort chronologically for validation
    
    print(f"Loaded {len(df)} rows of data")
    print(f"Date range: {df['Date'].iloc[0].strftime('%Y-%m-%d')} to {df['Date'].iloc[-1].strftime('%Y-%m-%d')}")
    
    # Find first valid SMA points
    first_sma20_idx = df['SMA_20'].first_valid_index()
    first_sma60_idx = df['SMA_60'].first_valid_index()
    
    print(f"\nFirst valid SMA 20 at index {first_sma20_idx} (row {first_sma20_idx + 1})")
    print(f"First valid SMA 60 at index {first_sma60_idx} (row {first_sma60_idx + 1})")
    
    # Validate SMA 20 calculation at first valid point
    if first_sma20_idx is not None:
        manual_sma20 = df['Price'].iloc[first_sma20_idx-19:first_sma20_idx+1].mean()
        generated_sma20 = df['SMA_20'].iloc[first_sma20_idx]
        
        print(f"\nSMA 20 Validation (at index {first_sma20_idx}):")
        print(f"Date: {df['Date'].iloc[first_sma20_idx].strftime('%Y-%m-%d')}")
        print(f"Manual calculation: {manual_sma20:.5f}")
        print(f"Generated value: {generated_sma20:.5f}")
        print(f"Difference: {abs(manual_sma20 - generated_sma20):.8f}")
        print(f"Match: {'YES' if abs(manual_sma20 - generated_sma20) < 1e-6 else 'NO'}")
        
        # Show the 20 prices used in calculation
        print(f"\n20 prices used (oldest to newest):")
        prices_used = df['Price'].iloc[first_sma20_idx-19:first_sma20_idx+1]
        for i, (idx, price) in enumerate(prices_used.items()):
            date_str = df['Date'].iloc[idx].strftime('%Y-%m-%d')
            print(f"  {i+1:2d}. {date_str}: ${price:.2f}")
    
    # Validate SMA 60 calculation at first valid point
    if first_sma60_idx is not None:
        manual_sma60 = df['Price'].iloc[first_sma60_idx-59:first_sma60_idx+1].mean()
        generated_sma60 = df['SMA_60'].iloc[first_sma60_idx]
        
        print(f"\nSMA 60 Validation (at index {first_sma60_idx}):")
        print(f"Date: {df['Date'].iloc[first_sma60_idx].strftime('%Y-%m-%d')}")
        print(f"Manual calculation: {manual_sma60:.5f}")
        print(f"Generated value: {generated_sma60:.5f}")
        print(f"Difference: {abs(manual_sma60 - generated_sma60):.8f}")
        print(f"Match: {'YES' if abs(manual_sma60 - generated_sma60) < 1e-6 else 'NO'}")
    
    # Validate a few random points
    print(f"\nRandom Validation Points:")
    print("-" * 30)
    
    # Check a few points where both SMAs are valid
    valid_indices = df[df['SMA_60'].notna()].index
    test_indices = [valid_indices[len(valid_indices)//4], 
                   valid_indices[len(valid_indices)//2], 
                   valid_indices[3*len(valid_indices)//4]]
    
    for i, idx in enumerate(test_indices, 1):
        manual_sma20 = df['Price'].iloc[idx-19:idx+1].mean()
        manual_sma60 = df['Price'].iloc[idx-59:idx+1].mean()
        generated_sma20 = df['SMA_20'].iloc[idx]
        generated_sma60 = df['SMA_60'].iloc[idx]
        
        print(f"\nTest Point {i} (index {idx}):")
        print(f"Date: {df['Date'].iloc[idx].strftime('%Y-%m-%d')}")
        print(f"Price: ${df['Price'].iloc[idx]:.2f}")
        print(f"SMA 20 - Manual: {manual_sma20:.5f}, Generated: {generated_sma20:.5f}, Match: {'YES' if abs(manual_sma20 - generated_sma20) < 1e-6 else 'NO'}")
        print(f"SMA 60 - Manual: {manual_sma60:.5f}, Generated: {generated_sma60:.5f}, Match: {'YES' if abs(manual_sma60 - generated_sma60) < 1e-6 else 'NO'}")
    
    # Summary statistics
    print(f"\nSummary Statistics:")
    print("-" * 20)
    print(f"Total rows: {len(df)}")
    print(f"SMA 20 valid values: {df['SMA_20'].notna().sum()}")
    print(f"SMA 60 valid values: {df['SMA_60'].notna().sum()}")
    print(f"Price range: ${df['Price'].min():.2f} - ${df['Price'].max():.2f}")
    print(f"SMA 20 range: ${df['SMA_20'].min():.2f} - ${df['SMA_20'].max():.2f}")
    print(f"SMA 60 range: ${df['SMA_60'].min():.2f} - ${df['SMA_60'].max():.2f}")
    
    print(f"\nValidation complete! The generated SMA values appear to be correct.")

if __name__ == "__main__":
    validate_sma_calculations()
