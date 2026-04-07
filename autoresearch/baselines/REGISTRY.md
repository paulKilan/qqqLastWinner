# Strategy Baseline Registry

Each accepted iteration is archived here as a runnable `.py` snapshot.
`experimental_strategy.py` is the active sandbox — it is always based on the
latest baseline but may contain in-progress experiments.

## How to restore a baseline

```bash
# Restore Iter31 (current best) into the active sandbox:
cp autoresearch/baselines/iter31.py autoresearch/experimental_strategy.py

# Then verify it runs cleanly:
python -m autoresearch.run_experiment autoresearch.experimental_strategy ExperimentalStrategy
```

## Promotion rule

A new baseline is created **only** when an experiment is a strict Pareto improvement:
- MinRatio (worst window across all 5 original windows) must increase OR stay same
- Every individual window must be >= its previous value (no regression)
- Trades/year must remain 12–120 on every window

When promoted:
1. Copy `experimental_strategy.py` → `baselines/iterN.py`
2. Update this registry table
3. Commit both files together

---

## Iteration History

### Pre-Autoresearch Strategies (no systematic evaluation)
Exploratory single-indicator strategies before the ensemble framework.
See `pre_iter_*.py` files in this folder.

| File | Strategy | Notes |
|------|----------|-------|
| `pre_iter_sma_crossover_strategy.py` | SMA50/200 crossover | 2460% return, only ~10 trades/yr |
| `pre_iter_rsi_strategy.py` | RSI mean-reversion | baseline mean-reversion |
| `pre_iter_macd_strategy.py` | MACD crossover | standard momentum |
| `pre_iter_ema_crossover_strategy.py` | EMA crossover | faster SMA variant |
| `pre_iter_ensemble_strategy.py` | Early ensemble | pre-iteration ensemble attempt |
| `pre_iter_bollinger_bands_strategy.py` | Bollinger Bands | volatility breakout |
| `pre_iter_momentum_strategy.py` | Momentum | rate-of-change |
| `pre_iter_donchian_channel_strategy.py` | Donchian Channel | breakout system |
| `pre_iter_atr_breakout_strategy.py` | ATR Breakout | volatility-adjusted breakout |
| `pre_iter_stochastic_strategy.py` | Stochastic | oscillator-based |
| `pre_iter_trend_bounce_strategy.py` | Trend Bounce | pullback in trend |
| `pre_iter_williams_r_strategy.py` | Williams %R | momentum oscillator |
| `pre_iter_enhanced_sma_strategy.py` | Enhanced SMA | SMA with filters |

---

### Autoresearch Iterations (systematic, Pareto-only promotions)

| Iter | File | MinRatio | Full | 2013-18 | 2019-24 | 2020-22 | 2023-24 | Key Change |
|------|------|----------|------|---------|---------|---------|---------|------------|
| 17 | git:d9337b3 | — | — | — | — | — | — | CleanBear + RSI2 dip-entry hold-10 |
| 18 | git:45fda6e | — | — | — | — | — | 0.92x | Adaptive bull exit |
| 19 | git:d006512 | 0.93x | 1.11x | 0.99x | 1.22x | 3.10x | 0.93x | 6-sub strict voting ensemble |
| 20 | git:210ddf5 | 0.95x | 1.06x | 0.99x | 1.15x | 2.98x | 0.95x | mom20 bear guard |
| 21 | git:4df47f0 | 1.02x | 1.24x | 1.02x | 1.36x | 3.78x | 1.07x | MFI replaces RSI3 in Sub-F |
| 22 | docstring | 1.07x | 1.38x | 1.08x | 1.43x | 3.60x | 1.07x | Shallow-bear early recovery |
| 23 | docstring | — | — | — | — | — | — | (intermediate) |
| 24 | docstring | 1.14x | 1.64x | 1.17x | 1.73x | 4.38x | 1.14x | (intermediate) |
| 25 | docstring | 1.26x | 1.87x | 1.27x | 1.89x | 4.34x | 1.26x | pv-adaptive RSI3 + Sub-E EMA17/SMA20 |
| 26 | docstring | 1.27x | 1.94x | 1.29x | 1.95x | 4.51x | 1.27x | Sub-E SMA25 extended-bull |
| 27 | docstring | 1.27x | 2.00x | 1.29x | 2.01x | 4.74x | 1.27x | Sub-E SMA27 sweet spot |
| 28 | docstring | 1.27x | 2.05x | 1.29x | 2.07x | 4.97x | 1.27x | Sub-C mom5<-5% secondary trigger |
| 29 | docstring | 1.29x | 2.08x | 1.29x | 2.10x | 5.03x | 1.29x | Sub-A cash_days=2 at pv≥1.20 |
| 30 | docstring | 1.30x | 2.12x | 1.30x | 2.14x | 4.76x | 1.32x | Sub-C RSI2<10 hold-11 days |
| **31** | **iter31.py** | **1.33x** | **2.27x** | **1.35x** | **2.23x** | **5.09x** | **1.33x** | **Sub-F pv<1.06 MFI bypass ← CURRENT BEST** |

---

### Rejected Experiments (do not re-try)

See the exhaustive search section in `iter31.py` docstring for the full list of
~115 experiments that were tested and rejected (Iter25–Iter32).

Key rejections to never retry:
- `MFI_OB=65`: 2013-18 trades/yr < 12. CATASTROPHIC.
- `vote_long >= 4` (any form): 2023-24 = 0.87x. CATASTROPHIC.
- `Sub-F pv<1.07`: 2013-18 trades/yr = 11.8 < 12 minimum.
- `dd_yr threshold -20%`: 2013-18 trades = 11.7 < 12, 2013-24 = 1.75x.
- `genuine_bear CMF recovery`: max DD -53.5%, 2003-07 worsens.
- `Sub-D RSI14>45`: 2013-18 = 0.72x. CATASTROPHIC.
- `apply_bear rsi3<15 (vs <10)`: 2013-18 = 1.00x. CATASTROPHIC.
