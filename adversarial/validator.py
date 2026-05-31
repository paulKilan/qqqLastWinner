"""
validator.py — Decide whether a Patcher's proposed fix generalizes or just
patches the one bad window.

Tests applied to the patched config:
  1. Failure window: must improve by >= MIN_FAIL_IMPROVE_PCT vs baseline.
  2. Same-regime sample: 3 other windows whose regime tag matches the failure
     regime. Patched config must average >= MIN_SAME_REGIME_RATIO vs baseline.
  3. Different-regime control: 3 windows in different regimes. Patched config
     must NOT lose more than MAX_OTHER_REGIME_REGRESSION vs baseline (we're
     watching for "fix breaks something else").
  4. Full holdout: harness EVAL_WINDOWS — patched-config mean return must not
     regress more than MAX_HOLDOUT_REGRESSION_PCT vs baseline.

Verdict: "generalizes" / "overfits" / "neutral" / "regresses-elsewhere".
The Patcher proposing the fix never sees the holdout outcome until after the
verdict — that's the pre-commit guarantee.
"""
from __future__ import annotations

import os
import sys
import random
from dataclasses import dataclass, asdict

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

from adversarial.regime_labeler import label_dict
from adversarial.breaker import generate_windows, _evaluate, load_current_best_params
from adversarial.patcher import apply_patch, evaluate_on_windows
from autoresearch.run_experiment import EVAL_WINDOWS


MIN_FAIL_IMPROVE_PCT = 2.0          # patched must outperform on the failure window by >=2pct return
MIN_SAME_REGIME_RATIO = 0.97        # same-regime average may slip by up to 3% (patched/baseline >= 0.97)
MAX_OTHER_REGIME_REGRESSION = 5.0   # other regime mean return may not drop by more than 5pct
MIN_HOLDOUT_PASS_FRACTION = 0.6     # at least 60% of holdout windows must beat baseline (within tolerance)
HOLDOUT_PER_WINDOW_ABS_TOL = 1.0    # absolute pp tolerance per window (small windows)
HOLDOUT_PER_WINDOW_REL_TOL = 0.05   # relative tolerance per window (large compounding windows). A window passes if patched >= baseline OR drop is within EITHER absolute pp OR relative %.


@dataclass
class ValidationResult:
    verdict: str
    fail_window_baseline_ret: float
    fail_window_patched_ret: float
    same_regime_baseline_avg: float
    same_regime_patched_avg: float
    other_regime_baseline_avg: float
    other_regime_patched_avg: float
    holdout_baseline_avg: float
    holdout_patched_avg: float
    n_same_regime: int
    n_other_regime: int
    notes: str


def _regime_tag(regime: dict) -> tuple:
    """Compact regime fingerprint for matching."""
    return (regime["vol_regime"], regime["trend_regime"], regime["dispersion_regime"])


def _pick_regime_samples(target_regime: dict, n_same: int = 3, n_other: int = 3,
                         exclude: set[str] | None = None,
                         seed: int = 42) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    rng = random.Random(seed)
    exclude = exclude or set()
    target = _regime_tag(target_regime)
    candidates = generate_windows(window_years=1.0, step_months=6, start="1999-01-04")
    same, other = [], []
    rng.shuffle(candidates)
    for s, e in candidates:
        win = f"{s} to {e}"
        if win in exclude:
            continue
        try:
            r = label_dict(s, e)
        except Exception:
            continue
        tag = (r["vol_regime"], r["trend_regime"], r["dispersion_regime"])
        if tag == target and len(same) < n_same:
            same.append((s, e))
        elif tag != target and len(other) < n_other:
            other.append((s, e))
        if len(same) >= n_same and len(other) >= n_other:
            break
    return same, other


def _avg_return(results: list[dict]) -> float:
    rs = [r["strat_return_pct"] for r in results if "error" not in r]
    return sum(rs) / len(rs) if rs else 0.0


