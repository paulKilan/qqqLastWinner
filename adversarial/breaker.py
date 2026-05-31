"""
breaker.py — Find time windows where the current best harness strategy
underperforms QQQ buy-and-hold by the largest margin.

Two-stage scan:
  1. Fixed-length sliding windows (default 1 year, 6mo step). Score each by
     `strategy_return - qqq_return`. Lowest = worst.
  2. Top-N worst windows are tagged with regime labels for the Patcher.

The Breaker doesn't "reason" — it produces a ranked list of candidate failure
windows + their regime descriptors. The Claude routine consumes that and picks
the one to attack this cycle (preferring windows whose regime hasn't been
attacked recently).
"""
from __future__ import annotations

import os
import sys
import json
from dataclasses import dataclass

import pandas as pd

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

from adversarial.regime_labeler import label_dict
from autoresearch.run_experiment import evaluate_window, load_strategy
from autoresearch.harness.parametric_strategy import ITER31_DEFAULTS


HARNESS_STATE = os.path.join(ROOT_DIR, "autoresearch", "harness", "state.json")
HARNESS_PARAMS_FILE = os.path.join(ROOT_DIR, "autoresearch", "harness", "current_params.json")


def load_current_best_params() -> dict:
    """Read the harness's current best params; fall back to Iter31 if missing."""
    if os.path.exists(HARNESS_STATE):
        try:
            s = json.load(open(HARNESS_STATE))
            p = s.get("params")
            if p:
                return p
        except Exception:
            pass
    return dict(ITER31_DEFAULTS)


def write_active_params(params: dict):
    """Stage the params for ParametricStrategy to read on its next instantiation."""
    os.environ["HARNESS_PARAMS_FILE"] = HARNESS_PARAMS_FILE
    tmp = HARNESS_PARAMS_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(params, f, indent=2)
    os.replace(tmp, HARNESS_PARAMS_FILE)


def _evaluate(start: str, end: str) -> dict:
    """Run ParametricStrategy on one window. Returns metrics dict, or {error:...}."""
    # Force fresh module so it re-reads HARNESS_PARAMS_FILE
    if "autoresearch.harness.parametric_strategy" in sys.modules:
        del sys.modules["autoresearch.harness.parametric_strategy"]
    from autoresearch.harness.parametric_strategy import ParametricStrategy
    try:
        return evaluate_window(ParametricStrategy(), start, end, ticker="QQQ")
    except Exception as e:
        return {"window": f"{start} to {end}", "error": str(e)}


@dataclass
class FailureWindow:
    start: str
    end: str
    strat_return_pct: float
    qqq_return_pct: float
    underperf_pct: float           # strat - qqq (more negative = worse)
    sharpe: float
    max_dd_pct: float
    trades_per_year: float
    regime: dict


def generate_windows(window_years: float = 1.0, step_months: int = 6,
                     start: str = "1999-01-04", end: str | None = None) -> list[tuple[str, str]]:
    end_dt = pd.to_datetime(end) if end else pd.Timestamp.today()
    cur = pd.to_datetime(start)
    out = []
    width = pd.DateOffset(years=int(window_years), months=int((window_years % 1) * 12))
    step = pd.DateOffset(months=step_months)
    while cur + width <= end_dt:
        out.append((cur.strftime("%Y-%m-%d"), (cur + width).strftime("%Y-%m-%d")))
        cur = cur + step
    return out


def find_failures(params: dict, top_n: int = 5,
                  window_years: float = 1.0, step_months: int = 6,
                  exclude: set[str] | None = None) -> list[FailureWindow]:
    """Scan all sliding windows, return the top-N most-underperforming."""
    write_active_params(params)
    windows = generate_windows(window_years, step_months)
    exclude = exclude or set()

    rows = []
    for s, e in windows:
        win_label = f"{s} to {e}"
        if win_label in exclude:
            continue
        r = _evaluate(s, e)
        if "error" in r:
            continue
        rows.append({
            "start": s, "end": e,
            "strat_return_pct": r["strat_return_pct"],
            "qqq_return_pct": r["qqq_return_pct"],
            "underperf_pct": r["strat_return_pct"] - r["qqq_return_pct"],
            "sharpe": r["sharpe"],
            "max_dd_pct": r["max_drawdown_pct"],
            "trades_per_year": r["trades_per_year"],
        })

    rows.sort(key=lambda x: x["underperf_pct"])
    failures = []
    for r in rows[:top_n]:
        regime = label_dict(r["start"], r["end"])
        failures.append(FailureWindow(**r, regime=regime))
    return failures


def to_jsonable(failures: list[FailureWindow]) -> list[dict]:
    return [{
        "start": f.start, "end": f.end,
        "strat_return_pct": f.strat_return_pct,
        "qqq_return_pct": f.qqq_return_pct,
        "underperf_pct": round(f.underperf_pct, 2),
        "sharpe": f.sharpe,
        "max_dd_pct": f.max_dd_pct,
        "trades_per_year": f.trades_per_year,
        "regime": f.regime,
    } for f in failures]


if __name__ == "__main__":
    p = load_current_best_params()
    fs = find_failures(p, top_n=5, window_years=1.0, step_months=6)
    print(json.dumps(to_jsonable(fs), indent=2))
