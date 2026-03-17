"""
tune_ensemble.py
Grid-search for the best EnsembleStrategy configuration.

Phase 1: All non-empty subsets of the top profitable strategies,
         equal weights, sweep thresholds 0.1-0.7 → find best subsets.

Phase 2: Top subsets from Phase 1 get a weight sweep (every strategy
         gets weight 1, 2, or 3) with thresholds 0.2-0.5.

Scores each config on BOTH 3x and 1x modes and reports:
  - Top 10 by 3X return
  - Top 10 by 1X return
  - Top 10 by risk-adjusted score (return / abs(max_drawdown))
  - Top 10 by win rate (min 10 trades)
"""

import os
import importlib
import itertools
import pandas as pd
from datetime import datetime
from backtest.backtest import BacktestConfig, run_backtest_with_strategy
from strategy.ensemble_strategy import EnsembleStrategy

# ── config ────────────────────────────────────────────────────────────────────
DATA_DIR        = "data"
OUTPUT_DIR      = "backtest_outputs"
START_DATE      = "2013-01-02"
END_DATE        = "2024-12-31"
INITIAL_CAPITAL = 10_000
TRADE_PRICE     = "open"
SHARE_ROUNDING  = "fractional"

# All strategies with a short label
ALL_STRATS = {
    "SMA":     ("strategy.sma_crossover_strategy",    "SmaCrossoverStrategy"),
    "EMA":     ("strategy.ema_crossover_strategy",    "EmaCrossoverStrategy"),
    "ESMA":    ("strategy.enhanced_sma_strategy",     "EnhancedSmaStrategy"),
    "BB":      ("strategy.bollinger_bands_strategy",  "BollingerBandsStrategy"),
    "RSI":     ("strategy.rsi_strategy",              "RsiStrategy"),
    "MACD":    ("strategy.macd_strategy",             "MacdStrategy"),
    "MOM":     ("strategy.momentum_strategy",         "MomentumStrategy"),
    "STOCH":   ("strategy.stochastic_strategy",       "StochasticStrategy"),
    "DON":     ("strategy.donchian_channel_strategy", "DonchianChannelStrategy"),
    "WILLR":   ("strategy.williams_r_strategy",       "WilliamsRStrategy"),
    "ATR":     ("strategy.atr_breakout_strategy",     "AtrBreakoutStrategy"),
    "TRBOUNCE":("strategy.trend_bounce_strategy",     "TrendBounceStrategy"),
}

# Phase 1: sweep subsets from these candidates
PHASE1_POOL = ["SMA", "EMA", "ESMA", "BB", "RSI"]

# Phase 2: allow these additional strategies at low weight (1) to test as hedges
PHASE2_EXTRAS = ["MACD", "MOM", "STOCH", "DON", "WILLR", "ATR", "TRBOUNCE"]

THRESHOLDS_P1 = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7]
THRESHOLDS_P2 = [0.2, 0.3, 0.4, 0.5]
WEIGHT_LEVELS = [1, 2, 3]   # Phase 2 per-strategy weights

MIN_TRADES    = 5            # configs with fewer trades are excluded

# ── helpers ───────────────────────────────────────────────────────────────────
def _load_prices(path):
    df = pd.read_csv(path)
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.set_index("Date").sort_index()
    out = df[["Open", "Price"]].copy()
    out.columns = ["open", "close"]
    out["open"]  = pd.to_numeric(out["open"].astype(str).str.replace(",", ""), errors="coerce")
    out["close"] = pd.to_numeric(out["close"].astype(str).str.replace(",", ""), errors="coerce")
    return out.dropna(subset=["open", "close"])

def _max_drawdown(eq):
    return ((eq - eq.expanding().max()) / eq.expanding().max() * 100).min()

# Cache strategy instances to avoid re-importing
_strat_cache = {}
def _get_instance(key):
    # Always return a fresh instance (strategy may be stateful)
    mp, cn = ALL_STRATS[key]
    mod = importlib.import_module(mp)
    return getattr(mod, cn)()

def _build_ensemble(weights_dict, thresh):
    """weights_dict: {key: weight_int}, thresh: (long_t, short_t)"""
    pairs = [((_get_instance(k)), w) for k, w in weights_dict.items() if w > 0]
    return EnsembleStrategy(
        strategies=pairs,
        long_threshold=thresh,
        short_threshold=thresh,
    )

