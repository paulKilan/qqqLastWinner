import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Optional, Literal, Dict, Tuple

PriceField = Literal["open", "close"]
Rounding = Literal["floor", "nearest", "fractional"]

# -------------------------
# Configuration
# -------------------------
@dataclass
class BacktestConfig:
    """Configuration for backtesting parameters."""
    start_date: str
    end_date: str
    initial_capital: float = 10_000.0
    trade_price: PriceField = "open"          # Execute at t+1 open or close
    share_rounding: Rounding = "floor"        # How to round share quantities

# -------------------------
# Helper Functions
# -------------------------
def _round_shares(x: float, mode: Rounding) -> float:
    """Round share quantities based on specified mode."""
    if mode == "fractional":
        return float(x)
    if mode == "nearest":
        return float(np.round(x))
    return float(np.floor(max(x, 0.0)))  # Non-negative floor

def _prepare_price_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Prepare price data for backtesting.
    Expects columns: 'open', 'close' with DatetimeIndex.
    """
    out = df[["open", "close"]].copy()
    out.index = pd.to_datetime(out.index)
    out.sort_index(inplace=True)
    
    if out.isna().any().any():
        raise ValueError("Price data contains NaNs. Clean your data first.")
    
    return out

# -------------------------
# Strategy Output Processing
# -------------------------
def normalize_strategy_output(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
    """
    Normalize strategy output to standard format.
    
    Input: DataFrame with 'date', 'longPositionPct', 'shortPositionPct', 'error'
    Output: (positions_df, errors_series)
    """
    out = df.copy()
    
    # Handle different error column names
    err_col = "error" if "error" in out.columns else ("Error" if "Error" in out.columns else None)
    
    # Set date as index
    if "date" in out.columns:
        out = out.set_index("date")
    out.index = pd.to_datetime(out.index)
    out.sort_index(inplace=True)
    
    # Validate required columns
    if "longPositionPct" not in out.columns or "shortPositionPct" not in out.columns:
        raise ValueError("Strategy must provide 'longPositionPct' and 'shortPositionPct'")
    
    # Clean and validate position percentages
    out["longPositionPct"] = pd.to_numeric(out["longPositionPct"], errors="coerce").clip(0.0, 1.0)
    out["shortPositionPct"] = pd.to_numeric(out["shortPositionPct"], errors="coerce").clip(0.0, 1.0)
    
    # Create positions DataFrame
    positions = pd.DataFrame({
        "w_tqqq": out["longPositionPct"],
        "w_sqqq": out["shortPositionPct"]
    }, index=out.index)
    
    errors = out[err_col] if err_col else pd.Series(index=out.index, dtype="object")
    return positions, errors

# -------------------------
# Data Alignment and Execution Timing
# -------------------------
def align_data_and_shift_positions(
    positions: pd.DataFrame,
    tqqq_prices: pd.DataFrame,
    sqqq_prices: pd.DataFrame,
    cfg: BacktestConfig
) -> Tuple[pd.DatetimeIndex, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Align data to ETF trading calendar and shift positions for t+1 execution.
    
    This implements the core requirement: decisions made on day t are executed
    at the next trading day's open/close (t+1).
    """
    # Prepare price data
    tqqq = _prepare_price_data(tqqq_prices)
    sqqq = _prepare_price_data(sqqq_prices)
    
    # Define date range
    start, end = pd.to_datetime(cfg.start_date), pd.to_datetime(cfg.end_date)
    
    # Get common trading days for both ETFs
    etf_calendar = tqqq.index.intersection(sqqq.index)
    etf_calendar = etf_calendar[(etf_calendar >= start) & (etf_calendar <= end)]
    
    # Filter price data to trading calendar
    tqqq = tqqq.loc[etf_calendar]
    sqqq = sqqq.loc[etf_calendar]
    
    # Align positions to ETF calendar (forward-fill to persist last target)
    aligned_positions = positions.reindex(etf_calendar).ffill().fillna(0.0)
    
    # Shift positions by +1 day for t+1 execution
    shifted_positions = aligned_positions.shift(1)
    execution_dates = etf_calendar[1:]  # First day has no prior signal
    
    # Filter to execution dates
    shifted_positions = shifted_positions.loc[execution_dates]
    tqqq = tqqq.loc[execution_dates]
    sqqq = sqqq.loc[execution_dates]
    
    # Ensure position weights are valid
    shifted_positions["w_tqqq"] = shifted_positions["w_tqqq"].clip(0.0, 1.0)
    shifted_positions["w_sqqq"] = shifted_positions["w_sqqq"].clip(0.0, 1.0)
    
    return execution_dates, shifted_positions, tqqq, sqqq

