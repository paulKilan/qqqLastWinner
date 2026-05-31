"""
preregistered_test.py — Train/holdout split, point-statistic test, and
Benjamini-Hochberg multiple-comparison correction.

Pre-registration contract:
  - Split point fixed by the LEDGER (see TRAIN_END below).
  - The Translator decides feature direction/horizon BEFORE seeing holdout
    data. The hypothesis dict carries `expected_sign` ("+1" / "-1") and
    `horizon_days` (e.g., 5, 21).
  - On train: estimate sign + magnitude (no decision).
  - On holdout: ONE statistic computed (Spearman rho), ONE p-value from a
    permutation test. No re-fitting, no parameter tuning, no re-tries.

Multiple-comparison correction: each routine cycle reports `k` (number of
hypotheses tested this batch). BH threshold per hypothesis is alpha * (rank/k)
where alpha=0.05. The Validator's `kept` decision uses this threshold, NOT
raw p < 0.05.
"""
from __future__ import annotations

import os
import numpy as np
import pandas as pd
from dataclasses import dataclass, asdict

from hypothesis_search.feature_translator import compile_spec, forward_returns, _load


# Pre-registered split — anything before TRAIN_END is train, after is holdout.
# Locked to a date well inside the available data so re-runs don't drift.
TRAIN_END = "2018-12-31"
ALPHA = 0.05
N_PERMUTATIONS = 1000


@dataclass
class TestResult:
    feature_spec: dict
    horizon_days: int
    expected_sign: int
    train_rho: float
    train_n: int
    holdout_rho: float
    holdout_n: int
    p_value: float
    kept: bool                     # set by apply_bh_correction across batch
    bh_threshold: float            # batch-level
    notes: str


def _spearman(x: pd.Series, y: pd.Series) -> tuple[float, int]:
    df = pd.concat([x, y], axis=1).dropna()
    if len(df) < 30:
        return float("nan"), len(df)
    rx = df.iloc[:, 0].rank()
    ry = df.iloc[:, 1].rank()
    return float(rx.corr(ry)), len(df)


def _permutation_p(x: pd.Series, y: pd.Series, observed: float, n: int = N_PERMUTATIONS,
                   seed: int = 7) -> float:
    df = pd.concat([x, y], axis=1).dropna()
    if len(df) < 30 or np.isnan(observed):
        return float("nan")
    rng = np.random.default_rng(seed)
    rx = df.iloc[:, 0].rank().values
    ry = df.iloc[:, 1].rank().values
    cnt = 0
    abs_obs = abs(observed)
    for _ in range(n):
        perm = rng.permutation(ry)
        rho = np.corrcoef(rx, perm)[0, 1]
        if abs(rho) >= abs_obs:
            cnt += 1
    return (cnt + 1) / (n + 1)


def test_one(feature_spec: dict, horizon_days: int, expected_sign: int) -> TestResult:
    feat = compile_spec(feature_spec)
    fwd = forward_returns(horizon_days)

    df = _load()
    cut = pd.to_datetime(TRAIN_END)
    train_mask = df.index <= cut
    holdout_mask = df.index > cut

    train_rho, train_n = _spearman(feat[train_mask], fwd[train_mask])
    hold_rho, hold_n = _spearman(feat[holdout_mask], fwd[holdout_mask])

    notes = []
    # Sign agreement check — if train sign disagrees with expected, flag (still
    # report holdout, but kept=False unless very strong holdout signal).
    if not np.isnan(train_rho) and np.sign(train_rho) != np.sign(expected_sign):
        notes.append(f"train rho sign {train_rho:+.3f} disagrees with expected {expected_sign:+d}")

    p_value = _permutation_p(feat[holdout_mask], fwd[holdout_mask], hold_rho)

    return TestResult(
        feature_spec=feature_spec,
        horizon_days=horizon_days,
        expected_sign=expected_sign,
        train_rho=round(train_rho, 4) if not np.isnan(train_rho) else float("nan"),
        train_n=train_n,
        holdout_rho=round(hold_rho, 4) if not np.isnan(hold_rho) else float("nan"),
        holdout_n=hold_n,
        p_value=round(p_value, 4) if not np.isnan(p_value) else float("nan"),
        kept=False,                 # decided after BH
        bh_threshold=float("nan"),
        notes="; ".join(notes),
    )


def apply_bh_correction(results: list[TestResult], alpha: float = ALPHA) -> list[TestResult]:
    """Benjamini-Hochberg: sort by p, threshold for rank i is alpha * i/k."""
    k = len(results)
    if k == 0:
        return results
    valid = [(i, r) for i, r in enumerate(results) if not np.isnan(r.p_value)]
    valid.sort(key=lambda t: t[1].p_value)
    largest_kept_rank = 0
    for rank, (idx, r) in enumerate(valid, start=1):
        bh = alpha * rank / k
        r.bh_threshold = round(bh, 5)
        if r.p_value <= bh:
            largest_kept_rank = rank
    # All hypotheses with rank <= largest_kept_rank are "kept", but ALSO require
    # train/holdout sign agreement with expected_sign.
    for rank, (idx, r) in enumerate(valid, start=1):
        if rank <= largest_kept_rank:
            sign_ok = (np.sign(r.holdout_rho) == np.sign(r.expected_sign)
                       and np.sign(r.train_rho) == np.sign(r.expected_sign))
            r.kept = bool(sign_ok)
            if not sign_ok:
                r.notes = (r.notes + ("; " if r.notes else "") +
                           "BH-significant but sign mismatch").strip()
    return results


def to_dict(r: TestResult) -> dict:
    return asdict(r)
