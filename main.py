import os
import importlib
from datetime import datetime
import pandas as pd
from backtest.backtest import BacktestConfig, run_backtest_with_strategy

OUTPUT_DIR = "backtest_outputs"
DATA_DIR = "data"

def _load_prices(path: str) -> pd.DataFrame:
    """
    Loads Investing.com CSV (columns: Date, Price, Open, High, Low, Vol., Change %)
    and normalizes to ['open', 'close'] for backtest use.
    """

    df = pd.read_csv(path)

    # Standard Investing.com structure:
    # Date, Price, Open, High, Low, Vol., Change %
    if not {"Date", "Price", "Open"}.issubset(df.columns):
        raise ValueError(f"{path}: unexpected column names, expected Date/Price/Open.")

    df["Date"] = pd.to_datetime(df["Date"])
    df = df.set_index("Date").sort_index()

    # Normalize: 'Price' is the CLOSE, 'Open' is the OPEN
    out = df[["Open", "Price"]].copy()
    out.columns = ["open", "close"]

    # Convert to numeric, drop NaN (handle comma-separated numbers)
    out["open"] = pd.to_numeric(out["open"].astype(str).str.replace(",", ""), errors="coerce")
    out["close"] = pd.to_numeric(out["close"].astype(str).str.replace(",", ""), errors="coerce")
    out = out.dropna(subset=["open", "close"])

    return out

def main():
    # === user-configurable bits ===
    strategy_module = "strategy.sma_strategy"
    start_date = "2022-01-01"
    end_date   = "2025-09-30"
    initial_capital = 10_000
    trade_price = "open"                 # day t + 1 "open" or "close" (open price by default)
    share_rounding = "floor"             # "floor" | "nearest" | "fractional" (floor by default)
    contextData = {}                     # free-form JSON-like dict, passed to strategy.execute
    # ==============================

    # load strategy
    strat_mod = importlib.import_module(strategy_module)
    Strategy = getattr(strat_mod, "SMAStrategy")
    strategy = Strategy()

    # load ETF data
    tqqq = _load_prices(os.path.join(DATA_DIR, "TQQQ.csv"))
    sqqq = _load_prices(os.path.join(DATA_DIR, "SQQQ.csv"))

    # config
    cfg = BacktestConfig(
        start_date=start_date,
        end_date=end_date,
        initial_capital=initial_capital,
        trade_price=trade_price,          # t+1 open by default
        share_rounding=share_rounding,
    )

    # run
    trades, equity, issues = run_backtest_with_strategy(
        strategy=strategy,
        tqqq_prices=tqqq,
        sqqq_prices=sqqq,
        cfg=cfg,
        contextData=contextData
    )

    # save
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    trades_path = os.path.join(OUTPUT_DIR, f"trades_{ts}.csv")

    trades.to_csv(trades_path, index=False)

    print("Backtest complete")
    print(f"Trades : {trades_path}")
    if not trades.empty:
        print(f"Total trades: {len(trades)}")
        print(f"Final Equity: ${equity['Equity'].iloc[-1]:,.2f}")

if __name__ == "__main__":
    main()