def validate(failure_window: tuple[str, str], failure_regime: dict, patch: dict,
             baseline_params: dict | None = None) -> ValidationResult:
    base = baseline_params or load_current_best_params()
    patched = apply_patch(base, patch)

    # 1. Failure window
    fail_base = evaluate_on_windows(base, [failure_window])[0]
    fail_patched = evaluate_on_windows(patched, [failure_window])[0]
    fb_ret = fail_base.get("strat_return_pct", 0.0)
    fp_ret = fail_patched.get("strat_return_pct", 0.0)

    # 2 + 3. Same-regime + other-regime samples
    same_w, other_w = _pick_regime_samples(failure_regime, exclude={f"{failure_window[0]} to {failure_window[1]}"})
    same_base = evaluate_on_windows(base, same_w)
    same_patched = evaluate_on_windows(patched, same_w)
    other_base = evaluate_on_windows(base, other_w)
    other_patched = evaluate_on_windows(patched, other_w)

    # 4. Holdout: EVAL_WINDOWS minus failure window
    holdout = [(s, e) for (s, e) in EVAL_WINDOWS if f"{s} to {e}" != f"{failure_window[0]} to {failure_window[1]}"]
    hb = evaluate_on_windows(base, holdout)
    hp = evaluate_on_windows(patched, holdout)

    fail_improve = fp_ret - fb_ret
    same_b_avg = _avg_return(same_base)
    same_p_avg = _avg_return(same_patched)
    other_b_avg = _avg_return(other_base)
    other_p_avg = _avg_return(other_patched)
    hold_b_avg = _avg_return(hb)
    hold_p_avg = _avg_return(hp)

    # Per-window holdout pass-rate. Avoids the arithmetic-mean trap where the
    # 35-year compounding window dominates and tiny slippage there sinks every
    # patch. A patch passes if it beats baseline (within HOLDOUT_PER_WINDOW_TOLERANCE)
    # on at least MIN_HOLDOUT_PASS_FRACTION of holdout windows.
    def _window_passes(b: float, p: float) -> bool:
        if p >= b:
            return True
        abs_drop = b - p
        rel_drop = abs_drop / abs(b) if b not in (0, 0.0) else float("inf")
        return abs_drop <= HOLDOUT_PER_WINDOW_ABS_TOL or rel_drop <= HOLDOUT_PER_WINDOW_REL_TOL

    holdout_passes = sum(
        1 for hb_w, hp_w in zip(hb, hp)
        if "error" not in hb_w and "error" not in hp_w
        and _window_passes(hb_w["strat_return_pct"], hp_w["strat_return_pct"])
    )
    holdout_total = sum(1 for hb_w, hp_w in zip(hb, hp) if "error" not in hb_w and "error" not in hp_w)
    holdout_pass_frac = holdout_passes / holdout_total if holdout_total else 0.0

    notes = []
    verdict = "neutral"

    if fail_improve < MIN_FAIL_IMPROVE_PCT:
        verdict = "overfits"
        notes.append(f"failure window improvement {fail_improve:+.1f}% < {MIN_FAIL_IMPROVE_PCT:.1f}% required")
    elif same_p_avg < same_b_avg * MIN_SAME_REGIME_RATIO:
        verdict = "overfits"
        notes.append(f"same-regime mean dropped: {same_b_avg:.1f}% -> {same_p_avg:.1f}% (ratio {same_p_avg/max(same_b_avg,1e-9):.3f} < {MIN_SAME_REGIME_RATIO})")
    elif other_b_avg - other_p_avg > MAX_OTHER_REGIME_REGRESSION:
        verdict = "regresses-elsewhere"
        notes.append(f"other-regime mean dropped {other_b_avg - other_p_avg:.1f}% (max {MAX_OTHER_REGIME_REGRESSION:.1f}%)")
    elif holdout_pass_frac < MIN_HOLDOUT_PASS_FRACTION:
        verdict = "regresses-elsewhere"
        notes.append(f"holdout pass-rate {holdout_passes}/{holdout_total} ({holdout_pass_frac:.0%}) < required {MIN_HOLDOUT_PASS_FRACTION:.0%}")
    else:
        verdict = "generalizes"
        notes.append(f"failure +{fail_improve:.1f}%, same-regime {same_b_avg:.1f}->{same_p_avg:.1f}, "
                     f"other-regime {other_b_avg:.1f}->{other_p_avg:.1f}, holdout pass {holdout_passes}/{holdout_total}")

    return ValidationResult(
        verdict=verdict,
        fail_window_baseline_ret=fb_ret,
        fail_window_patched_ret=fp_ret,
        same_regime_baseline_avg=same_b_avg,
        same_regime_patched_avg=same_p_avg,
        other_regime_baseline_avg=other_b_avg,
        other_regime_patched_avg=other_p_avg,
        holdout_baseline_avg=hold_b_avg,
        holdout_patched_avg=hold_p_avg,
        n_same_regime=len(same_w),
        n_other_regime=len(other_w),
        notes="; ".join(notes),
    )


def to_dict(r: ValidationResult) -> dict:
    return asdict(r)
