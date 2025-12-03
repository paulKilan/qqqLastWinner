# SMA Data Generator

This folder contains scripts to generate Simple Moving Averages (SMA) from QQQ price data.

## Files

### `generate_sma.py`
Main script that reads `QQQ.csv` and generates SMA 20 and SMA 60 values.

**Usage:**
```bash
python dataGenerator/generate_sma.py
```

**Features:**
- Reads QQQ.csv from the data folder
- Calculates SMA 20 (20-day Simple Moving Average)
- Calculates SMA 60 (60-day Simple Moving Average)
- Handles comma-formatted numbers in price data
- Maintains original date format (MM/DD/YYYY)
- Sorts data to match original QQQ.csv format (newest first)
- Outputs to `QQQ_with_SMA_20_60.csv`

### `validate_sma.py`
Validation script that verifies the accuracy of generated SMA calculations.

**Usage:**
```bash
python dataGenerator/validate_sma.py
```

**Features:**
- Validates SMA calculations with manual verification
- Shows the exact prices used in SMA calculations
- Tests multiple random points throughout the dataset
- Provides detailed accuracy reports

## Generated Output

### `QQQ_with_SMA_20_60.csv`
Contains all original QQQ data plus two new columns:
- `SMA_20`: 20-day Simple Moving Average
- `SMA_60`: 60-day Simple Moving Average

**Format:**
```
Date,Price,Open,High,Low,Vol.,Change %,SMA_20,SMA_60
10/24/2025,617.1,615.99,618.42,615.13,47.63M,1.07%,604.868,587.33267
...
```

## Data Quality

- **Total rows**: 6,701 (covering 1999-03-11 to 2025-10-24)
- **SMA 20 coverage**: 99.7% (6,682 valid values)
- **SMA 60 coverage**: 99.1% (6,642 valid values)
- **Missing values**: First 19 rows for SMA 20, first 59 rows for SMA 60 (expected behavior)

## Validation Results

✅ **All SMA calculations verified as accurate**
- Manual calculations match generated values exactly
- Tested at multiple random points throughout the dataset
- Proper handling of chronological ordering for SMA calculations

## Next Steps

1. Review the generated `QQQ_with_SMA_20_60.csv` file
2. If satisfied with the results, manually convert/rename to `QQQ_with_SMAs.csv`
3. Update your strategy to use SMA 20 and SMA 60 instead of SMA 50 and SMA 250

## Notes

- The script preserves the original QQQ.csv format (newest dates first)
- SMA values are rounded to 5 decimal places for precision
- Empty cells for insufficient data periods (as expected for moving averages)
- All price data is cleaned to handle comma-formatted numbers
