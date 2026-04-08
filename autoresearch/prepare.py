"""
prepare.py — READ-ONLY baseline and data validation for autoresearch.

This file must NOT be modified by the research agent.
It computes the buy-and-hold benchmark for any ticker and date range,
and validates that data files are present and well-formed.

Adapted from karpathy/autoresearch: this is the "fixed ground truth"
that experiments are measured against.

Ticker support
--------------
Two data sources are accepted (tried in order):

1. autoresearch/{ticker.lower()}_ohlcv.csv
   Columns: date (index), open_adj, high_adj, low_adj, close_adj, volume
   Used for: QQQ (extended 1990-2025), SPY, NVDA, TSLA, GOOGL, etc.

2. data/{TICKER}.csv  (legacy QQQ format from investing.com)
   Columns: Date (index), Open, Price, ...
   Used for: QQQ fallback only.
"""

import os
import sys
import pandas as pd
import numpy as np

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT_DIR, "data")
AUTORESEARCH_DIR = os.path.dirname(os.path.abspath(__file__))


def load_prices(ticker: str = "QQQ") -> pd.DataFrame:
    """
    Load adjusted daily price data for *ticker*.

    Returns a DataFrame with columns ['open', 'close'] and a DatetimeIndex.

    Search order
    ------------
    1. autoresearch/{ticker.lower()}_ohlcv.csv  — preferred; always adjusted.
    2. data/{TICKER}.csv                        — legacy investing.com format (QQQ only).
    """
    ticker = ticker.upper()

    # ── 1. OHLCV file (preferred) ─────────────────────────────────────────────
    ohlcv_path = os.path.join(AUTORESEARCH_DIR, f"{ticker.lower()}_ohlcv.csv")
    if os.path.exists(ohlcv_path):
        df = pd.read_csv(ohlcv_path, index_col=0, parse_dates=True)
        df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
        df.index.name = "Date"

        # Resolve close column
        if "close_adj" in df.columns:
            close = df["close_adj"].astype(float)
        elif "close" in df.columns:
            close = df["close"].astype(float)
        else:
            raise ValueError(f"No close price column in {ohlcv_path}")

        # Resolve open column
        if "open_adj" in df.columns:
            open_ = df["open_adj"].astype(float)
        elif "open" in df.columns:
            open_ = df["open"].astype(float)
        else:
            open_ = close  # fallback: use close as open proxy

        out = pd.DataFrame({"open": open_, "close": close})
        return out.dropna()

    # ── 2. Legacy data/{TICKER}.csv ───────────────────────────────────────────
    csv_path = os.path.join(DATA_DIR, f"{ticker}.csv")
    if not os.path.exists(csv_path):
        raise FileNotFoundError(
            f"No price data found for {ticker}.\n"
            f"  Tried OHLCV : {ohlcv_path}\n"
            f"  Tried legacy: {csv_path}\n"
            f"Run: python -m autoresearch.fetch_ticker {ticker}"
        )

    df = pd.read_csv(csv_path)
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.set_index("Date").sort_index()

    out = df[["Open", "Price"]].copy()
    out.columns = ["open", "close"]
    out["open"]  = pd.to_numeric(out["open"].astype(str).str.replace(",", ""),  errors="coerce")
    out["close"] = pd.to_numeric(out["close"].astype(str).str.replace(",", ""), errors="coerce")
    return out.dropna(subset=["open", "close"])


def buy_and_hold(ticker: str, start_date: str, end_date: str) -> dict:
    """
    Compute buy-and-hold return for *ticker* over [start_date, end_date].

    Returns dict with:
        start_price, end_price, return_pct, annualized_return_pct,
        max_drawdown_pct, trading_days
    """
    prices = load_prices(ticker)
    start = pd.to_datetime(start_date)
    end   = pd.to_datetime(end_date)

    mask   = (prices.index >= start) & (prices.index <= end)
    period = prices.loc[mask]

    if period.empty:
        raise ValueError(f"No {ticker} data in range {start_date} to {end_date}")

    close       = period["close"]
    start_price = float(close.iloc[0])
    end_price   = float(close.iloc[-1])
    ret         = (end_price - start_price) / start_price * 100.0

    years   = (period.index[-1] - period.index[0]).days / 365.25
    ann_ret = ((end_price / start_price) ** (1.0 / max(years, 0.001)) - 1.0) * 100.0 if years > 0 else 0.0

    running_max = close.expanding().max()
    drawdowns   = (close - running_max) / running_max * 100.0
    max_dd      = float(drawdowns.min())

    return {
        "start_price":            start_price,
        "end_price":              end_price,
        "return_pct":             round(ret, 4),
        "annualized_return_pct":  round(ann_ret, 4),
        "max_drawdown_pct":       round(max_dd, 4),
        "trading_days":           len(period),
    }


# ── Backward-compatible aliases (QQQ default) ─────────────────────────────────
def load_qqq_prices() -> pd.DataFrame:
    """Alias for load_prices('QQQ') — kept for backward compatibility."""
    return load_prices("QQQ")


def qqq_buy_and_hold(start_date: str, end_date: str) -> dict:
    """Alias for buy_and_hold('QQQ', ...) — kept for backward compatibility."""
    return buy_and_hold("QQQ", start_date, end_date)


def rolling_benchmarks(ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
    """
    Compute buy-and-hold equity curve (starting from $10,000) for *ticker*.
    Used for comparison with strategy equity curves.
    """
    prices = load_prices(ticker)
    start  = pd.to_datetime(start_date)
    end    = pd.to_datetime(end_date)

    mask   = (prices.index >= start) & (prices.index <= end)
    period = prices.loc[mask].copy()

    daily_ret = period["close"].pct_change().fillna(0.0)
    equity    = 10_000.0 * (1.0 + daily_ret).cumprod()
    return pd.DataFrame({"BuyHold_Equity": equity}, index=period.index)


def qqq_rolling_benchmarks(start_date: str, end_date: str) -> pd.DataFrame:
    """Alias for rolling_benchmarks('QQQ', ...) — kept for backward compatibility."""
    return rolling_benchmarks("QQQ", start_date, end_date)


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
