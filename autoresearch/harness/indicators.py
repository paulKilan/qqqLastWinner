"""
indicators.py — Technical-indicator helpers for the parametric ensemble.

All functions take an OHLCV DataFrame (columns: open/high/low/close/volume,
plus *_adj variants) plus the window's date index, and return reindexed
Series aligned to that index. No lookahead bias.

Indicators (selected from the literature for momentum/trend/dip-buying):
  - MACD          (Moving Average Convergence Divergence)
  - KDJ / Stoch   (K, D, J — momentum oscillator)
  - Bollinger     (mid/upper/lower + bandwidth)
  - Williams %R   (overbought/oversold faster than RSI)
  - OBV           (on-balance volume; volume-confirmed trend)
  - Donchian      (high/low channel for breakout detection)
  - Aroon         (Up/Down — pure trend identifier)
"""

import pandas as pd
import numpy as np


def _close(ohlcv):
    return ohlcv["close_adj"].astype(float)


def _high(ohlcv):
    return ohlcv["high_adj"].astype(float)


def _low(ohlcv):
    return ohlcv["low_adj"].astype(float)


def _volume(ohlcv):
    return ohlcv["volume"].astype(float)


def macd(ohlcv, idx, fast=12, slow=26, signal=9):
    """MACD line, signal line, histogram. Computed on full history then reindexed."""
    c = _close(ohlcv)
    ema_f = c.ewm(span=fast, adjust=False).mean()
    ema_s = c.ewm(span=slow, adjust=False).mean()
    line = ema_f - ema_s
    sig = line.ewm(span=signal, adjust=False).mean()
    hist = line - sig
    return (
        line.reindex(idx, method="ffill").fillna(0),
        sig.reindex(idx, method="ffill").fillna(0),
        hist.reindex(idx, method="ffill").fillna(0),
    )


def kdj(ohlcv, idx, period=9, k_smooth=3, d_smooth=3):
    """KDJ stochastic. Returns K, D, J. J = 3K - 2D, can extend beyond [0,100]."""
    h = _high(ohlcv)
    l = _low(ohlcv)
    c = _close(ohlcv)
    ll = l.rolling(period).min()
    hh = h.rolling(period).max()
    rsv = ((c - ll) / (hh - ll).replace(0, np.nan) * 100).fillna(50)
    K = rsv.ewm(alpha=1.0 / k_smooth, adjust=False).mean()
    D = K.ewm(alpha=1.0 / d_smooth, adjust=False).mean()
    J = 3 * K - 2 * D
    return (
        K.reindex(idx, method="ffill").fillna(50),
        D.reindex(idx, method="ffill").fillna(50),
        J.reindex(idx, method="ffill").fillna(50),
    )


def bollinger(ohlcv, idx, period=20, n_std=2.0):
    """Bollinger middle, upper, lower, bandwidth (= (upper-lower)/middle)."""
    c = _close(ohlcv)
    mid = c.rolling(period).mean()
    sd = c.rolling(period).std()
    up = mid + n_std * sd
    lo = mid - n_std * sd
    bw = (up - lo) / mid.replace(0, np.nan)
    return (
        mid.reindex(idx, method="ffill"),
        up.reindex(idx, method="ffill"),
        lo.reindex(idx, method="ffill"),
        bw.reindex(idx, method="ffill").fillna(0),
    )


def williams_r(ohlcv, idx, period=14):
    """Williams %R in [-100, 0]. -100 = oversold, 0 = overbought."""
    h = _high(ohlcv)
    l = _low(ohlcv)
    c = _close(ohlcv)
    hh = h.rolling(period).max()
    ll = l.rolling(period).min()
    wr = ((hh - c) / (hh - ll).replace(0, np.nan) * -100).fillna(-50)
    return wr.reindex(idx, method="ffill").fillna(-50)


def obv(ohlcv, idx, sma_period=20):
    """On-balance volume + its SMA. Long-confirmation when OBV > OBV_SMA."""
    c = _close(ohlcv)
    v = _volume(ohlcv)
    direction = np.sign(c.diff().fillna(0))
    obv_series = (direction * v).cumsum()
    obv_sma = obv_series.rolling(sma_period).mean()
    return (
        obv_series.reindex(idx, method="ffill").fillna(0),
        obv_sma.reindex(idx, method="ffill").fillna(0),
    )


def donchian(ohlcv, idx, period=20):
    """Donchian channel high/low/midpoint over `period` days."""
    h = _high(ohlcv)
    l = _low(ohlcv)
    hi = h.rolling(period).max()
    lo = l.rolling(period).min()
    mid = (hi + lo) / 2.0
    return (
        hi.reindex(idx, method="ffill"),
        lo.reindex(idx, method="ffill"),
        mid.reindex(idx, method="ffill"),
    )


def aroon(ohlcv, idx, period=25):
    """Aroon Up / Down in [0, 100]. Up=100 means new high today, etc."""
    h = _high(ohlcv)
    l = _low(ohlcv)

    # rolling argmax position (0 = oldest, period = newest within window)
    def _pos_high(window):
        return float(np.argmax(window))

    def _pos_low(window):
        return float(np.argmin(window))

    up = h.rolling(period + 1).apply(_pos_high, raw=True) / period * 100.0
    dn = l.rolling(period + 1).apply(_pos_low, raw=True) / period * 100.0
    return (
        up.reindex(idx, method="ffill").fillna(50),
        dn.reindex(idx, method="ffill").fillna(50),
    )
