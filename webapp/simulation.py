"""
webapp/simulation.py — Run Iter31 backtests for 2013-2024 and return
equity curves + trade markers + stats for all tickers, ready for Chart.js.
"""

import os
import sys

ROOT_DIR         = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUTORESEARCH_DIR = os.path.join(ROOT_DIR, "autoresearch")
sys.path.insert(0, ROOT_DIR)

import pandas as pd
import numpy as np

from autoresearch.run_experiment import load_strategy, run_backtest
from autoresearch.prepare import rolling_benchmarks, load_prices

TICKERS        = ["QQQ"]
START          = "2007-01-03"  # Long-horizon view; data goes back further but 2007 captures GFC + every cycle since
INITIAL        = 10_000.0
STALE_DAYS     = 5   # refresh data if last row is older than this many calendar days

COLORS = {
    "QQQ":   {"strat": "#3b82f6", "bh": "#93c5fd", "buy": "#22c55e", "sell": "#ef4444"},
}


def _stats(equity: pd.Series, bh: pd.Series, trades_df: pd.DataFrame) -> dict:
    years     = (equity.index[-1] - equity.index[0]).days / 365.25
    n_trades  = len(trades_df)
    strat_ret = (equity.iloc[-1] / INITIAL - 1) * 100
    bh_ret    = (bh.iloc[-1]     / INITIAL - 1) * 100
    ratio     = strat_ret / bh_ret if bh_ret != 0 else 0

    running_max = equity.expanding().max()
    dd          = (equity - running_max) / running_max * 100
    max_dd      = float(dd.min())

    dr     = equity.pct_change().dropna()
    sharpe = float((dr.mean() / dr.std()) * np.sqrt(252)) if dr.std() > 0 else 0.0

    win_rate = float(trades_df["isProfitable"].mean()) if n_trades > 0 else 0.0
    avg_profit = float(trades_df["ProfitPercent"].mean() * 100) if n_trades > 0 else 0.0

    return {
        "strat_return_pct": round(strat_ret, 1),
        "bh_return_pct":    round(bh_ret, 1),
        "ratio":            round(ratio, 2),
        "final_equity":     round(float(equity.iloc[-1]), 0),
        "bh_final_equity":  round(float(bh.iloc[-1]), 0),
        "max_drawdown_pct": round(max_dd, 1),
        "sharpe":           round(sharpe, 2),
        "trades_per_year":  round(n_trades / max(years, 0.1), 1),
        "n_trades":         n_trades,
        "win_rate":         round(win_rate * 100, 1),
        "avg_profit_pct":   round(avg_profit, 2),
    }


def _trade_markers(trades_df: pd.DataFrame, equity_s: pd.Series) -> dict:
    """
    Build entry and exit marker arrays for Chart.js scatter overlay.
    Each marker: { x: date, y: equity_at_that_date, meta: {trade details} }
    """
    entries = []
    exits   = []

    for _, row in trades_df.iterrows():
        entry_date = row["StartDate"]
        exit_date  = row["EndDate"]
        direction  = row["Direction"]
        is_short   = bool(row["isShortSale"])

        # Find equity value at entry and exit dates (nearest available)
        def equity_at(dt):
            idx = equity_s.index.searchsorted(dt)
            idx = min(idx, len(equity_s) - 1)
            return round(float(equity_s.iloc[idx]), 2)

        entry_eq = equity_at(entry_date)
        exit_eq  = equity_at(exit_date)

        profit_pct = round(float(row["ProfitPercent"]) * 100, 2)
        profit_abs = round(float(row["Profit"]), 2)
        duration   = int(row["Duration"])

        meta = {
            "direction":   direction,
            "is_short":    is_short,
            "entry_date":  entry_date.strftime("%Y-%m-%d"),
            "exit_date":   exit_date.strftime("%Y-%m-%d"),
            "entry_price": round(float(row["BuyPrice"]), 2),
            "exit_price":  round(float(row["SellPrice"]), 2),
            "shares":      round(float(row["ShareSize"]), 4),
            "profit_pct":  profit_pct,
            "profit_abs":  profit_abs,
            "duration":    duration,
            "profitable":  bool(row["isProfitable"]),
            "equity_after_exit": exit_eq,
        }

        entries.append({
            "x": entry_date.strftime("%Y-%m-%d"),
            "y": entry_eq,
            "meta": meta,
        })
        exits.append({
            "x": exit_date.strftime("%Y-%m-%d"),
            "y": exit_eq,
            "meta": meta,
        })

    return {"entries": entries, "exits": exits}


def _is_stale(ticker: str) -> bool:
    """Return True if the ticker's OHLCV file is missing or older than STALE_DAYS."""
    from datetime import date
    path = os.path.join(AUTORESEARCH_DIR, f"{ticker.lower()}_ohlcv.csv")
    if not os.path.exists(path):
        return True
    df   = pd.read_csv(path, index_col=0, parse_dates=True)
    last = df.index.max().date()
    return (date.today() - last).days > STALE_DAYS


def get_simulation_data(strategy_id: str = "iter31") -> dict:
    from datetime import date
    from webapp.strategy_registry import find_strategy, instantiate_strategy
    end_date = date.today().strftime("%Y-%m-%d")

    # Auto-refresh any ticker whose data is stale
    from webapp.signals import refresh_ticker
    refreshed = []
    for ticker in TICKERS:
        if _is_stale(ticker):
            ok = refresh_ticker(ticker)
            if ok:
                refreshed.append(ticker)

    strategy_spec = find_strategy(strategy_id)
    result = {
        "tickers": {}, "start": START, "end": end_date, "refreshed": refreshed,
        "strategy": {
            "id": strategy_spec["id"], "label": strategy_spec["label"],
            "source": strategy_spec["source"], "description": strategy_spec["description"],
        },
    }

    for ticker in TICKERS:
        os.environ["STRATEGY_TICKER"] = ticker.upper()

        # Clear any cached OHLCV in both strategy classes so a fresh strategy
        # picks up the latest data.
        try:
            from autoresearch.experimental_strategy import _OHLCV_CACHE
            _OHLCV_CACHE.clear()
        except Exception:
            pass

        strategy = instantiate_strategy(strategy_spec, ticker=ticker)
        # Reset any per-ticker caches the strategy might hold
        for attr in ("_ohlcv_data", "_ohlcv_ticker"):
            if hasattr(strategy, attr):
                setattr(strategy, attr, None)

        try:
            trades_df, equity_df, _ = run_backtest(strategy, START, end_date, ticker=ticker)
            bh_df = rolling_benchmarks(ticker, START, end_date)

            equity_s = equity_df["Equity"]
            bh_s     = bh_df["BuyHold_Equity"]

            idx      = equity_s.index.union(bh_s.index)
            equity_s = equity_s.reindex(idx).ffill()
            bh_s     = bh_s.reindex(idx).ffill()

            stats   = _stats(equity_s, bh_s, trades_df)
            markers = _trade_markers(trades_df, equity_s)

            # Weekly equity curve for chart (~600 pts)
            eq_w  = equity_s.resample("W").last().dropna()
            bh_w  = bh_s.resample("W").last().dropna()

            result["tickers"][ticker] = {
                "dates":        [d.strftime("%Y-%m-%d") for d in eq_w.index],
                "strat_equity": [round(v, 2) for v in eq_w.tolist()],
                "bh_equity":    [round(v, 2) for v in bh_w.tolist()],
                "markers":      markers,
                "colors":       COLORS[ticker],
                "stats":        stats,
            }

        except Exception as e:
            result["tickers"][ticker] = {"error": str(e)}

    return result
