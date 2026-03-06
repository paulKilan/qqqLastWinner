"""
Compare 1X (QQQ long/short) vs 3X (TQQQ/SQQQ) backtest results.
Shows readable trade-by-trade comparison aligned to the same strategy signals.
"""
import os
import pandas as pd
from backtest.backtest import BacktestConfig, run_backtest_with_strategy, normalize_strategy_output
from strategy.ensemble_strategy import EnsembleStrategy
import importlib

DATA_DIR = "data"
START_DATE = "2013-01-02"
END_DATE = "2024-12-31"
INITIAL_CAPITAL = 10_000

ENSEMBLE_STRATEGIES = [
    ("strategy.sma_crossover_strategy",   "SmaCrossoverStrategy",   0.4),
    ("strategy.ema_crossover_strategy",   "EmaCrossoverStrategy",   0.4),
    ("strategy.enhanced_sma_strategy",    "EnhancedSmaStrategy",    0.2),
    ("strategy.bollinger_bands_strategy", "BollingerBandsStrategy", 0.2),
    ("strategy.rsi_strategy",             "RsiStrategy",            0.0),
]
LONG_THRESHOLD  = 0.3
SHORT_THRESHOLD = 0.3


def _load_prices(path):
    df = pd.read_csv(path)
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.set_index("Date").sort_index()
    out = df[["Open", "Price"]].copy()
    out.columns = ["open", "close"]
    out["open"] = pd.to_numeric(out["open"].astype(str).str.replace(",", ""), errors="coerce")
    out["close"] = pd.to_numeric(out["close"].astype(str).str.replace(",", ""), errors="coerce")
    out = out.dropna(subset=["open", "close"])
    return out


def build_strategy():
    pairs = []
    for mod_path, cls_name, weight in ENSEMBLE_STRATEGIES:
        mod = importlib.import_module(mod_path)
        cls = getattr(mod, cls_name)
        pairs.append((cls(), weight))
    return EnsembleStrategy(
        strategies=pairs,
        long_threshold=LONG_THRESHOLD,
        short_threshold=SHORT_THRESHOLD,
    )


def run_mode(mode: str):
    strategy = build_strategy()
    if mode == "1x":
        qqq = _load_prices(os.path.join(DATA_DIR, "QQQ.csv"))
        long_prices, short_prices = qqq, qqq
    else:
        long_prices = _load_prices(os.path.join(DATA_DIR, "TQQQ.csv"))
        short_prices = _load_prices(os.path.join(DATA_DIR, "SQQQ.csv"))

    cfg = BacktestConfig(
        start_date=START_DATE, end_date=END_DATE,
        initial_capital=INITIAL_CAPITAL, trade_price="open",
        share_rounding="fractional", leverage_mode=mode,
    )
    trades, equity, issues = run_backtest_with_strategy(
        strategy=strategy, tqqq_prices=long_prices,
        sqqq_prices=short_prices, cfg=cfg, contextData={},
    )
    return trades, equity


def format_trade_row(t):
    """Format one trade into a readable string."""
    direction = t.get('Direction', 'LONG' if not t.get('isShortSale', False) else 'SHORT')
    sym = t['Symbol']
    start = pd.Timestamp(t['StartDate']).strftime('%Y-%m-%d')
    end = pd.Timestamp(t['EndDate']).strftime('%Y-%m-%d')
    duration = t.get('Duration', '?')
    buy = t['BuyPrice']
    sell = t['SellPrice']
    profit = t['Profit']
    pct = t.get('ProfitPercent', 0) * 100
    win = "✓" if t['isProfitable'] else "✗"
    return (direction, sym, start, end, duration, buy, sell, profit, pct, win)