# -------------------------
# Core Backtesting Engine
# -------------------------
def run_backtest_with_strategy(
    strategy,
    tqqq_prices: pd.DataFrame,
    sqqq_prices: pd.DataFrame,
    cfg: BacktestConfig,
    contextData: Optional[dict] = None
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Run backtest with the given strategy.
    
    Returns:
        trades_df: Complete trade log with entry/exit details
        equity_df: Daily equity curve
        issues_df: Strategy errors and warnings
    """
    # 1. Get strategy signals
    strategy_output = strategy.execute(
        startDate=cfg.start_date, 
        endDate=cfg.end_date, 
        contextData=contextData or {}
    )
    positions, errors = normalize_strategy_output(strategy_output)
    
    # 2. Align data and shift for t+1 execution
    exec_dates, positions, tqqq, sqqq = align_data_and_shift_positions(
        positions, tqqq_prices, sqqq_prices, cfg
    )
    
    # 3. Collect strategy errors
    issues_df = errors.reindex(exec_dates).dropna().to_frame(name="error").reset_index()
    issues_df.rename(columns={"index": "Date"}, inplace=True)
    
    # 4. Initialize backtest state
    cash = float(cfg.initial_capital)
    shares = {"TQQQ": 0.0, "SQQQ": 0.0}
    open_trades = {"TQQQ": None, "SQQQ": None}
    trade_log = []
    equity_log = []
    
    def calculate_equity(date: pd.Timestamp) -> float:
        """Calculate total portfolio equity at close prices."""
        return (cash + 
                shares["TQQQ"] * float(tqqq.loc[date, "close"]) + 
                shares["SQQQ"] * float(sqqq.loc[date, "close"]))
    
    # 5. Execute trades only on signal changes
    prev_w_tqqq = None
    prev_w_sqqq = None
    
    for date in exec_dates:
        # Get target allocations and prices
        w_tqqq = float(positions.loc[date, "w_tqqq"])
        w_sqqq = float(positions.loc[date, "w_sqqq"])
        tqqq_price = float(tqqq.loc[date, cfg.trade_price])
        sqqq_price = float(sqqq.loc[date, cfg.trade_price])
        
        # Only trade if signal has changed
        if prev_w_tqqq is not None and (w_tqqq == prev_w_tqqq and w_sqqq == prev_w_sqqq):
            # No signal change, just record equity
            equity_log.append({
                "Date": date,
                "Equity": calculate_equity(date),
                "Cash": cash,
                "TQQQ_Shares": shares["TQQQ"],
                "SQQQ_Shares": shares["SQQQ"]
            })
            continue
        
        # Signal has changed - execute trades
        # First, sell all current positions
        for symbol, price_df in [("TQQQ", tqqq), ("SQQQ", sqqq)]:
            if shares[symbol] > 0:
                sell_price = float(price_df.loc[date, cfg.trade_price])
                sell_value = shares[symbol] * sell_price
                cash += sell_value
                
                # Log the sale if it closes a position
                if open_trades[symbol] is not None:
                    trade = open_trades[symbol]
                    profit = (sell_price - trade["entry_price"]) * trade["shares"]
                    profit_pct = profit / (trade["entry_price"] * trade["shares"])
                    
                    trade_log.append({
                        "Symbol": symbol,
                        "StartDate": trade["entry_date"],
                        "EndDate": date,
                        "Duration": (exec_dates.get_loc(date) - exec_dates.get_loc(trade["entry_date"])),
                        "BuyPrice": round(trade["entry_price"], 6),
                        "SellPrice": round(sell_price, 6),
                        "ShareSize": int(trade["shares"]) if cfg.share_rounding != "fractional" else trade["shares"],
                        "Profit": round(profit, 6),
                        "ProfitPercent": round(profit_pct, 6),
                        "isProfitable": profit > 0,
                        "isShortSale": False
                    })
                    open_trades[symbol] = None
                
                shares[symbol] = 0.0
        
        # Now buy new positions based on target allocation
        current_equity = calculate_equity(date)
        target_tqqq_value = w_tqqq * current_equity
        target_sqqq_value = w_sqqq * current_equity
        
        # Calculate target share quantities
        target_tqqq_shares = _round_shares(target_tqqq_value / max(tqqq_price, 1e-9), cfg.share_rounding)
        target_sqqq_shares = _round_shares(target_sqqq_value / max(sqqq_price, 1e-9), cfg.share_rounding)
        
        # Execute new trades
        for symbol, target_shares, price in [("TQQQ", target_tqqq_shares, tqqq_price), 
                                           ("SQQQ", target_sqqq_shares, sqqq_price)]:
            if target_shares > 0:
                trade_value = price * target_shares
                
                # Check if we have enough cash for the trade
                if trade_value <= cash:
                    cash -= trade_value
                    shares[symbol] = target_shares
                    
                    # Track new position
                    open_trades[symbol] = {
                        "symbol": symbol,
                        "entry_date": date,
                        "entry_price": price,
                        "shares": target_shares
                    }
        
        # Update previous positions for next iteration
        prev_w_tqqq = w_tqqq
        prev_w_sqqq = w_sqqq
        
        # Record daily equity
        equity_log.append({
            "Date": date,
            "Equity": calculate_equity(date),
            "Cash": cash,
            "TQQQ_Shares": shares["TQQQ"],
            "SQQQ_Shares": shares["SQQQ"]
        })
    
    # 6. Force-close remaining positions on final day
    final_date = exec_dates[-1]
    for symbol, price_df in [("TQQQ", tqqq), ("SQQQ", sqqq)]:
        if shares[symbol] != 0:
            final_price = float(price_df.loc[final_date, cfg.trade_price])
            final_value = final_price * shares[symbol]
            cash += final_value
            
            # Log the final trade
            if open_trades[symbol] is not None:
                trade = open_trades[symbol]
                profit = (final_price - trade["entry_price"]) * trade["shares"]
                profit_pct = profit / (trade["entry_price"] * trade["shares"])
                
                trade_log.append({
                    "Symbol": symbol,
                    "StartDate": trade["entry_date"],
                    "EndDate": final_date,
                    "Duration": (exec_dates.get_loc(final_date) - exec_dates.get_loc(trade["entry_date"])),
                    "BuyPrice": round(trade["entry_price"], 6),
                    "SellPrice": round(final_price, 6),
                    "ShareSize": int(trade["shares"]) if cfg.share_rounding != "fractional" else trade["shares"],
                    "Profit": round(profit, 6),
                    "ProfitPercent": round(profit_pct, 6),
                    "isProfitable": profit > 0,
                    "isShortSale": False
                })
            
            shares[symbol] = 0.0
    
    # 7. Create output DataFrames
    trades_df = pd.DataFrame(trade_log)
    equity_df = pd.DataFrame(equity_log).set_index("Date").sort_index()
    
    return trades_df, equity_df, issues_df
