"""
experimental_strategy.py — CleanBear + RSI2 Dip-Entry Strategy

Iteration 17: CleanBear with RSI2(10) Hold-10 Days for Frequency

Key learnings from extensive debug testing (fulldata/selective/momentum/slope/adx tests):
1. CRITICAL FIX: Use self._data for SMA50/200 — full QQQ history since 1999.
   This eliminates the 200-day warmup bias (missing all of 2013's +37% rally).
2. AlwaysLong in bull (SMA50>SMA200) achieves 0.84x ratio — better than any bear-period
   strategy in pure-bull windows (EMA whipsaws cost money).
3. "Genuine bear" filter (SMA50<SMA200 AND 1yr drawdown > 15%) avoids false shorts
   during shallow corrections; only enters shorts in real sustained bears (2022: -33%).
4. EMA13/34 timing within bear: short when EMA13<EMA34, cash on bounces.
5. RSI(3)<10 extreme oversold → force long (bottom-fishing at extreme lows).
6. RSI2<10 hold-10-days in bull: buy dips, hold 10 days, then cash until next dip.
   Generates 12 trades/year (meets frequency requirement) while maintaining strong ratio.

Strategy logic:
  BULL (SMA50>SMA200):
    - RSI2<10: enter LONG, hold for 10 trading days (dip-buying)
    - Otherwise: CASH (don't chase overbought markets)

  BEAR (SMA50<SMA200 + 1yr DD>15%):
    - EMA13<EMA34: SHORT (confirmed bear trend)
    - EMA13>=EMA34: CASH (bear bounce, don't fight recovery)
    - RSI3<10: LONG override (extreme oversold at bear bottoms)

  SHALLOW BEAR (SMA50<SMA200 but 1yr DD<15%):
    - CASH (brief dip, don't fight bull market)

Performance (debug backtests, 5 windows 2013-2024):
  Full 2013-24: 0.99x | 2013-18: 0.81x | 2019-24: 1.22x | 2020-22: 3.95x | 2023-24: 0.78x
  MinRatio: 0.78x | AvgTrades/Yr: 12 (meets 12-120 requirement)
"""

import pandas as pd
import numpy as np
from strategy.base_strategy import BaseStrategy


class ExperimentalStrategy(BaseStrategy):
    """
    RSI2 dip-entry bull strategy + genuine bear shorts.

    Bull mode: only long after RSI(2) dip below 10, hold 10 days, then cash.
    Bear mode: EMA13/34 timing for short entries in confirmed (DD>15%) bears.
    RSI(3) < 10: emergency long at extreme oversold anywhere.
    Uses full QQQ history (self._data) for SMA indicators — no warmup bias.
    """

    def __init__(self):
        super().__init__(allow_short=True)

    def _calculate_positions(self, data: pd.DataFrame, contextData=None) -> pd.DataFrame:
        result_df = self._make_result_df(data)

        # ── Full-history indicators (NO warmup bias) ─────────────────────────
        full = self._data["close"].astype(float)
        sma50  = full.rolling(50).mean().reindex(data.index)
        sma200 = full.rolling(200).mean().reindex(data.index)
        ema13  = full.ewm(span=13, adjust=False).mean().reindex(data.index)
        ema34  = full.ewm(span=34, adjust=False).mean().reindex(data.index)
        roll252_max = full.rolling(252).max().reindex(data.index)

        # ── Window-period indicators ──────────────────────────────────────────
        close = data["close"].astype(float)
        dd_yr = (close - roll252_max) / roll252_max * 100  # 1-yr drawdown %

        # RSI(2) — very sensitive, swings to extremes on every 2-day pullback
        delta2 = close.diff()
        gain2 = delta2.where(delta2 > 0, 0.0).rolling(2).mean()
        loss2 = (-delta2.where(delta2 < 0, 0.0)).rolling(2).mean()
        rsi2 = (100 - 100 / (1 + gain2 / loss2.replace(0, np.nan))).fillna(50)

        # RSI(3) — for extreme oversold detection
        gain3 = delta2.where(delta2 > 0, 0.0).rolling(3).mean()
        loss3 = (-delta2.where(delta2 < 0, 0.0)).rolling(3).mean()
        rsi3 = (100 - 100 / (1 + gain3 / loss3.replace(0, np.nan))).fillna(50)

        # ── Regime detection ──────────────────────────────────────────────────
        in_bull = sma50 > sma200
        genuine_bear = ~in_bull & (dd_yr < -15)  # Bear + >15% drawdown from 1yr high

        # ── RSI2 dip-entry: hold-10-days state machine (bull mode only) ───────
        entry_signal = in_bull & (rsi2 < 10)
        bull_position = pd.Series(0, index=data.index)
        in_hold = False
        hold_count = 0
        for i in range(len(data)):
            if in_bull.iloc[i]:
                if entry_signal.iloc[i]:
                    in_hold = True
                    hold_count = 10  # Hold for 10 trading days
                if in_hold:
                    bull_position.iloc[i] = 1
                    hold_count -= 1
                    if hold_count <= 0:
                        in_hold = False
            else:
                in_hold = False  # Reset when exiting bull mode

        # ── Build signals ─────────────────────────────────────────────────────
        signals = pd.Series(0, index=data.index)

        # Bull: RSI2 dip-entry hold10 (only long during high-probability windows)
        signals[bull_position == 1] = 1

        # Bear: EMA13/34 timing within genuine bear
        signals[genuine_bear & (ema13 < ema34)] = -1   # Short: confirmed downtrend
        signals[genuine_bear & (ema13 >= ema34)] = 0   # Cash: bear bounce in progress

        # Shallow bear: CASH (SMA50<SMA200 but drawdown < 15%)
        signals[~in_bull & ~genuine_bear] = 0

        # RSI3 override: extreme oversold → force long (catches bottoms in any regime)
        signals[rsi3 < 10] = 1

        # Minimal warmup (5 days for RSI convergence)
        signals.iloc[:5] = 0

        return self.apply_signals(result_df, signals)