def _run(ensemble, mode, prices):
    long_px, short_px = prices[mode]
    cfg = BacktestConfig(
        start_date=START_DATE, end_date=END_DATE,
        initial_capital=INITIAL_CAPITAL,
        trade_price=TRADE_PRICE,
        share_rounding=SHARE_ROUNDING,
        leverage_mode=mode,
    )
    try:
        trades, equity, _ = run_backtest_with_strategy(
            strategy=ensemble, tqqq_prices=long_px,
            sqqq_prices=short_px, cfg=cfg, contextData={},
        )
        final = equity["Equity"].iloc[-1]
        ret   = (final - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100
        n     = len(trades)
        winr  = trades["isProfitable"].mean() * 100 if n > 0 else 0.0
        mdd   = _max_drawdown(equity["Equity"])
        adj   = ret / abs(mdd) if mdd != 0 else 0.0   # risk-adjusted score
        return dict(ret=ret, trades=n, winr=winr, mdd=mdd, adj=adj)
    except Exception:
        return None


# ── main ──────────────────────────────────────────────────────────────────────
def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    tqqq = _load_prices(os.path.join(DATA_DIR, "TQQQ.csv"))
    sqqq = _load_prices(os.path.join(DATA_DIR, "SQQQ.csv"))
    qqq  = _load_prices(os.path.join(DATA_DIR, "QQQ.csv"))
    prices = {"3x": (tqqq, sqqq), "1x": (qqq, qqq)}

    results = []

    # ── PHASE 1: all non-empty subsets of PHASE1_POOL, equal weights ──────────
    print("Phase 1: sweeping subsets of profitable strategies...")
    total_p1 = (2**len(PHASE1_POOL) - 1) * len(THRESHOLDS_P1)
    done = 0

    for r in range(1, len(PHASE1_POOL) + 1):
        for subset in itertools.combinations(PHASE1_POOL, r):
            weights = {k: 1 for k in subset}
            label = "+".join(subset)

            for thresh in THRESHOLDS_P1:
                for mode in ["3x", "1x"]:
                    ens = _build_ensemble(weights, thresh)
                    res = _run(ens, mode, prices)
                    if res and res["trades"] >= MIN_TRADES:
                        results.append(dict(
                            phase=1, label=label, weights=str(weights),
                            thresh=thresh, lev=mode, **res
                        ))
                done += 1
                if done % 20 == 0:
                    print(f"  {done}/{total_p1}  latest: {label} t={thresh:.1f}")

    print(f"Phase 1 done: {len(results)} valid configs so far.")

    # ── PHASE 2: weight sweep on top Phase-1 subsets ──────────────────────────
    # Pick the top 5 subsets by 3X return from Phase 1
    p1_df = pd.DataFrame([r for r in results if r["lev"] == "3x"])
    if not p1_df.empty:
        top_labels = p1_df.nlargest(5, "ret")["label"].unique().tolist()

        print(f"\nPhase 2: weight sweep on top subsets: {top_labels}")
        total_p2 = 0
        p2_configs = []

        for label in top_labels:
            keys = label.split("+")
            # Generate all weight combos (each key gets 1, 2, or 3)
            for weight_combo in itertools.product(WEIGHT_LEVELS, repeat=len(keys)):
                # skip if all same weight (equivalent to equal weights already done)
                if len(set(weight_combo)) == 1:
                    continue
                weights = dict(zip(keys, weight_combo))
                for thresh in THRESHOLDS_P2:
                    p2_configs.append((label, weights, thresh))

        total_p2 = len(p2_configs)
        print(f"  Testing {total_p2} Phase-2 configs...")

        for i, (label, weights, thresh) in enumerate(p2_configs):
            wlabel = label + " " + str(weights)
            for mode in ["3x", "1x"]:
                ens = _build_ensemble(weights, thresh)
                res = _run(ens, mode, prices)
                if res and res["trades"] >= MIN_TRADES:
                    results.append(dict(
                        phase=2, label=wlabel, weights=str(weights),
                        thresh=thresh, lev=mode, **res
                    ))
            if (i + 1) % 50 == 0:
                print(f"  {i+1}/{total_p2}")

    # ── PHASE 3: Add one "losing" strategy as a hedge alongside each top subset
    print("\nPhase 3: testing losing strategies as hedges on top combos...")
    p3_base = ["SMA+EMA", "SMA+EMA+ESMA", "SMA+EMA+BB"]
    for base_label in p3_base:
        base_keys = base_label.split("+")
        for extra in PHASE2_EXTRAS:
            weights = {k: 2 for k in base_keys}
            weights[extra] = 1   # low-weight hedge
            label = base_label + "+" + extra
            for thresh in THRESHOLDS_P2:
                for mode in ["3x", "1x"]:
                    ens = _build_ensemble(weights, thresh)
                    res = _run(ens, mode, prices)
                    if res and res["trades"] >= MIN_TRADES:
                        results.append(dict(
                            phase=3, label=label, weights=str(weights),
                            thresh=thresh, lev=mode, **res
                        ))

    # ── Summarize results ─────────────────────────────────────────────────────
    df = pd.DataFrame(results)
    W = 130

    def print_table(title, subset, sort_col, n=10):
        print("\n" + "=" * W)
        print(f"  {title}")
        print("=" * W)
        print(f"  {'Label':<45} {'Thr':>5} {'Mode':<5} {'Return':>9} {'Win%':>6} "
              f"{'MaxDD':>8} {'Adj':>7} {'Trades':>7} {'Ph':>3}")
        print("  " + "-" * (W - 2))
        top = subset.nlargest(n, sort_col)
        for _, r in top.iterrows():
            print(f"  {r.label:<45} {r.thresh:>5.2f} {r['lev']:<5} {r.ret:>+8.1f}% "
                  f"{r.winr:>5.1f}% {r.mdd:>7.1f}% {r.adj:>7.2f} "
                  f"{int(r.trades):>7}  {int(r.phase):>2}")

    print_table("TOP 10 by 3X RETURN",        df[df["lev"]=="3x"], "ret")
    print_table("TOP 10 by 1X RETURN",        df[df["lev"]=="1x"], "ret")
    print_table("TOP 10 by 3X RISK-ADJUSTED", df[df["lev"]=="3x"], "adj")
    print_table("TOP 10 by 1X RISK-ADJUSTED", df[df["lev"]=="1x"], "adj")
    print_table("TOP 10 by WIN RATE (3x, >=10 trades)",
                df[(df["lev"]=="3x") & (df["trades"]>=10)], "winr")

    # ── Save ─────────────────────────────────────────────────────────────────
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = os.path.join(OUTPUT_DIR, f"tune_results_{ts}.csv")
    df.to_csv(csv_path, index=False)

    # Best config overall: highest 3X return
    best_3x     = df[df["lev"]=="3x"].nlargest(1, "ret").iloc[0]
    best_1x     = df[df["lev"]=="1x"].nlargest(1, "ret").iloc[0]
    best_3x_adj = df[df["lev"]=="3x"].nlargest(1, "adj").iloc[0]
    best_1x_adj = df[df["lev"]=="1x"].nlargest(1, "adj").iloc[0]

    print("\n" + "=" * W)
    print("  WINNERS")
    print("=" * W)
    print(f"  Best 3X return:       {best_3x.label}  thresh={best_3x.thresh:.2f}  "
          f"{best_3x.ret:+.1f}%  DD:{best_3x.mdd:.1f}%  Win:{best_3x.winr:.1f}%")
    print(f"  Best 1X return:       {best_1x.label}  thresh={best_1x.thresh:.2f}  "
          f"{best_1x.ret:+.1f}%  DD:{best_1x.mdd:.1f}%  Win:{best_1x.winr:.1f}%")
    print(f"  Best 3X risk-adj:     {best_3x_adj.label}  thresh={best_3x_adj.thresh:.2f}  "
          f"{best_3x_adj.ret:+.1f}%  DD:{best_3x_adj.mdd:.1f}%  Win:{best_3x_adj.winr:.1f}%")
    print(f"  Best 1X risk-adj:     {best_1x_adj.label}  thresh={best_1x_adj.thresh:.2f}  "
          f"{best_1x_adj.ret:+.1f}%  DD:{best_1x_adj.mdd:.1f}%  Win:{best_1x_adj.winr:.1f}%")
    print(f"\n  Full results -> {csv_path}")
    print("=" * W)


if __name__ == "__main__":
    main()
