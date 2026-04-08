"""
webapp/signals.py — Compute Iter31 signal breakdown for a list of tickers.
Called by app.py; can also be run standalone for debugging.
"""

import os
import sys
import json
import time
import urllib.request
from datetime import datetime, date

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

import pandas as pd
import numpy as np

AUTORESEARCH_DIR = os.path.join(ROOT_DIR, "autoresearch")
TICKERS = ["QQQ", "SPY", "NVDA", "TSLA", "GOOGL"]

PERIOD1 = 631152000  # 1990-01-01


# ── Data refresh ──────────────────────────────────────────────────────────────

def _fetch_ohlcv(ticker: str) -> pd.DataFrame:
    period2 = int((datetime.now()).timestamp()) + 86400
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
        f"?period1={PERIOD1}&period2={period2}&interval=1d&events=adjsplit"
    )
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept": "application/json",
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode())

    result = data["chart"]["result"][0]
    ts     = result["timestamp"]
    quotes = result["indicators"]["quote"][0]
    adjc   = result["indicators"].get("adjclose", [{}])[0].get("adjclose", None)

    dates = pd.to_datetime(ts, unit="s", utc=True).tz_convert(None).normalize()
    df = pd.DataFrame({
        "open": quotes["open"], "high": quotes["high"],
        "low":  quotes["low"],  "close": quotes["close"],
        "volume": quotes["volume"],
    }, index=dates)
    df.index.name = "Date"

    if adjc is not None:
        ratio = pd.Series(adjc, index=dates) / df["close"]
        for col in ["open", "high", "low", "close"]:
            df[f"{col}_adj"] = (df[col] * ratio).round(6)
    else:
        for col in ["open", "high", "low", "close"]:
            df[f"{col}_adj"] = df[col].round(6)

    return df[["open_adj", "high_adj", "low_adj", "close_adj", "volume"]].dropna(subset=["close_adj"])


def refresh_ticker(ticker: str) -> bool:
    """Fetch latest OHLCV for ticker. Returns True on success."""
    path = os.path.join(AUTORESEARCH_DIR, f"{ticker.lower()}_ohlcv.csv")
    try:
        df = _fetch_ohlcv(ticker)
        df.to_csv(path)
        return True
    except Exception:
        return False


# ── Signal computation ────────────────────────────────────────────────────────

def _rsi(series: pd.Series, period: int) -> pd.Series:
    delta = series.diff()
    gain  = delta.where(delta > 0, 0.0).rolling(period).mean()
    loss  = (-delta.where(delta < 0, 0.0)).rolling(period).mean()
    return (100 - 100 / (1 + gain / loss.replace(0, np.nan))).fillna(50)


