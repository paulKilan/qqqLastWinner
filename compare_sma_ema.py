import pandas as pd
import os
from backtest.backtest import BacktestConfig, run_backtest_with_strategy
from strategy.sma_crossover_strategy import SmaCrossoverStrategy
from strategy.ema_crossover_strategy import EmaCrossoverStrategy

DATA_DIR = "data"

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

def run_comparison():
    # Load Data
    tqqq = _load_prices(os.path.join(DATA_DIR, "TQQQ.csv"))
    sqqq = _load_prices(os.path.join(DATA_DIR, "SQQQ.csv"))

    # Config
    cfg = BacktestConfig(
        start_date="2013-01-02",
        end_date="2024-12-31",
        initial_capital=10_000,
        trade_price="open",
        share_rounding="floor",
    )

    # Run SMA
    print("Running SMA...")
    sma_strat = SmaCrossoverStrategy()
    sma_trades, _, _ = run_backtest_with_strategy(sma_strat, tqqq, sqqq, cfg)
    sma_trades.to_csv("comparison_sma.csv", index=False)
    print(f"SMA Trades: {len(sma_trades)}")

    # Run EMA
    print("Running EMA...")
    ema_strat = EmaCrossoverStrategy()
    ema_trades, _, _ = run_backtest_with_strategy(ema_strat, tqqq, sqqq, cfg)
    ema_trades.to_csv("comparison_ema.csv", index=False)
    print(f"EMA Trades: {len(ema_trades)}")

if __name__ == "__main__":
    run_comparison()
