import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Optional, Literal, Dict, Tuple

PriceField = Literal["open", "close"]
Rounding = Literal["floor", "nearest", "fractional"]

# -------------------------
# Config
# -------------------------
@dataclass
class BacktestConfig:
    start_date: str
    end_date: str
    initial_capital: float = 10_000.0         # initial capital of $10K (by default, adjustable in main.py)
    trade_price: PriceField = "open"          # fills at t+1 open (default) or close
    share_rounding: Rounding = "floor"        # "floor" | "nearest" | "fractional"
    # optional frictions (OFF by default)
    slippage_bps: Optional[float] = None
    commission_bps: Optional[float] = None

# -------------------------
# Helpers
# -------------------------
def _round_shares(x: float, mode: Rounding) -> float:
    if mode == "fractional":
        return float(x)
    if mode == "nearest":
        return float(np.round(x))
    return float(np.floor(max(x, 0.0)))  # non-negative, floor

# NOT IN USE (OFF by default))
def _apply_slippage(px: float, side: str, slippage_bps: Optional[float]) -> float:
    if not slippage_bps:
        return px
    m = slippage_bps / 10_000.0
    return px * (1 + m) if side == "buy" else px * (1 - m)

# NOT IN USE (OFF by default))
def _commission(notional: float, commission_bps: Optional[float]) -> float:
    if not commission_bps:
        return 0.0
    return abs(notional) * (commission_bps / 10_000.0)

def _prep_prices(df: pd.DataFrame) -> pd.DataFrame:
    """
    Expect columns: 'open','close' (adjusted if available). Index must be DatetimeIndex.
    If your CSV uses column case variants, normalize before calling this (main.py does).
    """
    out = df.loc[:, ["open", "close"]].copy()
    out.index = pd.to_datetime(out.index)
    out.sort_index(inplace=True)
    if out.isna().any().any():
        raise ValueError("Price data contains NaNs in open/close after loading. Clean your CSVs.")
    return out

