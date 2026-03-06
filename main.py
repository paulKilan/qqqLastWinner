import os
import importlib
from datetime import datetime
import pandas as pd
from backtest.backtest import BacktestConfig, run_backtest_with_strategy
from strategy.ensemble_strategy import EnsembleStrategy

OUTPUT_DIR = "backtest_outputs"
DATA_DIR = "data"

def _load_prices(path: str) -> pd.DataFrame:
    """
    Loads Investing.com CSV (columns: Date, Price, Open, High, Low, Vol., Change %)
    and normalizes to ['open', 'close'] for backtest use.
    """

    df = pd.read_csv(path)

    # Standard Investing.com structure:
    # Date, Price, Open, High, Low, Vol., Change %
    if not {"Date", "Price", "Open"}.issubset(df.columns):
        raise ValueError(f"{path}: unexpected column names, expected Date/Price/Open.")

    df["Date"] = pd.to_datetime(df["Date"])
    df = df.set_index("Date").sort_index()

    # Normalize: 'Price' is the CLOSE, 'Open' is the OPEN
    out = df[["Open", "Price"]].copy()
    out.columns = ["open", "close"]

    # Convert to numeric, drop NaN (handle comma-separated numbers)
    out["open"] = pd.to_numeric(out["open"].astype(str).str.replace(",", ""), errors="coerce")
    out["close"] = pd.to_numeric(out["close"].astype(str).str.replace(",", ""), errors="coerce")
    out = out.dropna(subset=["open", "close"])

    return out

def _load_strategy(module_path: str, class_name: str):
    """Dynamically load a strategy class and return an instance."""
    mod = importlib.import_module(module_path)
    cls = getattr(mod, class_name)
    return cls()


# =============================================================================
# MODE: "single" or "ensemble"
# =============================================================================
MODE = "ensemble"

# =============================================================================
# LEVERAGE MODE: "3x" (TQQQ/SQQQ) or "1x" (QQQ long/short)
# =============================================================================
LEVERAGE = "1x"

# =============================================================================
# SINGLE STRATEGY CONFIG  (used when MODE = "single")
# =============================================================================
SINGLE_STRATEGY_MODULE = "strategy.sma_crossover_strategy"
SINGLE_STRATEGY_CLASS  = "SmaCrossoverStrategy"

# =============================================================================
# ENSEMBLE CONFIG  (used when MODE = "ensemble")
# =============================================================================
# Each entry: (module_path, class_name, weight)
# Weights are auto-normalized so they don't need to sum to 1.
# Tuned weights (from tune_ensemble.py grid search):
#   Best overall:    SMA=0.4, EMA=0.4, Enhanced=0.2, BB=0.2, RSI=0.0 → $507k, 25 trades, 72% win
#   Best moderate:   SMA=0.6, EMA=0.2, Enhanced=0.0, BB=0.4, RSI=0.4 → $308k, 68 trades, 71% win
ENSEMBLE_STRATEGIES = [
    ("strategy.sma_crossover_strategy",   "SmaCrossoverStrategy",   0.4),
    ("strategy.ema_crossover_strategy",   "EmaCrossoverStrategy",   0.4),
    ("strategy.enhanced_sma_strategy",    "EnhancedSmaStrategy",    0.2),
    ("strategy.bollinger_bands_strategy", "BollingerBandsStrategy", 0.2),
    ("strategy.rsi_strategy",             "RsiStrategy",            0.0),
]
LONG_THRESHOLD  = 0.3   # go long when blended long signal >= this
SHORT_THRESHOLD = 0.3   # go short when blended short signal >= this

# =============================================================================
# COMMON BACKTEST SETTINGS
# =============================================================================
START_DATE       = "2013-01-02"
END_DATE         = "2024-12-31"
INITIAL_CAPITAL  = 10_000
TRADE_PRICE      = "open"       # t+1 "open" or "close"
SHARE_ROUNDING   = "fractional"  # "floor" | "nearest" | "fractional"


def main():
    # ---- build strategy ----
    if MODE == "ensemble":
        pairs = []
        for mod_path, cls_name, weight in ENSEMBLE_STRATEGIES:
            strat = _load_strategy(mod_path, cls_name)
            pairs.append((strat, weight))
        strategy = EnsembleStrategy(
            strategies=pairs,
            long_threshold=LONG_THRESHOLD,
            short_threshold=SHORT_THRESHOLD,
        )
        print(f"\nEnsemble mode: {len(pairs)} strategies, "
              f"long_thresh={LONG_THRESHOLD}, short_thresh={SHORT_THRESHOLD}")
    else:
        strategy = _load_strategy(SINGLE_STRATEGY_MODULE, SINGLE_STRATEGY_CLASS)
        print(f"\nSingle mode: {SINGLE_STRATEGY_CLASS}")

    # ---- load ETF data ----
    if LEVERAGE == "1x":
        # 1X mode: use QQQ for both long and short
        qqq = _load_prices(os.path.join(DATA_DIR, "QQQ.csv"))
        long_prices = qqq
        short_prices = qqq
        print(f"Leverage: 1X (QQQ long / QQQ short-sell)")
        print(f"QQQ data: {qqq.index.min().date()} → {qqq.index.max().date()}, {len(qqq)} rows")
    else:
        # 3X mode: use TQQQ/SQQQ
        long_prices = _load_prices(os.path.join(DATA_DIR, "TQQQ.csv"))
        short_prices = _load_prices(os.path.join(DATA_DIR, "SQQQ.csv"))
        print(f"Leverage: 3X (TQQQ long / SQQQ short)")

    # ---- backtest config ----
    cfg = BacktestConfig(
        start_date=START_DATE,
        end_date=END_DATE,
        initial_capital=INITIAL_CAPITAL,
        trade_price=TRADE_PRICE,
        share_rounding=SHARE_ROUNDING,
        leverage_mode=LEVERAGE,
    )

    # ---- run ----
    trades, equity, issues = run_backtest_with_strategy(
        strategy=strategy,
        tqqq_prices=long_prices,
        sqqq_prices=short_prices,
        cfg=cfg,
        contextData={},
    )

    # ---- save ----
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    trades_path = os.path.join(OUTPUT_DIR, f"trades_{LEVERAGE}_{ts}.csv")

    trades.to_csv(trades_path, index=False)

    print(f"\nBacktest complete ({LEVERAGE} mode)")
    print(f"Trades : {trades_path}")
    if not trades.empty:
        print(f"Total trades: {len(trades)}")
        print(f"Final Equity: ${equity['Equity'].iloc[-1]:,.2f}")
        ret = (equity['Equity'].iloc[-1] - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100
        print(f"Return: {ret:+.2f}%")
        print("\nAll Trades (Entry Date = Buy Date):")
        pd.set_option('display.max_rows', None)
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', 1000)
        cols = ['Symbol', 'Direction', 'StartDate', 'BuyPrice', 'EndDate', 'SellPrice', 'Profit', 'isProfitable']
        available_cols = [c for c in cols if c in trades.columns]
        print(trades[available_cols].to_string())

if __name__ == "__main__":
    main()
