"""
SMA Strategy Configuration Examples

This file shows how to easily switch between different SMA periods
by modifying the configuration at the top of sma_strategy.py
"""

# =============================================================================
# EXAMPLE CONFIGURATIONS
# =============================================================================

# Configuration 1: Classic Golden Cross (50/200 or 50/250)
CLASSIC_CONFIG = {
    "FAST_SMA_PERIOD": 50,
    "SLOW_SMA_PERIOD": 250,
    "DESCRIPTION": "Classic long-term trend following with 50/250 crossover"
}

# Configuration 2: Faster Response (20/60)
FAST_CONFIG = {
    "FAST_SMA_PERIOD": 20,
    "SLOW_SMA_PERIOD": 60,
    "DESCRIPTION": "Faster response to trend changes with 20/60 crossover"
}

# Configuration 3: Very Fast (10/30)
VERY_FAST_CONFIG = {
    "FAST_SMA_PERIOD": 10,
    "SLOW_SMA_PERIOD": 30,
    "DESCRIPTION": "Very fast response for short-term trading with 10/30 crossover"
}

# Configuration 4: Ultra Long-term (100/500)
ULTRA_LONG_CONFIG = {
    "FAST_SMA_PERIOD": 100,
    "SLOW_SMA_PERIOD": 500,
    "DESCRIPTION": "Ultra long-term trend following with 100/500 crossover"
}

# =============================================================================
# HOW TO SWITCH CONFIGURATIONS
# =============================================================================

"""
To switch between configurations:

1. Open strategy/sma_strategy.py
2. Find the CONFIGURATION section at the top (lines 13-22)
3. Change these two lines:

   FAST_SMA_PERIOD = 50    # Change this number
   SLOW_SMA_PERIOD = 250   # Change this number

4. Make sure your QQQ_with_SMAs.csv has the corresponding SMA columns:
   - For 20/60: needs SMA_20 and SMA_60 columns
   - For 50/250: needs SMA_50 and SMA_250 columns

EXAMPLES:

For 20/60 configuration:
   FAST_SMA_PERIOD = 20
   SLOW_SMA_PERIOD = 60

For 10/30 configuration:
   FAST_SMA_PERIOD = 10
   SLOW_SMA_PERIOD = 30

The strategy will automatically:
- Update column names (SMA_20, SMA_60, etc.)
- Update all logic and analysis functions
- Print the current configuration when initialized
- Validate that required columns exist in your data
"""

# =============================================================================
# PERFORMANCE EXPECTATIONS
# =============================================================================

PERFORMANCE_NOTES = """
Different SMA periods will have different characteristics:

FASTER SMAs (e.g., 20/60):
✓ More responsive to price changes
✓ More trading signals (higher frequency)
✓ Better at catching short-term trends
✗ More whipsaws and false signals
✗ Higher transaction costs

SLOWER SMAs (e.g., 50/250):
✓ Fewer false signals
✓ Better for long-term trends
✓ Lower transaction costs
✗ Slower to respond to trend changes
✗ May miss shorter-term opportunities

CHOOSE BASED ON:
- Market conditions (trending vs choppy)
- Risk tolerance
- Transaction costs
- Time horizon
"""

if __name__ == "__main__":
    print("SMA Strategy Configuration Guide")
    print("=" * 50)
    
    configs = [CLASSIC_CONFIG, FAST_CONFIG, VERY_FAST_CONFIG, ULTRA_LONG_CONFIG]
    
    for i, config in enumerate(configs, 1):
        print(f"\n{i}. {config['DESCRIPTION']}")
        print(f"   Fast SMA: {config['FAST_SMA_PERIOD']} periods")
        print(f"   Slow SMA: {config['SLOW_SMA_PERIOD']} periods")
        print(f"   Required columns: SMA_{config['FAST_SMA_PERIOD']}, SMA_{config['SLOW_SMA_PERIOD']}")
    
    print(f"\n{PERFORMANCE_NOTES}")
    print("\nTo switch configurations, edit the CONFIGURATION section in strategy/sma_strategy.py")