# -------------------------
# Strategy output normalization
# -------------------------
def normalize_strategy_output(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
    """
    Input columns (from BaseStrategy.execute):
      'date', 'longPositionPct', 'shortPositionPct', 'error' (or 'Error')
    Output:
      positions: index=date, cols=['w_tqqq','w_sqqq'] in [0,1]
      errors:    Series of error strings (NaN if none)
    """
    out = df.copy()

    # accept either 'error' or 'Error'
    err_col = "error" if "error" in out.columns else ("Error" if "Error" in out.columns else None)

    if "date" in out.columns:
        out = out.set_index("date")
    out.index = pd.to_datetime(out.index)
    out.sort_index(inplace=True)

    if "longPositionPct" not in out.columns or "shortPositionPct" not in out.columns:
        raise ValueError("Strategy output must include 'longPositionPct' and 'shortPositionPct'.")

    out["longPositionPct"]  = pd.to_numeric(out["longPositionPct"], errors="coerce").clip(0.0, 1.0)
    out["shortPositionPct"] = pd.to_numeric(out["shortPositionPct"], errors="coerce").clip(0.0, 1.0)

    positions = pd.DataFrame(
        {"w_tqqq": out["longPositionPct"], "w_sqqq": out["shortPositionPct"]},
        index=out.index,
    )
    errors = out[err_col] if err_col else pd.Series(index=out.index, dtype="object")
    return positions, errors

# -------------------------
# Alignment (t → t+1)
# -------------------------
def align_and_shift(
    positions: pd.DataFrame,
    tqqq: pd.DataFrame,
    sqqq: pd.DataFrame,
    cfg: BacktestConfig
) -> Tuple[pd.DatetimeIndex, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Align to ETF calendar and shift positions by +1 bar for next-day execution."""
    t = _prep_prices(tqqq)
    s = _prep_prices(sqqq)

    start, end = pd.to_datetime(cfg.start_date), pd.to_datetime(cfg.end_date)

    # ETF trading calendar & date range
    etf_idx = t.index.intersection(s.index)
    etf_idx = etf_idx[(etf_idx >= start) & (etf_idx <= end)]
    t, s = t.loc[etf_idx], s.loc[etf_idx]

    # Reindex positions to ETF calendar, forward-fill (policy: persist last target)
    pos = positions.reindex(etf_idx).ffill().fillna(0.0)

    # Shift by +1 so decisions on day t execute at t+1
    pos_shifted = pos.shift(1)
    exec_idx = etf_idx[1:]  # first exec day has no prior signal

    pos_shifted = pos_shifted.loc[exec_idx]
    t, s = t.loc[exec_idx], s.loc[exec_idx]

    # Guardrails
    pos_shifted["w_tqqq"] = pos_shifted["w_tqqq"].clip(0.0, 1.0)
    pos_shifted["w_sqqq"] = pos_shifted["w_sqqq"].clip(0.0, 1.0)

    return exec_idx, pos_shifted, t, s

# -------------------------
# Backtest core
# -------------------------
def run_backtest_with_strategy(
    strategy,                    # exposes execute(startDate=..., endDate=..., contextData=...)
    tqqq_prices: pd.DataFrame,   # index=Date, cols ['open','close']
    sqqq_prices: pd.DataFrame,   # index=Date, cols ['open','close']
    cfg: BacktestConfig,
    contextData: Optional[dict] = None
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Returns:
      trades_df: Trade log (row per round-trip).
      equity_df: Daily equity curve (Date index).
      issues_df: Rows where strategy reported an error.
    """
    # 1) get targets from strategy
    raw = strategy.execute(startDate=cfg.start_date, endDate=cfg.end_date, contextData=contextData or {})
    positions_raw, errors = normalize_strategy_output(raw)

    # 2) align & shift to t+1 execution
    exec_idx, positions, t, s = align_and_shift(positions_raw, tqqq_prices, sqqq_prices, cfg)

    # 3) collect errors on exec days
    issues_df = errors.reindex(exec_idx).dropna().to_frame(name="error").reset_index().rename(columns={"index": "Date"})

    # 4) run
    px_field = cfg.trade_price
    cash = float(cfg.initial_capital)
    shares: Dict[str, float] = {"TQQQ": 0.0, "SQQQ": 0.0}
    open_trade: Dict[str, dict] = {"TQQQ": None, "SQQQ": None}
    trade_rows, equity_rows = [], []

    def equity_at_close(dt: pd.Timestamp) -> float:
        return (cash
                + shares["TQQQ"] * float(t.loc[dt, "close"])
                + shares["SQQQ"] * float(s.loc[dt, "close"]))

    for dt in exec_idx:
        wT = float(positions.loc[dt, "w_tqqq"])
        wS = float(positions.loc[dt, "w_sqqq"])
        pxT = float(t.loc[dt, px_field])
        pxS = float(s.loc[dt, px_field])

        # snapshot equity using closes
        equity_pre = equity_at_close(dt)

        # targets
        target_T = wT * equity_pre
        target_S = wS * equity_pre
        tgt_shares_T = _round_shares(target_T / max(pxT, 1e-9), cfg.share_rounding)
        tgt_shares_S = _round_shares(target_S / max(pxS, 1e-9), cfg.share_rounding)

        for symbol, tgt, px in (("TQQQ", tgt_shares_T, pxT), ("SQQQ", tgt_shares_S, pxS)):
            cur = shares[symbol]
            delta = tgt - cur
            if abs(delta) < 1e-12:
                continue

            side = "buy" if delta > 0 else "sell"
            if cfg.share_rounding != "fractional":
                delta = float(np.floor(delta) if delta > 0 else np.ceil(delta))
                if delta == 0.0:
                    continue

            fill_px = _apply_slippage(px, side, cfg.slippage_bps)
            notional = fill_px * delta
            fee = _commission(notional, cfg.commission_bps)

            # cash/shares
            cash -= notional
            cash -= fee
            shares[symbol] += delta

            # open/close trade rows
            if delta > 0 and open_trade[symbol] is None:
                open_trade[symbol] = {
                    "Symbol": symbol,
                    "StartDate": dt,
                    "BuyPrice": fill_px,
                    "EntryFee": fee,
                    "ShareSize": shares[symbol],  # entry size
                }
            elif delta < 0 and shares[symbol] == 0:
                ot = open_trade[symbol]
                if ot is not None:
                    qty = ot["ShareSize"]
                    buy_px = ot["BuyPrice"]
                    entry_fee = ot["EntryFee"]
                    sell_px = fill_px
                    exit_fee = fee
                    profit = (sell_px - buy_px) * qty - (entry_fee + exit_fee)
                    profit_pct = profit / max(buy_px * qty, 1e-9)
                    start_idx = exec_idx.get_loc(ot["StartDate"])
                    end_idx = exec_idx.get_loc(dt)
                    duration = end_idx - start_idx
                    trade_rows.append({
                        "Symbol": symbol,
                        "StartDate": ot["StartDate"],
                        "EndDate": dt,
                        "Duration": duration,
                        "BuyPrice": round(buy_px, 6),
                        "SellPrice": round(sell_px, 6),
                        "ShareSize": int(qty) if cfg.share_rounding != "fractional" else qty,
                        "Profit": round(profit, 6),
                        "ProfitPercent": round(profit_pct, 6),
                        "isProfitable": profit > 0,
                        "isShortSale": False
                    })
                    open_trade[symbol] = None

        # end-of-day mark
        equity_rows.append({
            "Date": dt,
            "Equity": equity_at_close(dt),
            "Cash": cash,
            "TQQQ_Shares": shares["TQQQ"],
            "SQQQ_Shares": shares["SQQQ"],
        })

    # 5) force-close remaining positions on final exec day
    final_dt = exec_idx[-1]
    for symbol, px_df in (("TQQQ", t), ("SQQQ", s)):
        if shares[symbol] != 0:
            px = float(px_df.loc[final_dt, px_field])
            fill_px = _apply_slippage(px, "sell", cfg.slippage_bps)
            delta = -shares[symbol]
            notional = fill_px * delta
            fee = _commission(notional, cfg.commission_bps)
            cash -= notional
            cash -= fee

            ot = open_trade[symbol]
            if ot is not None:
                qty = ot["ShareSize"]
                profit = (fill_px - ot["BuyPrice"]) * qty - (ot["EntryFee"] + fee)
                profit_pct = profit / max(ot["BuyPrice"] * qty, 1e-9)
                start_idx = exec_idx.get_loc(ot["StartDate"])
                end_idx = exec_idx.get_loc(final_dt)
                duration = end_idx - start_idx
                trade_rows.append({
                    "Symbol": symbol,
                    "StartDate": ot["StartDate"],
                    "EndDate": final_dt,
                    "Duration": duration,
                    "BuyPrice": round(ot["BuyPrice"], 6),
                    "SellPrice": round(fill_px, 6),
                    "ShareSize": int(qty) if cfg.share_rounding != "fractional" else qty,
                    "Profit": round(profit, 6),
                    "ProfitPercent": round(profit_pct, 6),
                    "isProfitable": profit > 0,
                    "isShortSale": False
                })
                open_trade[symbol] = None
            shares[symbol] = 0.0

    trades_df = pd.DataFrame(trade_rows)
    equity_df = pd.DataFrame(equity_rows).set_index("Date").sort_index()
    return trades_df, equity_df, issues_df
