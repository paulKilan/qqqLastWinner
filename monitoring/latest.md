# QQQ Harness Monitor — 2026-05-31 12:00 UTC

## Header

- **Timestamp**: 2026-05-31 12:00:56 (heartbeat)
- **PID**: 53016 — **alive: True**
- **Iterations**: 500,528
- **Promotions**: 398
- **Tested combos**: 572,083
- **Champions**: 5
- **Current best**: `score_p0_20260510T210014` (focus=score) — score **984.53**, ret **140,555%**, sharpe **1.31**, outperf **3.94x**, DD **-23.6%**, min_ratio **1.02**

## Champion Pool Overview

| # | Label                          | Focus      | Score   | Ret %     | Sharpe | Outperf | MaxDD% | MinRatio |
|---|--------------------------------|------------|---------|-----------|--------|---------|--------|----------|
| 0 | score_p0_20260510T210014       | score      |  984.53 | 140555.06 |  1.31  |  3.94x  | -23.60 |  1.016   |
| 1 | min_ratio_p1_20260522T211339   | min_ratio  |  169.05 |  24040.70 |  1.53  |  4.73x  | -23.96 |  1.797   |
| 2 | sharpe_p2_20260524T112941      | sharpe     |  487.87 |  69562.81 |  1.74  |  5.95x  | -22.00 |  1.242   |
| 3 | diverse_p3_20260525T170635     | diverse    |  886.57 | 126525.23 |  1.89  |  5.24x  | -21.35 |  1.861   |
| 4 | outperf_p4_20260519T180312     | outperf    |  118.19 |  16758.90 |  1.17  |  6.64x  | -34.03 |  0.843   |

## Per-Window Performance — Best Champion (C0: score_p0)

| Window                       |     Strat% |     QQQ% | Ratio   | Tr/Yr | Win%  | MaxDD% | Sharpe |
|------------------------------|-----------:|---------:|--------:|------:|------:|-------:|-------:|
| 1990-01-02 to 2026-04-02     | 1400390.5% |  10269.0%| 136.37x |  19.0 | 64.4% | -38.1% |  1.26  |
| 1990-01-02 to 1998-12-31     |    717.7%  |    706.2%|   1.02x |  15.0 | 59.3% | -23.4% |  1.23  |
| 1999-01-04 to 2002-12-31     |   1219.4%  |    -55.3%|  10.00x |  39.6 | 65.2% | -38.1% |  1.76  |
| 2003-01-02 to 2007-12-31     |    116.7%  |    105.6%|   1.11x |  13.0 | 63.1% | -16.0% |  1.03  |
| 2008-01-02 to 2012-12-31     |    199.0%  |     34.5%|   5.77x |  23.4 | 59.0% | -15.2% |  1.10  |
| 2013-01-02 to 2026-04-02     |   1830.9%  |    872.4%|   2.10x |  15.9 | 69.7% | -23.6% |  1.29  |
| 2013-01-02 to 2018-12-31     |    163.4%  |    145.1%|   1.13x |  12.0 | 72.2% | -19.5% |  1.13  |
| 2019-01-02 to 2026-04-02     |    640.2%  |    295.1%|   2.17x |  19.0 | 68.8% | -23.6% |  1.42  |
| 2020-01-02 to 2022-12-30     |    124.1%  |     25.4%|   4.88x |  24.7 | 64.9% | -23.6% |  1.18  |
| 2023-01-03 to 2026-04-02     |    148.8%  |    125.5%|   1.19x |  15.7 | 70.6% | -14.8% |  1.69  |

## Diversity Check — Pairwise Hamming Distance

|     |  C0 |  C1 |  C2 |  C3 |  C4 |
|-----|----:|----:|----:|----:|----:|
| C0  |   - |  45 |  47 |  47 |  46 |
| C1  |  45 |   - |  24 |  27 |  42 |
| C2  |  47 |  24 |   - | **6** | 45 |
| C3  |  47 |  27 | **6** |   - |  44 |
| C4  |  46 |  42 |  45 |  44 |   - |

**FLAG**: No pair below 4. Closest pair = **C2 (sharpe) vs C3 (diverse) at Hamming=6** — borderline. C3 looks like a fine-tuned descendant of C2 (only 6 param keys differ). Worth watching; not yet "too similar" by the <4 threshold but the diversity slot may be redundant.

## Per-Champion Architecture Summary

### C0 — score_p0 (born iter 78187)
- **Active subs**: A✓ B✓ C✓ D✓ E✓ F✓ G✗ H✗ I✗ J✗ K✗ L✗
- **Vote**: long=5 short=2  (Iter31 defaults)
- **35 param diffs from Iter31** — pure 6-sub baseline. Notable: subA_strong_adx 25→32, subA_rsi3_low 85→78, regime_dd_thresh -15→-18, bear_short_rsi3 85→79, shallow_rsi3_long 10→7, subC_rsi2_thresh 10→15, mfi_ob 63→60, subE_ema 17→18, subF_pv_bypass 1.06→1.105

### C1 — min_ratio_p1 (born iter 302178)
- **Active subs**: A✓ B✓ C✓ D✓ E✓ F✓ G✗ H✗ I✗ J✓ K✓ L✓
- **Vote**: long=6 short=3  (raised — needs more confirmation)
- **42 param diffs**. Adds J/K/L (Williams+OBV, Donchian+Aroon, Z-score). Notable: regime_dd_thresh -15→-24 (much looser bear gate), subE_sma 27→40, subF_pv_bypass 1.06→1.145, bear_short_rsi3 85→92 (rarely short), bb_period 20→12 (tighter BB)

