"""
Deep investigation: why do 1X (32 trades) and 3X (30 trades) still differ
with fractional shares enabled?
"""
import os
import pandas as pd
from backtest.backtest import (
    BacktestConfig, normalize_strategy_output,
    align_data_and_shift_positions, _prepare_price_data
)
from strategy.ensemble_strategy import EnsembleStrategy
import importlib

DATA_DIR = "data"
START_DATE = "2013-01-02"
END_DATE   = "2024-12-31"

def _load_prices(path):
    df = pd.read_csv(path)
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.set_index("Date").sort_index()
    out = df[["Open", "Price"]].copy()
    out.columns = ["open", "close"]
    out["open"]  = pd.to_numeric(out["open"].astype(str).str.replace(",", ""), errors="coerce")
    out["close"] = pd.to_numeric(out["close"].astype(str).str.replace(",", ""), errors="coerce")
    return out.dropna(subset=["open", "close"])

def build_strategy():
    configs = [
        ("strategy.sma_crossover_strategy",   "SmaCrossoverStrategy",   0.4),
        ("strategy.ema_crossover_strategy",    "EmaCrossoverStrategy",   0.4),
        ("strategy.enhanced_sma_strategy",     "EnhancedSmaStrategy",    0.2),
        ("strategy.bollinger_bands_strategy",  "BollingerBandsStrategy", 0.2),
        ("strategy.rsi_strategy",              "RsiStrategy",            0.0),
    ]
    pairs = []
    for mp, cn, w in configs:
        mod = importlib.import_module(mp)
        pairs.append((getattr(mod, cn)(), w))
    return EnsembleStrategy(strategies=pairs, long_threshold=0.3, short_threshold=0.3)

# ── 1. Raw strategy signals ──────────────────────────────────────────────────
strategy = build_strategy()
raw = strategy.execute(startDate=START_DATE, endDate=END_DATE, contextData={})
positions, _ = normalize_strategy_output(raw)

print("=" * 80)
print("STEP 1 — Raw strategy signal CHANGES (identical for both modes)")
print("=" * 80)
prev_l = prev_s = None
changes = []
for dt, row in positions.iterrows():
    wl, ws = float(row["w_long"]), float(row["w_short"])
    if (wl, ws) != (prev_l, prev_s):
        if wl == 1:   action = "GO LONG"
        elif ws == 1: action = "GO SHORT"
        else:         action = "GO CASH"
        changes.append((dt, action, wl, ws))
    prev_l, prev_s = wl, ws

for dt, a, wl, ws in changes:
    print(f"  {dt.date()}  {a:<10}")
print(f"\n  Total signal changes: {len(changes)}")

# ── 2. Build trading calendars for both modes ────────────────────────────────
qqq  = _load_prices(os.path.join(DATA_DIR, "QQQ.csv"))
tqqq = _load_prices(os.path.join(DATA_DIR, "TQQQ.csv"))
sqqq = _load_prices(os.path.join(DATA_DIR, "SQQQ.csv"))

start_dt = pd.Timestamp(START_DATE)
end_dt   = pd.Timestamp(END_DATE)

cal_1x = qqq.index[(qqq.index >= start_dt) & (qqq.index <= end_dt)]
cal_3x_raw = tqqq.index.intersection(sqqq.index)
cal_3x = cal_3x_raw[(cal_3x_raw >= start_dt) & (cal_3x_raw <= end_dt)]

print("\n" + "=" * 80)
print("STEP 2 — Trading calendars")
print("=" * 80)
print(f"  1X calendar (QQQ):          {len(cal_1x)} trading days  [{cal_1x[0].date()} → {cal_1x[-1].date()}]")
print(f"  3X calendar (TQQQ ∩ SQQQ): {len(cal_3x)} trading days  [{cal_3x[0].date()} → {cal_3x[-1].date()}]")

# Days in 1X but NOT in 3X
only_in_1x = cal_1x.difference(cal_3x)
only_in_3x = cal_3x.difference(cal_1x)
print(f"\n  Days in QQQ but NOT in TQQQ/SQQQ: {len(only_in_1x)}")
for d in only_in_1x[:20]:
    print(f"    {d.date()}")
print(f"\n  Days in TQQQ/SQQQ but NOT in QQQ: {len(only_in_3x)}")
for d in only_in_3x[:20]:
    print(f"    {d.date()}")

# ── 3. Forward-filled shifted positions on each calendar ─────────────────────
print("\n" + "=" * 80)
print("STEP 3 — Shifted positions at signal boundaries (where trades execute)")
print("=" * 80)

def get_shifted_positions(positions, calendar):
    aligned = positions.reindex(calendar).ffill().fillna(0.0)
    shifted = aligned.shift(1)
    exec_dates = calendar[1:]
    return shifted.loc[exec_dates]

shifted_1x = get_shifted_positions(positions, cal_1x)
shifted_3x = get_shifted_positions(positions, cal_3x)

# Find rows where prev differs from current (i.e., a trade triggers)
def find_trade_dates(shifted):
    trades = []
    prev = None
    for dt, row in shifted.iterrows():
        state = (float(row["w_long"]), float(row["w_short"]))
        if prev is None or state != prev:
            if state[0] == 1:   action = "LONG"
            elif state[1] == 1: action = "SHORT"
            else:               action = "CASH"
            trades.append((dt, action))
        prev = state
    return trades

td_1x = find_trade_dates(shifted_1x)
td_3x = find_trade_dates(shifted_3x)

print(f"\n  Trade-trigger dates in 1X: {len(td_1x)}")
print(f"  Trade-trigger dates in 3X: {len(td_3x)}")

# Convert to dicts for comparison
d1x = {dt.date(): a for dt, a in td_1x}
d3x = {dt.date(): a for dt, a in td_3x}

all_dates = sorted(set(d1x) | set(d3x))
diffs = [(d, d1x.get(d, '—'), d3x.get(d, '—'))
         for d in all_dates if d1x.get(d) != d3x.get(d)]

print(f"\n  Dates where 1X and 3X trade on DIFFERENT days (or one is missing):")
print(f"  {'Date':<14} {'1X Action':<14} {'3X Action':<14}")
print("  " + "-" * 42)
for d, a1, a3 in diffs:
    marker = " ← MISMATCH" if a1 == '—' or a3 == '—' else " ← SHIFTED DATE"
    print(f"  {str(d):<14} {a1:<14} {a3:<14}{marker}")

print(f"\n  Total mismatches: {len(diffs)}")
print("""
  ROOT CAUSE: When a signal fires on a day that exists in QQQ's calendar
  but NOT in TQQQ/SQQQ's calendar (or vice versa), the 'reindex + ffill'
  shifts the trade to execute on the NEXT available day in that calendar.
  This means the SAME strategy signal triggers trades on slightly different
  dates — causing apparent count differences in the final log.
""")