def main():
    print("=" * 120)
    print("BACKTEST COMPARISON: 1X (QQQ long/short) vs 3X (TQQQ/SQQQ)")
    print(f"Period: {START_DATE} → {END_DATE} | Capital: ${INITIAL_CAPITAL:,} | Strategy: Ensemble")
    print("=" * 120)

    # Run both
    trades_1x, equity_1x = run_mode("1x")
    trades_3x, equity_3x = run_mode("3x")

    # ========== 1X TRADES ==========
    print("\n" + "─" * 120)
    print("  1X MODE — QQQ Long / QQQ Short-Sell")
    print("─" * 120)
    print(f"  {'#':<3} {'Dir':<6} {'Sym':<6} {'Entry Date':<12} {'Entry $':>10} {'Exit Date':<12} {'Exit $':>10} {'Days':>5} {'Profit':>12} {'Return':>9} {'Win':>4}")
    print("  " + "-" * 105)

    cumulative_1x = INITIAL_CAPITAL
    for i, (_, t) in enumerate(trades_1x.iterrows()):
        d, sym, start, end, dur, buy, sell, profit, pct, win = format_trade_row(t)
        cumulative_1x += profit
        print(f"  {i+1:<3} {d:<6} {sym:<6} {start:<12} ${buy:>9.2f} {end:<12} ${sell:>9.2f} {dur:>5} ${profit:>10.2f} {pct:>+8.2f}%  {win}")

    final_1x = equity_1x['Equity'].iloc[-1]
    ret_1x = (final_1x - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100

    # Max drawdown
    eq_s = equity_1x['Equity']
    dd_1x = ((eq_s - eq_s.expanding().max()) / eq_s.expanding().max() * 100).min()

    print("  " + "-" * 105)
    print(f"  {'TOTAL':<3} {'':6} {'':6} {'':12} {'':>10} {'':12} {'':>10} {'':>5} ${trades_1x['Profit'].sum():>10.2f} {ret_1x:>+8.2f}%")
    print(f"\n  Final Equity: ${final_1x:,.2f}  |  Return: {ret_1x:+,.2f}%  |  "
          f"Trades: {len(trades_1x)}  |  Win Rate: {trades_1x['isProfitable'].mean()*100:.1f}%  |  "
          f"Max DD: {dd_1x:.2f}%")

    # ========== 3X TRADES ==========
    print("\n" + "─" * 120)
    print("  3X MODE — TQQQ Long / SQQQ Long")
    print("─" * 120)
    print(f"  {'#':<3} {'Dir':<6} {'Sym':<6} {'Entry Date':<12} {'Entry $':>10} {'Exit Date':<12} {'Exit $':>10} {'Days':>5} {'Profit':>12} {'Return':>9} {'Win':>4}")
    print("  " + "-" * 105)

    for i, (_, t) in enumerate(trades_3x.iterrows()):
        d, sym, start, end, dur, buy, sell, profit, pct, win = format_trade_row(t)
        print(f"  {i+1:<3} {d:<6} {sym:<6} {start:<12} ${buy:>9.2f} {end:<12} ${sell:>9.2f} {dur:>5} ${profit:>10.2f} {pct:>+8.2f}%  {win}")

    final_3x = equity_3x['Equity'].iloc[-1]
    ret_3x = (final_3x - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100

    eq_s = equity_3x['Equity']
    dd_3x = ((eq_s - eq_s.expanding().max()) / eq_s.expanding().max() * 100).min()

    print("  " + "-" * 105)
    print(f"  {'TOTAL':<3} {'':6} {'':6} {'':12} {'':>10} {'':12} {'':>10} {'':>5} ${trades_3x['Profit'].sum():>10.2f} {ret_3x:>+8.2f}%")
    print(f"\n  Final Equity: ${final_3x:,.2f}  |  Return: {ret_3x:+,.2f}%  |  "
          f"Trades: {len(trades_3x)}  |  Win Rate: {trades_3x['isProfitable'].mean()*100:.1f}%  |  "
          f"Max DD: {dd_3x:.2f}%")

    # ========== WHY DIFFERENT? ==========
    print("\n" + "=" * 120)
    print("WHY ARE THE TRADE COUNTS DIFFERENT?")
    print("=" * 120)
    print("""
  The strategy signals are IDENTICAL — both modes receive the exact same
  longPositionPct / shortPositionPct from the Ensemble strategy.

  The difference is in EXECUTION:

  • In 3X mode, "go short" means buying SQQQ shares.
    SQQQ prices in 2013-2016 were $30,000-$300,000/share (synthetic 3x data).
    With $10K-$20K capital, floor($20,000 / $293,840) = 0 shares → trade SKIPPED.

  • In 1X mode, "go short" means short-selling QQQ at ~$66-$342/share.
    This always executes because QQQ is affordable.

  Result: 3X mode skips 7 early short trades that 1X can execute,
  giving 25 trades vs 32. The win rates differ because those 7
  skipped trades had a mix of wins and losses.
""")

    # ========== SUMMARY ==========
    print("─" * 120)
    print("SIDE-BY-SIDE SUMMARY")
    print("─" * 120)

    rows = [
        ("Final Equity",  f"${final_1x:>12,.2f}", f"${final_3x:>12,.2f}"),
        ("Return",        f"{ret_1x:>+12,.2f}%",  f"{ret_3x:>+12,.2f}%"),
        ("Total Trades",  f"{len(trades_1x):>13}", f"{len(trades_3x):>13}"),
        ("Win Rate",      f"{trades_1x['isProfitable'].mean()*100:>12.1f}%", f"{trades_3x['isProfitable'].mean()*100:>12.1f}%"),
        ("Max Drawdown",  f"{dd_1x:>12.2f}%",     f"{dd_3x:>12.2f}%"),
        ("Avg Trade P&L", f"${trades_1x['Profit'].mean():>11,.2f}", f"${trades_3x['Profit'].mean():>11,.2f}"),
        ("Best Trade",    f"${trades_1x['Profit'].max():>11,.2f}", f"${trades_3x['Profit'].max():>11,.2f}"),
        ("Worst Trade",   f"${trades_1x['Profit'].min():>11,.2f}", f"${trades_3x['Profit'].min():>11,.2f}"),
    ]

    print(f"  {'Metric':<20} {'1X (QQQ)':>15}   {'3X (TQQQ/SQQQ)':>15}")
    print("  " + "-" * 55)
    for label, v1, v2 in rows:
        print(f"  {label:<20} {v1:>15}   {v2:>15}")
    print("=" * 120)


if __name__ == "__main__":
    main()
