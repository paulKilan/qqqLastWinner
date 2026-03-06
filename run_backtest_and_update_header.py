import os
import sys
import importlib
import pandas as pd
from datetime import datetime
from backtest.backtest import BacktestConfig, run_backtest_with_strategy

# Add project root to path
sys.path.append(os.getcwd())

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

def run_and_update(strategy_module, strategy_class_name):
    print(f"Running backtest for {strategy_class_name} in {strategy_module}...")
    
    # Load strategy
    try:
        strat_mod = importlib.import_module(strategy_module)
        Strategy = getattr(strat_mod, strategy_class_name)
        strategy = Strategy()
    except Exception as e:
        print(f"Error loading strategy: {e}")
        return

    # Load Data
    tqqq = _load_prices(os.path.join(DATA_DIR, "TQQQ.csv"))
    sqqq = _load_prices(os.path.join(DATA_DIR, "SQQQ.csv"))

    # Config (Standard for all)
    cfg = BacktestConfig(
        start_date="2013-01-02",
        end_date="2024-12-31",
        initial_capital=10_000,
        trade_price="open",
        share_rounding="floor",
    )

    # Run Backtest
    trades, equity, issues = run_backtest_with_strategy(
        strategy=strategy,
        tqqq_prices=tqqq,
        sqqq_prices=sqqq,
        cfg=cfg,
        contextData={}
    )

    # Calculate Metrics
    total_trades = len(trades)
    final_equity = equity['Equity'].iloc[-1] if not equity.empty else 10000
    return_pct = ((final_equity - 10000) / 10000) * 100
    
    results_comment = f"""'''
Backtest Results:
- Start Date: {cfg.start_date}
- End Date: {cfg.end_date}
- Initial Capital: ${cfg.initial_capital:,.2f}
- Final Equity: ${final_equity:,.2f}
- Total Trades: {total_trades}
- Return: {return_pct:.2f}%
'''
"""

    # Update File
    module_path = strategy_module.replace(".", "/") + ".py"
    if os.path.exists(module_path):
        with open(module_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Remove existing results comment if present (simple check)
        if content.startswith("'''\nBacktest Results:"):
            end_quote_idx = content.find("'''\n", 4)
            if end_quote_idx != -1:
                content = content[end_quote_idx+4:]
        
        new_content = results_comment + content
        
        with open(module_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"Updated {module_path} with results.")
    else:
        print(f"File {module_path} not found.")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python run_backtest_and_update_header.py <module> <class_name>")
    else:
        run_and_update(sys.argv[1], sys.argv[2])