### C2 — sharpe_p2 (born iter 357871)
- **Active subs**: A✓ B✓ C✓ D✓ E✓ F✓ G✗ H✗ I✗ J✓ K✓ L✓
- **Vote**: long=6 short=3
- **45 param diffs**. Same active-sub set as C1 & C3. Notable: bb_period 20→26, bb_std 2.0→2.5, kdj_neutral_low 30→39, kdj_overbought 80→86, macd_signal 9→6, subA_strong_adx 25→20 (looser), subA_pv_high 1.2→1.29

### C3 — diverse_p3 (born iter 411470)
- **Active subs**: A✓ B✓ C✓ D✓ E✓ F✓ G✗ H✗ I✗ J✓ K✓ L✓
- **Vote**: long=6 short=3
- **44 param diffs**. **Nearly identical to C2** (Hamming=6). Differences: subA_pv_mid 1.13→1.18, subC_mom5_thresh -0.04→-0.035, subE_ema 15→16, macd_signal 6→12, don_period 23→28, wr_high -29→-30. Likely a parametric tweak of C2 promoted under the "diverse" focus.

### C4 — outperf_p4 (born iter 279129)
- **Active subs**: A✓ B✓ C✓ D✓ E✓ F✓ G✓ H✓ I✗ J✗ K✓ L✗
- **Vote**: long=6 short=2
- **38 param diffs**. Unique active set (only champion with G+H, no J/L). Notable: don_pos 0.5→0.8 (much later Donchian breakout), shallow_rsi3_long 10→18, subC_mom5_thresh -0.05→-0.09, kdj_oversold 20→11 (deep), macd_slow 26→34. Aggressive (6.64x outperf) but bleeds DD (-34%).

## Ensemble Diagram — Best Champion (C0: score_p0)

```
ENSEMBLE STRUCTURE (vote_long=5, vote_short=2)
├── Sub-A ✓  ADX-strong bull-pos + RSI3 cash-out
│     adx_strong=32, rsi3_low=78, rsi3_high=93
│     pv_high=1.17, pv_mid=1.05, pv_rsi_low=1.09
│     cash_high=2 (def), cash_mid=2, cash_low=2
├── Sub-B ✓  Plain in-bull long (always-on baseline)
├── Sub-C ✓  RSI2 dip + mom5 crash buy
│     rsi2_thresh=15, rsi2_hold=11 (def)
│     mom5_thresh=-0.05 (def), mom5_hold=6
├── Sub-D ✓  Mirror of Sub-B (vote weight)
├── Sub-E ✓  PV-split SMA/EMA trend follow
│     pv_split=1.05, sma_period=27 (def), ema_period=18
├── Sub-F ✓  PV-bypass MFI trend
│     pv_bypass=1.105, mfi_ob=60
├── Sub-G ✗  MACD trend confirmation
├── Sub-H ✗  KDJ momentum
├── Sub-I ✗  Bollinger mid-band trend
├── Sub-J ✗  Williams %R + OBV
├── Sub-K ✗  Donchian + Aroon breakout
└── Sub-L ✗  252d Z-score mean-reversion
      (enabled in C1/C2/C3 but disabled here)

REGIME GATES
  sma50=52, sma200=200 (def)
  regime_dd_thresh=-18
  bear_short_rsi3=79, shallow_rsi3_long=7
```

## Param Diffs vs Iter31 Defaults — Best Champion (C0)

| Param                  | Iter31 | C0     |
|------------------------|-------:|-------:|
| aroon_period           |     25 |     15 |
| bb_bandwidth_min       |   0.04 |  0.025 |
| bb_period              |     20 |     25 |
| bb_std                 |    2.0 |    2.7 |
| bear_short_rsi3        |     85 |     79 |
| don_period             |     20 |     31 |
| kdj_neutral_low        |     30 |     29 |
| kdj_overbought         |     80 |     70 |
| kdj_oversold           |     20 |     25 |
| kdj_period             |      9 |     19 |
| macd_fast              |     12 |     13 |
| macd_signal_period     |      9 |     13 |
| mfi_ob                 |     63 |     60 |
| obv_sma_period         |     20 |     26 |
| regime_dd_thresh       |    -15 |    -18 |
| shallow_rsi3_long      |     10 |      7 |
| sma50_period           |     50 |     52 |
| subA_cash_low          |      3 |      2 |
| subA_cash_mid          |      1 |      2 |
| subA_pv_high           |    1.2 |   1.17 |
| subA_pv_mid            |    1.1 |   1.05 |
| subA_pv_rsi_low        |   1.15 |   1.09 |
| subA_rsi3_high         |     90 |     93 |
| subA_rsi3_low          |     85 |     78 |
| subA_strong_adx        |     25 |     32 |
| subC_mom5_hold         |     10 |      6 |
| subC_rsi2_thresh       |     10 |     15 |
| subE_ema_period        |     17 |     18 |
| subE_pv_split          |    1.1 |   1.05 |
| subF_pv_bypass         |   1.06 |  1.105 |
| subL_zscore_high       |    2.0 |   2.25 |
| subL_zscore_low        |   -1.5 |   -2.0 |
| subL_zscore_period     |    252 |    168 |
| wr_high                |    -20 |     -5 |
| wr_low                 |    -80 |    -82 |

(Note: many diffs touch params for disabled subs G–L — these are "vestigial" tuning bits that won't affect C0's runtime path.)

## Search Progress

- **Iterations**: 500,528
- **Promotions**: 398
- **Tested combos**: 572,083
- **Total combo space**: ~1.945e+52
- **Coverage**: ~2.9e-47 of space (effectively unbounded — search is sampling rather than exhausting)
