"""
feature_translator.py — Compile a feature_spec dict (produced by the LLM
extraction step) into an actual numeric series aligned to QQQ trading days.

Supported spec shapes (kept narrow on purpose — extend as needed):

  {"kind": "rolling", "source": "close", "op": "pct_change", "window": 20}
  {"kind": "rolling", "source": "close", "op": "log_return", "window": 5}
  {"kind": "rolling", "source": "close", "op": "zscore", "window": 60}
  {"kind": "rolling", "source": "volume", "op": "pct_of_mean", "window": 20}
  {"kind": "ratio", "numer": {...}, "denom": {...}}    # nested specs
  {"kind": "diff", "left": {...}, "right": {...}}
  {"kind": "rsi", "source": "close", "period": 14}
  {"kind": "vol_of_vol", "window": 20, "outer_window": 60}

Anything else returns NotImplemented and the cycle records 'spec-unsupported'
in the ledger so the LLM tries a different translation next time.
"""
from __future__ import annotations

import os
import numpy as np
import pandas as pd


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OHLCV = os.path.join(ROOT, "autoresearch", "qqq_ohlcv.csv")

_DF: pd.DataFrame | None = None


def _load() -> pd.DataFrame:
    global _DF
    if _DF is None:
        df = pd.read_csv(OHLCV, index_col=0, parse_dates=True)
        df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
        _DF = df.sort_index()
    return _DF


def _series(source: str) -> pd.Series:
    df = _load()
    if source in df.columns:
        return df[source].astype(float)
    if source == "close":
        return (df["close_adj"] if "close_adj" in df.columns else df["close"]).astype(float)
    if source == "open":
        return (df["open_adj"] if "open_adj" in df.columns else df["open"]).astype(float)
    if source == "high":
        return (df["high_adj"] if "high_adj" in df.columns else df["high"]).astype(float)
    if source == "low":
        return (df["low_adj"] if "low_adj" in df.columns else df["low"]).astype(float)
    if source == "volume":
        return df["volume"].astype(float)
    raise ValueError(f"Unknown source: {source}")


def compile_spec(spec: dict) -> pd.Series:
    kind = spec["kind"]

    if kind == "rolling":
        s = _series(spec["source"])
        op = spec["op"]
        w = int(spec["window"])
        if op == "pct_change":
            return s.pct_change(w)
        if op == "log_return":
            return np.log(s / s.shift(w))
        if op == "zscore":
            return (s - s.rolling(w).mean()) / s.rolling(w).std()
        if op == "pct_of_mean":
            return s / s.rolling(w).mean() - 1
        raise ValueError(f"Unknown rolling op: {op}")

    if kind == "ratio":
        return compile_spec(spec["numer"]) / compile_spec(spec["denom"]).replace(0, np.nan)

    if kind == "diff":
        return compile_spec(spec["left"]) - compile_spec(spec["right"])

    if kind == "rsi":
        s = _series(spec.get("source", "close"))
        p = int(spec.get("period", 14))
        delta = s.diff()
        gain = delta.where(delta > 0, 0.0).rolling(p).mean()
        loss = (-delta.where(delta < 0, 0.0)).rolling(p).mean()
        return (100 - 100 / (1 + gain / loss.replace(0, np.nan))).fillna(50)

    if kind == "vol_of_vol":
        w = int(spec["window"])
        ow = int(spec["outer_window"])
        rets = _series("close").pct_change()
        rv = rets.rolling(w).std() * np.sqrt(252)
        return rv.rolling(ow).std()

    raise NotImplementedError(f"spec.kind={kind} not supported yet")


def forward_returns(horizon_days: int) -> pd.Series:
    s = _series("close")
    return s.shift(-horizon_days) / s - 1
