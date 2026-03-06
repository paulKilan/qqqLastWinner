import pandas as pd
import os
from strategy.sma_crossover_strategy import SmaCrossoverStrategy
from backtest.backtest import normalize_strategy_output, align_data_and_shift_positions, BacktestConfig

def debug_strategy():
    print("Initializing Strategy...")
    strategy = SmaCrossoverStrategy()
    
    print("Loading Data...")
    # Manually load data to check dates
    tqqq = pd.read_csv("data/TQQQ.csv")
    sqqq = pd.read_csv("data/SQQQ.csv")
    print(f"TQQQ Range: {tqqq['Date'].min()} to {tqqq['Date'].max()}")
    print(f"SQQQ Range: {sqqq['Date'].min()} to {sqqq['Date'].max()}")
    
    print("Executing Strategy...")
    start_date = "2022-01-01"
    end_date = "2025-09-30"
    
    output = strategy.execute(start_date, end_date)
    print("Strategy Output Head:")
    print(output.head())
    print("Strategy Output Tail:")
    print(output.tail())
    
    print("\nChecking for signals...")
    longs = output[output['longPositionPct'] == 1.0]
    shorts = output[output['shortPositionPct'] == 1.0]
    print(f"Long Signals: {len(longs)}")
    print(f"Short Signals: {len(shorts)}")
    
    if len(longs) == 0 and len(shorts) == 0:
        print("NO SIGNALS GENERATED!")
        return

    print("\nNormalizing Output...")
    positions, errors = normalize_strategy_output(output)
    print("Positions Head:")
    print(positions.head())
    
    print("\nAligning Data...")
    tqqq_prices = _load_prices("data/TQQQ.csv")
    sqqq_prices = _load_prices("data/SQQQ.csv")
    
    cfg = BacktestConfig(start_date=start_date, end_date=end_date)
    
    exec_dates, shifted_positions, tqqq, sqqq = align_data_and_shift_positions(
        positions, tqqq_prices, sqqq_prices, cfg
    )
    
    print(f"\nExecution Dates: {len(exec_dates)}")
    print("Shifted Positions Head:")
    print(shifted_positions.head())
    
    print("\nChecking for position changes in shifted positions...")
    changes = 0
    prev_w_tqqq = None
    for date in exec_dates:
        w_tqqq = shifted_positions.loc[date, "w_tqqq"]
        if prev_w_tqqq is not None and w_tqqq != prev_w_tqqq:
            changes += 1
        prev_w_tqqq = w_tqqq
    print(f"Position Changes detected: {changes}")

def _load_prices(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    if not {"Date", "Price", "Open"}.issubset(df.columns):
        raise ValueError(f"{path}: unexpected column names, expected Date/Price/Open.")
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.set_index("Date").sort_index()
    out = df[["Open", "Price"]].copy()
    out.columns = ["open", "close"]
    out["open"] = pd.to_numeric(out["open"].astype(str).str.replace(",", ""), errors="coerce")
    out["close"] = pd.to_numeric(out["close"].astype(str).str.replace(",", ""), errors="coerce")
    out = out.dropna(subset=["open", "close"])
    return out

if __name__ == "__main__":
    debug_strategy()