def compute_signal(ticker: str) -> dict:
    from autoresearch.experimental_strategy import _load_ohlcv, _compute_mfi_cmf, _compute_adx, _OHLCV_CACHE
    from autoresearch.prepare import load_prices

    os.environ["STRATEGY_TICKER"] = ticker.upper()
    _OHLCV_CACHE.clear()

    prices = load_prices(ticker)
    close  = prices["close"].astype(float)

    # ── Indicators ────────────────────────────────────────────────────────────
    sma50   = close.rolling(50).mean()
    sma200  = close.rolling(200).mean()
    sma27   = close.rolling(27).mean()
    ema5    = close.ewm(span=5,  adjust=False).mean()
    ema8    = close.ewm(span=8,  adjust=False).mean()
    ema13   = close.ewm(span=13, adjust=False).mean()
    ema17   = close.ewm(span=17, adjust=False).mean()
    ema34   = close.ewm(span=34, adjust=False).mean()
    roll252 = close.rolling(252).max()

    rsi2  = _rsi(close, 2)
    rsi3  = _rsi(close, 3)
    pv    = close / sma200.replace(0, np.nan)
    mom5  = close / close.shift(5)  - 1
    mom20 = close / close.shift(20) - 1
    dd_yr = (close - roll252) / roll252 * 100

    ohlcv = _load_ohlcv(ticker)
    mfi, cmf = _compute_mfi_cmf(ohlcv, close.index)
    adx, plus_di, minus_di = _compute_adx(ohlcv, close.index)

    # ── Regime ────────────────────────────────────────────────────────────────
    in_bull      = sma50 > sma200
    genuine_bear = ~in_bull & (dd_yr < -15)
    bear_short   = genuine_bear & (ema13 < ema34) & (mom20 <= 0) & (cmf <= 0) & (rsi3 < 85)
    shallow_rec  = (~in_bull) & (~genuine_bear) & (ema5 > ema8) & (mom5 > 0)

    def g(s): return float(s.iloc[-1])

    # ── Sub-strategy votes ────────────────────────────────────────────────────
    strong_up = bool((g(adx) > 25) and (g(plus_di) > g(minus_di)))
    rsi3_thr  = 85 if g(pv) >= 1.15 else 90

    # Sub-A
    if not g(in_bull):
        subA = -1 if g(bear_short) else 0
        subA_reason = "Not in bull — bear rules"
    elif g(rsi3) > rsi3_thr:
        subA = 0
        subA_reason = f"RSI3={g(rsi3):.1f} > {rsi3_thr} — overbought exit"
    else:
        subA = 1
        subA_reason = f"RSI3={g(rsi3):.1f} ≤ {rsi3_thr} — no exit signal"

    # Sub-B / Sub-D
    subB = 1 if g(in_bull) else (-1 if g(bear_short) else 0)
    subB_reason = "SMA50 > SMA200" if g(in_bull) else "Not in bull"
    subD, subD_reason = subB, subB_reason

    # Sub-C
    recent_rsi2 = (rsi2.iloc[-12:-1] < 10) & in_bull.iloc[-12:-1]
    recent_mom5 = (mom5.iloc[-11:-1] < -0.05) & in_bull.iloc[-11:-1]
    subC_hold   = bool(recent_rsi2.any() or recent_mom5.any())
    if not g(in_bull):
        subC = -1 if g(bear_short) else 0
        subC_reason = "Not in bull"
    elif subC_hold:
        subC = 1
        trigger = "RSI2<10" if recent_rsi2.any() else "Mom5<-5%"
        subC_reason = f"Hold active ({trigger} triggered within 11 days)"
    else:
        subC = 0
        subC_reason = "No recent dip trigger"

    # Sub-E
    if g(in_bull):
        if g(pv) >= 1.10:
            subE = 1 if g(close) > g(sma27) else 0
            subE_reason = f"pv={g(pv):.3f}≥1.10 → SMA27 branch; close {'>' if subE else '≤'} SMA27"
        else:
            subE = 1 if g(close) > g(ema17) else 0
            subE_reason = f"pv={g(pv):.3f}<1.10 → EMA17 branch; close {'>' if subE else '≤'} EMA17"
    else:
        subE = -1 if g(bear_short) else 0
        subE_reason = "Not in bull"

    # Sub-F
    MFI_OB = 63
    if g(in_bull):
        if g(pv) < 1.06:
            subF = 1
            subF_reason = f"pv={g(pv):.3f}<1.06 → MFI bypass (near SMA200 support)"
        else:
            mfi_ok = g(mfi) <= MFI_OB
            subF = 1 if mfi_ok else 0
            subF_reason = f"pv={g(pv):.3f}≥1.06 → MFI={g(mfi):.1f} {'≤63 OK' if mfi_ok else '>63 overbought exit'}"
    else:
        subF = -1 if g(bear_short) else 0
        subF_reason = "Not in bull"

    votes = [subA, subB, subC, subD, subE, subF]
    vote_long  = sum(1 for v in votes if v == 1)
    vote_short = sum(1 for v in votes if v == -1)

    if vote_long >= 5:
        final = "LONG"
    elif vote_short >= 2:
        final = "SHORT"
    else:
        final = "CASH"

    prev_close = float(close.iloc[-2]) if len(close) > 1 else g(close)
    day_chg    = (g(close) - prev_close) / prev_close * 100

    return {
        "ticker":   ticker,
        "as_of":    str(close.index[-1].date()),
        "close":    round(g(close), 2),
        "day_chg":  round(day_chg, 2),
        "final":    final,
        # Regime
        "in_bull":       bool(g(in_bull)),
        "genuine_bear":  bool(g(genuine_bear)),
        "bear_short":    bool(g(bear_short)),
        "shallow_rec":   bool(g(shallow_rec)),
        # Key indicators
        "sma50":     round(g(sma50), 2),
        "sma200":    round(g(sma200), 2),
        "pv":        round(g(pv), 4),
        "dd_yr":     round(g(dd_yr), 2),
        "rsi2":      round(g(rsi2), 1),
        "rsi3":      round(g(rsi3), 1),
        "mfi":       round(g(mfi), 1),
        "cmf":       round(g(cmf), 4),
        "adx":       round(g(adx), 1),
        "plus_di":   round(g(plus_di), 1),
        "minus_di":  round(g(minus_di), 1),
        "mom5":      round(g(mom5) * 100, 2),
        "mom20":     round(g(mom20) * 100, 2),
        "ema13_gt_ema34": bool(g(ema13) > g(ema34)),
        "strong_up": strong_up,
        "rsi3_thr":  rsi3_thr,
        # Votes
        "votes": {
            "A": {"vote": subA, "reason": subA_reason, "label": "Adaptive Exit"},
            "B": {"vote": subB, "reason": subB_reason, "label": "Always Long"},
            "C": {"vote": subC, "reason": subC_reason, "label": "Dip Buyer"},
            "D": {"vote": subD, "reason": subD_reason, "label": "Always Long #2"},
            "E": {"vote": subE, "reason": subE_reason, "label": "Adaptive MA"},
            "F": {"vote": subF, "reason": subF_reason, "label": "MFI / Volume"},
        },
        "vote_long":  vote_long,
        "vote_short": vote_short,
    }


def get_all_signals(refresh_data: bool = False) -> dict:
    if refresh_data:
        for ticker in TICKERS:
            refresh_ticker(ticker)
            time.sleep(0.5)

    results = {}
    for ticker in TICKERS:
        try:
            results[ticker] = compute_signal(ticker)
        except Exception as e:
            results[ticker] = {"ticker": ticker, "error": str(e), "final": "ERROR"}

    return {
        "tickers": results,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
