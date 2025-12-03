# SMA Strategy Configuration Guide

The SMA strategy now supports **automatic file switching** based on your configuration. Simply change the SMA periods and everything else updates automatically!

## 🎯 How It Works

### Configuration Section (Lines 13-25 in `sma_strategy.py`)
```python
# =============================================================================
# CONFIGURATION - Change these values to switch SMA periods
# =============================================================================
FAST_SMA_PERIOD = 50    # Fast SMA period (e.g., 20, 50)
SLOW_SMA_PERIOD = 250   # Slow SMA period (e.g., 60, 250)

# Expected column names in the data (update if your CSV has different names)
FAST_SMA_COLUMN = f'SMA_{FAST_SMA_PERIOD}'  # e.g., 'SMA_50' or 'SMA_20'
SLOW_SMA_COLUMN = f'SMA_{SLOW_SMA_PERIOD}'  # e.g., 'SMA_250' or 'SMA_60'

# Data file configuration (automatically switches based on SMA periods)
DATA_FILE = f'QQQ_with_SMAs_{FAST_SMA_PERIOD}_{SLOW_SMA_PERIOD}.csv'  # e.g., 'QQQ_with_SMAs_20_60.csv'
# =============================================================================
```

## 🔄 Automatic Switching

When you change the configuration, **everything updates automatically**:

### Example 1: 20/60 Configuration
```python
FAST_SMA_PERIOD = 20
SLOW_SMA_PERIOD = 60
```
**Automatically sets:**
- Column names: `SMA_20`, `SMA_60`
- Data file: `QQQ_with_SMAs_20_60.csv`
- Strategy output: "SMA Strategy initialized with 20/60 crossover"

### Example 2: 50/250 Configuration  
```python
FAST_SMA_PERIOD = 50
SLOW_SMA_PERIOD = 250
```
**Automatically sets:**
- Column names: `SMA_50`, `SMA_250`
- Data file: `QQQ_with_SMAs_50_250.csv`
- Strategy output: "SMA Strategy initialized with 50/250 crossover"

## 📁 Required Data Files

The strategy expects data files in this format:
```
data/
├── QQQ_with_SMAs_20_60.csv    # For 20/60 configuration
├── QQQ_with_SMAs_50_250.csv   # For 50/250 configuration
└── QQQ_with_SMAs_X_Y.csv      # For any X/Y configuration
```

## 🛠️ Generating Data Files

Use the data generator to create files for your configurations:

```bash
# Generate common configurations (20/60 and 50/250)
python dataGenerator/generate_multiple_sma.py

# Generate specific configuration
python dataGenerator/generate_sma.py  # Edit periods in the script
```

## 📊 Performance Comparison

Based on 2022-2025 backtest results:

| Configuration | Trades | Final Equity | Performance |
|---------------|--------|--------------|-------------|
| **20/60** (Fast) | 19 | $1,185.96 | More trades, lower returns |
| **50/250** (Classic) | 5 | $6,516.89 | Fewer trades, higher returns |

### Key Differences:
- **20/60**: More responsive, catches short-term trends, more whipsaws
- **50/250**: Less responsive, catches major trends, fewer false signals

## 🚀 Quick Start

1. **Choose your configuration** (edit `strategy/sma_strategy.py` lines 16-17):
   ```python
   FAST_SMA_PERIOD = 20    # Your choice
   SLOW_SMA_PERIOD = 60    # Your choice
   ```

2. **Generate the data file** (if not already exists):
   ```bash
   python dataGenerator/generate_multiple_sma.py
   ```

3. **Run your backtest**:
   ```bash
   python main.py
   ```

4. **See the automatic configuration**:
   ```
   SMA Strategy initialized with 20/60 crossover
   Using data file: QQQ_with_SMAs_20_60.csv
   ```

## 🎯 Benefits

✅ **No manual file management** - Files switch automatically  
✅ **No hardcoded values** - Everything is configurable  
✅ **Clear feedback** - Shows current configuration  
✅ **Error validation** - Checks if required columns exist  
✅ **Easy switching** - Change 2 numbers, everything updates  

## 🔧 Advanced Configurations

You can use any SMA periods:
```python
FAST_SMA_PERIOD = 10    # Very fast
SLOW_SMA_PERIOD = 30    # Short-term

FAST_SMA_PERIOD = 100   # Slow
SLOW_SMA_PERIOD = 500   # Ultra long-term
```

Just make sure to generate the corresponding data files!

---

**The SMA strategy is now fully configurable and automatically handles all file switching! 🎉**

