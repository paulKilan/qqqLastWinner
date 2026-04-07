"""
prepare.py — READ-ONLY baseline and data validation for autoresearch.

This file must NOT be modified by the research agent.
It computes the QQQ buy-and-hold benchmark for any date range
and validates that data files are present and well-formed.

Adapted from karpathy/autoresearch: this is the "fixed ground truth"
that experiments are measured against.
"""

import os
import sys
import pandas as pd
import numpy as np

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT_DIR, "data")


def load_qqq_prices() -> pd.DataFrame:
    """Load QQQ.csv and return DataFrame with ['open', 'close'] and DatetimeIndex."""
    path = os.path.join(DATA_DIR, "QQQ.csv")
    if not os.path.exists(path):
        raise FileNotFoundError(f"QQQ.csv not found at {path}")

    df = pd.read_csv(path)
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.set_index("Date").sort_index()

    out = df[["Open", "Price"]].copy()
    out.columns = ["open", "close"]
    out["open"] = pd.to_numeric(out["open"].astype(str).str.replace(",", ""), errors="coerce")
    out["close"] = pd.to_numeric(out["close"].astype(str).str.replace(",", ""), errors="coerce")
    out = out.dropna(subset=["open", "close"])
    return out


def qqq_buy_and_hold(start_date: str, end_date: str) -> dict:
    """
    Compute QQQ buy-and-hold return for a date range.

    Returns dict with:
        start_price, end_price, return_pct, annualized_return_pct,
        max_drawdown_pct, trading_days
    """
    prices = load_qqq_prices()
    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date)

    mask = (prices.index >= start) & (prices.index <= end)
    period = prices.loc[mask]

    if period.empty:
        raise ValueError(f"No QQQ data in range {start_date} to {end_date}")

    close = period["close"]
    start_price = float(close.iloc[0])
    end_price = float(close.iloc[-1])
    ret = (end_price - start_price) / start_price * 100.0

    # Annualized return
    years = (period.index[-1] - period.index[0]).days / 365.25
    if years > 0:
        ann_ret = ((end_price / start_price) ** (1.0 / years) - 1.0) * 100.0
    else:
        ann_ret = 0.0

    # Max drawdown
    running_max = close.expanding().max()
    drawdowns = (close - running_max) / running_max * 100.0
    max_dd = float(drawdowns.min())

    return {
        "start_price": start_price,
        "end_price": end_price,
        "return_pct": round(ret, 4),
        "annualized_return_pct": round(ann_ret, 4),
        "max_drawdown_pct": round(max_dd, 4),
        "trading_days": len(period),
    }


def qqq_rolling_benchmarks(start_date: str, end_date: str) -> pd.DataFrame:
    """
    Compute QQQ buy-and-hold equity curve (starting from $10,000)
    for comparison with strategy equity curves.
    """
    prices = load_qqq_prices()
    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date)

    mask = (prices.index >= start) & (prices.index <= end)
    period = prices.loc[mask].copy()

    daily_ret = period["close"].pct_change().fillna(0.0)
    equity = 10_000.0 * (1.0 + daily_ret).cumprod()
    return pd.DataFrame({"BuyHold_Equity": equity}, index=period.index)


def validate_data():
    """Validate that all required data files exist and are parseable."""
    issues = []

    for fname in ["QQQ.csv"]:
        path = os.path.join(DATA_DIR, fname)
        if not os.path.exists(path):
            issues.append(f"MISSING: {fname}")
            continue
        try:
            df = pd.read_csv(path)
            if not {"Date", "Price", "Open"}.issubset(df.columns):
                issues.append(f"BAD COLUMNS in {fname}: {list(df.columns)}")
            elif len(df) < 100:
                issues.append(f"TOO FEW ROWS in {fname}: {len(df)}")
        except Exception as e:
            issues.append(f"PARSE ERROR in {fname}: {e}")

    if issues:
        print("DATA VALIDATION FAILED:")
        for i in issues:
            print(f"  - {i}")
        return False

    prices = load_qqq_prices()
    print(f"Data validated OK.")
    print(f"  QQQ: {prices.index.min().date()} to {prices.index.max().date()}, {len(prices)} trading days")
    return True


if __name__ == "__main__":
    if not validate_data():
        sys.exit(1)

    # Print benchmark for default range
    bench = qqq_buy_and_hold("2013-01-02", "2024-12-31")
    print(f"\nQQQ Buy-and-Hold Benchmark (2013-01-02 to 2024-12-31):")
    print(f"  Return:           {bench['return_pct']:+.2f}%")
    print(f"  Annualized:       {bench['annualized_return_pct']:+.2f}%")
    print(f"  Max Drawdown:     {bench['max_drawdown_pct']:.2f}%")
    print(f"  Trading Days:     {bench['trading_days']}")
    print(f"  2x Target Return: {bench['return_pct'] * 2:+.2f}%")
