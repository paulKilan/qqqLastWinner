"""
regime_labeler.py — Tag time windows with vol / rate / dispersion / trend regimes.

Used by the Breaker to articulate *why* a window broke the strategy, not just
that it did. Every label is derived from price/volume data already in the repo
(autoresearch/qqq_ohlcv.csv). Rates regime is approximated from QQQ duration
sensitivity since we don't have a ^TNX series committed; you can replace with
a real series later.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, asdict
from typing import Dict

import numpy as np
import pandas as pd


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OHLCV_PATH = os.path.join(ROOT_DIR, "autoresearch", "qqq_ohlcv.csv")


# ── Thresholds (calibrated on 1990-2026 QQQ; quintile-style cutpoints) ───────
VOL_LOW_PCTL = 0.33
VOL_HIGH_PCTL = 0.67
TREND_BULL_THR = 0.05      # 6m trailing return %
TREND_BEAR_THR = -0.05
DISPERSION_HIGH_PCTL = 0.67  # cross-sectional volatility proxy from intraday range


_OHLCV: pd.DataFrame | None = None


def _load() -> pd.DataFrame:
    global _OHLCV
    if _OHLCV is None:
        df = pd.read_csv(OHLCV_PATH, index_col=0, parse_dates=True)
        df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
        _OHLCV = df.sort_index()
    return _OHLCV


@dataclass
class RegimeLabels:
    window: str
    start: str
    end: str
    n_days: int
    realized_vol_ann: float        # annualized stdev of daily returns (%)
    vol_regime: str                # "low" | "mid" | "high"
    trailing_return_pct: float
    trend_regime: str              # "bull" | "sideways" | "bear"
    drawdown_pct: float            # max DD inside window (%)
    intraday_dispersion: float     # mean (high-low)/close as cross-sec proxy
    dispersion_regime: str         # "compressed" | "normal" | "elevated"
    rate_proxy_drift: float        # heuristic: window QQQ vs 200d-MA slope
    rate_regime: str               # "easing" | "neutral" | "tightening" (heuristic)

    def summary(self) -> str:
        return (
            f"vol={self.vol_regime}({self.realized_vol_ann:.0f}%) "
            f"trend={self.trend_regime}({self.trailing_return_pct:+.1%}) "
            f"dispersion={self.dispersion_regime}({self.intraday_dispersion:.2%}) "
            f"rate={self.rate_regime}"
        )


def _slice(start: str, end: str) -> pd.DataFrame:
    df = _load()
    s = pd.to_datetime(start)
    e = pd.to_datetime(end)
    return df.loc[(df.index >= s) & (df.index <= e)]


def _full_distribution_thresholds() -> Dict[str, float]:
    df = _load()
    close = df["close_adj"].astype(float) if "close_adj" in df.columns else df["close"].astype(float)
    rets = close.pct_change()
    realized = rets.rolling(63).std() * np.sqrt(252) * 100
    range_ = (df["high_adj"] - df["low_adj"]) / df["close_adj"] if "close_adj" in df.columns else (df["high"] - df["low"]) / df["close"]
    return {
        "vol_low": float(np.nanquantile(realized, VOL_LOW_PCTL)),
        "vol_high": float(np.nanquantile(realized, VOL_HIGH_PCTL)),
        "disp_high": float(np.nanquantile(range_, DISPERSION_HIGH_PCTL)),
        "disp_mid_low": float(np.nanquantile(range_, 0.33)),
    }


def label_window(start: str, end: str) -> RegimeLabels:
    """Compute all four regime tags for a single window."""
    df = _slice(start, end)
    if df.empty:
        raise ValueError(f"No data in window {start}..{end}")

    close = (df["close_adj"] if "close_adj" in df.columns else df["close"]).astype(float)
    high = (df["high_adj"] if "high_adj" in df.columns else df["high"]).astype(float)
    low = (df["low_adj"] if "low_adj" in df.columns else df["low"]).astype(float)

    rets = close.pct_change().dropna()
    realized_vol = float(rets.std() * np.sqrt(252) * 100) if len(rets) > 1 else 0.0

    trailing_return = float(close.iloc[-1] / close.iloc[0] - 1) if len(close) > 1 else 0.0

    running_max = close.expanding().max()
    drawdown = float(((close - running_max) / running_max).min() * 100) if len(close) > 1 else 0.0

    intraday_dispersion = float(((high - low) / close).mean())

    full = _load()
    full_close = (full["close_adj"] if "close_adj" in full.columns else full["close"]).astype(float)
    sma200 = full_close.rolling(200).mean()
    sma_window = sma200.reindex(close.index).dropna()
    if len(sma_window) > 20:
        slope = float((sma_window.iloc[-1] - sma_window.iloc[0]) / sma_window.iloc[0])
    else:
        slope = 0.0

    th = _full_distribution_thresholds()
    if realized_vol < th["vol_low"]:
        vol_regime = "low"
    elif realized_vol > th["vol_high"]:
        vol_regime = "high"
    else:
        vol_regime = "mid"

    if trailing_return > TREND_BULL_THR:
        trend_regime = "bull"
    elif trailing_return < TREND_BEAR_THR:
        trend_regime = "bear"
    else:
        trend_regime = "sideways"

    if intraday_dispersion > th["disp_high"]:
        dispersion_regime = "elevated"
    elif intraday_dispersion < th["disp_mid_low"]:
        dispersion_regime = "compressed"
    else:
        dispersion_regime = "normal"

    if slope > 0.05:
        rate_regime = "easing"      # rising prices alongside SMA200 lift = supportive
    elif slope < -0.05:
        rate_regime = "tightening"
    else:
        rate_regime = "neutral"

    return RegimeLabels(
        window=f"{start} to {end}",
        start=start, end=end,
        n_days=len(df),
        realized_vol_ann=round(realized_vol, 2),
        vol_regime=vol_regime,
        trailing_return_pct=round(trailing_return, 4),
        trend_regime=trend_regime,
        drawdown_pct=round(drawdown, 2),
        intraday_dispersion=round(intraday_dispersion, 4),
        dispersion_regime=dispersion_regime,
        rate_proxy_drift=round(slope, 4),
        rate_regime=rate_regime,
    )


def label_dict(start: str, end: str) -> dict:
    return asdict(label_window(start, end))


if __name__ == "__main__":
    import json
    for s, e in [
        ("2000-03-01", "2002-10-31"),  # dot-com crash
        ("2008-09-01", "2009-03-31"),  # GFC
        ("2020-02-01", "2020-04-30"),  # COVID
        ("2022-01-01", "2022-12-31"),  # rate-hike bear
        ("2023-01-03", "2024-12-31"),
    ]:
        print(json.dumps(label_dict(s, e), indent=2))
        print("---")
