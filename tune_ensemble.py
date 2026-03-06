"""
Ensemble Weight & Threshold Tuner

Systematically tests weight combinations and thresholds
across the profitable strategies to find optimal ensembles.
"""

import os
import itertools
import pandas as pd
import numpy as np
from backtest.backtest import BacktestConfig, run_backtest_with_strategy
from strategy.ensemble_strategy import EnsembleStrategy
from strategy.sma_crossover_strategy import SmaCrossoverStrategy
from strategy.ema_crossover_strategy import EmaCrossoverStrategy
from strategy.enhanced_sma_strategy import EnhancedSmaStrategy
from strategy.bollinger_bands_strategy import BollingerBandsStrategy
from strategy.rsi_strategy import RsiStrategy

# ── Config ──────────────────────────────────────────────────────
DATA_DIR         = "data"
OUTPUT_DIR       = "backtest_outputs"
START_DATE       = "2013-01-02"
END_DATE         = "2024-12-31"
INITIAL_CAPITAL  = 10_000
TRADE_PRICE      = "open"
SHARE_ROUNDING   = "floor"

# Thresholds to test
THRESHOLDS = [0.3, 0.4, 0.5, 0.6, 0.7]

# Weight grid: each strategy gets a weight from this set
# We use coarse steps first, then can refine later
WEIGHT_OPTIONS = [0.0, 0.2, 0.4, 0.6]

# Minimum number of strategies that must have weight > 0
MIN_ACTIVE = 2

# Target trade range for "moderate frequency"
TARGET_TRADES_MIN = 15
TARGET_TRADES_MAX = 200


def _load_prices(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.set_index("Date").sort_index()
    out = df[["Open", "Price"]].copy()
    out.columns = ["open", "close"]
    out["open"]  = pd.to_numeric(out["open"].astype(str).str.replace(",", ""), errors="coerce")
    out["close"] = pd.to_numeric(out["close"].astype(str).str.replace(",", ""), errors="coerce")
    return out.dropna(subset=["open", "close"])


def run_one(ensemble, tqqq, sqqq, cfg):
    """Run a single backtest, return (final_equity, n_trades, win_rate)."""
    trades, equity, _ = run_backtest_with_strategy(
        strategy=ensemble, tqqq_prices=tqqq, sqqq_prices=sqqq,
        cfg=cfg, contextData={},
    )
    if equity.empty:
        return INITIAL_CAPITAL, 0, 0.0
    final_eq = equity["Equity"].iloc[-1]
    n_trades = len(trades)
    win_rate = trades["isProfitable"].mean() * 100 if n_trades > 0 else 0.0
    return final_eq, n_trades, win_rate


def main():
    # Load price data once
    tqqq = _load_prices(os.path.join(DATA_DIR, "TQQQ.csv"))
    sqqq = _load_prices(os.path.join(DATA_DIR, "SQQQ.csv"))
    cfg = BacktestConfig(
        start_date=START_DATE, end_date=END_DATE,
        initial_capital=INITIAL_CAPITAL, trade_price=TRADE_PRICE,
        share_rounding=SHARE_ROUNDING,
    )

    # Pre-instantiate strategies once (they cache data internally)
    strat_pool = [
        ("SmaCrossover",   SmaCrossoverStrategy()),
        ("EmaCrossover",   EmaCrossoverStrategy()),
        ("EnhancedSma",    EnhancedSmaStrategy()),
        ("BollingerBands", BollingerBandsStrategy()),
        ("Rsi",            RsiStrategy()),
    ]
    n_strats = len(strat_pool)

    # Generate weight combos (coarse grid)
    combos = []
    for weights in itertools.product(WEIGHT_OPTIONS, repeat=n_strats):
        if sum(weights) == 0:
            continue
        active = sum(1 for w in weights if w > 0)
        if active < MIN_ACTIVE:
            continue
        combos.append(weights)

    print(f"Testing {len(combos)} weight combos × {len(THRESHOLDS)} thresholds "
          f"= {len(combos) * len(THRESHOLDS)} configurations\n")

    results = []
    best_equity = 0
    tested = 0

    for weights in combos:
        pairs = [(strat, w) for (_, strat), w in zip(strat_pool, weights) if w > 0]

        for thresh in THRESHOLDS:
            tested += 1
            try:
                ensemble = EnsembleStrategy(
                    strategies=pairs,
                    long_threshold=thresh,
                    short_threshold=thresh,
                )
                final_eq, n_trades, win_rate = run_one(ensemble, tqqq, sqqq, cfg)
                ret_pct = (final_eq - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100

                row = {
                    "SmaCrossover_w":   weights[0],
                    "EmaCrossover_w":   weights[1],
                    "EnhancedSma_w":    weights[2],
                    "BollingerBands_w": weights[3],
                    "Rsi_w":            weights[4],
                    "Threshold":        thresh,
                    "FinalEquity":      round(final_eq, 2),
                    "Return_pct":       round(ret_pct, 2),
                    "Trades":           n_trades,
                    "WinRate_pct":      round(win_rate, 2),
                }
                results.append(row)

                if final_eq > best_equity:
                    best_equity = final_eq
                    print(f"[{tested}] NEW BEST: ${final_eq:>12,.2f}  {ret_pct:>+9.2f}%  "
                          f"trades={n_trades:>3d}  thresh={thresh}  "
                          f"w={weights}")

            except Exception as e:
                pass  # skip broken combos silently

        # Progress every 500 tests
        if tested % 500 == 0:
            print(f"  ... {tested} configs tested")

    # ── Results ──
    df = pd.DataFrame(results)
    df.sort_values("Return_pct", ascending=False, inplace=True)

    # Save all results
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    all_path = os.path.join(OUTPUT_DIR, "ensemble_tuning_all.csv")
    df.to_csv(all_path, index=False)
    print(f"\nAll results ({len(df)} rows) saved to {all_path}")

    # Top 30 overall
    print("\n" + "=" * 100)
    print("TOP 30 BY RETURN")
    print("=" * 100)
    print(df.head(30).to_string(index=False))

    # Top 20 with moderate trade count
    moderate = df[(df["Trades"] >= TARGET_TRADES_MIN) & (df["Trades"] <= TARGET_TRADES_MAX)]
    print(f"\n{'=' * 100}")
    print(f"TOP 20 WITH MODERATE FREQUENCY ({TARGET_TRADES_MIN}-{TARGET_TRADES_MAX} trades)")
    print("=" * 100)
    print(moderate.head(20).to_string(index=False))

    # Best balanced (high return + moderate trades)
    if not moderate.empty:
        best = moderate.iloc[0]
        print(f"\n{'=' * 100}")
        print("RECOMMENDED CONFIGURATION")
        print("=" * 100)
        for col in best.index:
            print(f"  {col}: {best[col]}")


if __name__ == "__main__":
    main()
