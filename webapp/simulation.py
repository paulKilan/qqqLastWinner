"""
webapp/simulation.py — Run Iter31 backtests for 2013-2024 and return
equity curves + stats for all tickers, ready for Chart.js.
"""

import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

import pandas as pd
import numpy as np

from autoresearch.run_experiment import load_strategy, run_backtest
from autoresearch.prepare import rolling_benchmarks, load_prices

TICKERS = ["QQQ", "SPY", "NVDA", "TSLA", "GOOGL"]
START   = "2013-01-02"
END     = "2024-12-31"
INITIAL = 10_000.0

# Chart colours per ticker (strategy line, buy-and-hold line)
COLORS = {
    "QQQ":   {"strat": "#3b82f6", "bh": "#93c5fd"},  # blue
    "SPY":   {"strat": "#22c55e", "bh": "#86efac"},  # green
    "NVDA":  {"strat": "#a855f7", "bh": "#d8b4fe"},  # purple
    "TSLA":  {"strat": "#f97316", "bh": "#fdba74"},  # orange
    "GOOGL": {"strat": "#ef4444", "bh": "#fca5a5"},  # red
}


def _stats(equity: pd.Series, bh: pd.Series, n_trades: int) -> dict:
    """Compute summary stats from equity series."""
    years = (equity.index[-1] - equity.index[0]).days / 365.25

    strat_ret  = (equity.iloc[-1] / INITIAL - 1) * 100
    bh_ret     = (bh.iloc[-1]     / INITIAL - 1) * 100
    ratio      = strat_ret / bh_ret if bh_ret != 0 else 0

    # Max drawdown
    running_max = equity.expanding().max()
    dd          = (equity - running_max) / running_max * 100
    max_dd      = float(dd.min())

    # Sharpe
    dr = equity.pct_change().dropna()
    sharpe = float((dr.mean() / dr.std()) * np.sqrt(252)) if dr.std() > 0 else 0.0

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
    }


def get_simulation_data() -> dict:
    """
    Run backtests for all tickers 2013-2024.
    Returns JSON-serialisable dict ready for Chart.js.
    """
    result = {"tickers": {}, "dates": None}
    shared_dates = None   # All tickers reindexed to QQQ dates for clean x-axis

    for ticker in TICKERS:
        os.environ["STRATEGY_TICKER"] = ticker.upper()

        # Clear OHLCV cache so correct ticker file is loaded
        from autoresearch.experimental_strategy import _OHLCV_CACHE
        _OHLCV_CACHE.clear()

        strategy = load_strategy("autoresearch.experimental_strategy", "ExperimentalStrategy")
        strategy._ohlcv_data   = None
        strategy._ohlcv_ticker = None

        try:
            trades, equity_df, _ = run_backtest(strategy, START, END, ticker=ticker)
            bh_df  = rolling_benchmarks(ticker, START, END)

            equity_s = equity_df["Equity"]
            bh_s     = bh_df["BuyHold_Equity"]

            # Align both series to the same index
            idx = equity_s.index.union(bh_s.index)
            equity_s = equity_s.reindex(idx).ffill()
            bh_s     = bh_s.reindex(idx).ffill()

            if shared_dates is None:
                shared_dates = [d.strftime("%Y-%m-%d") for d in idx]

            stats = _stats(equity_s, bh_s, len(trades))

            # Downsample to weekly for smaller payload (~600 points vs 3000)
            equity_weekly = equity_s.resample("W").last().dropna()
            bh_weekly     = bh_s.resample("W").last().dropna()
            dates_weekly  = [d.strftime("%Y-%m-%d") for d in equity_weekly.index]

            result["tickers"][ticker] = {
                "dates":        dates_weekly,
                "strat_equity": [round(v, 2) for v in equity_weekly.tolist()],
                "bh_equity":    [round(v, 2) for v in bh_weekly.tolist()],
                "colors":       COLORS[ticker],
                "stats":        stats,
            }

        except Exception as e:
            result["tickers"][ticker] = {"error": str(e)}

    return result
