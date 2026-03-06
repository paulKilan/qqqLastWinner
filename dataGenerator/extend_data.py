"""
Extend TQQQ / SQQQ data back to 1999 using synthetic 3x / -3x daily returns
from QQQ, then splice with real post-Feb-2010 data.

Also recompute all QQQ_with_SMAs files for the full range.

Methodology:
  - TQQQ daily return = 3 × QQQ daily return  (applied to close-to-close)
  - SQQQ daily return = -3 × QQQ daily return
  - Open/High/Low are scaled proportionally from QQQ's intraday ratios
  - At the splice point (2010-02-11), we scale the entire synthetic series
    so the last synthetic day's close matches the first real day's open,
    ensuring price continuity.
"""

import pandas as pd
import numpy as np
import os
import shutil
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
BACKUP_DIR = os.path.join(DATA_DIR, "backup_originals")


def load_qqq():
    """Load QQQ, parse dates, sort ascending, return clean numeric data."""
    df = pd.read_csv(os.path.join(DATA_DIR, "QQQ.csv"))
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.sort_values("Date").reset_index(drop=True)

    for col in ["Price", "Open", "High", "Low"]:
        df[col] = pd.to_numeric(
            df[col].astype(str).str.replace(",", ""), errors="coerce"
        )
    return df


def load_etf(filename):
    """Load TQQQ or SQQQ CSV, parse dates, sort ascending."""
    path = os.path.join(DATA_DIR, filename)
    df = pd.read_csv(path)
    # Strip BOM and whitespace from column names
    df.columns = df.columns.str.strip().str.strip("\ufeff").str.strip('"')
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.sort_values("Date").reset_index(drop=True)

    for col in ["Price", "Open", "High", "Low"]:
        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col].astype(str).str.replace(",", "").str.strip('"'),
                errors="coerce",
            )
    return df


def synthesize_leveraged(qqq: pd.DataFrame, multiplier: float, splice_price: float):
    """
    Build synthetic leveraged ETF prices from QQQ daily returns.

    Args:
        qqq: QQQ DataFrame sorted ascending with numeric Price/Open/High/Low
        multiplier: 3.0 for TQQQ, -3.0 for SQQQ
        splice_price: The opening price on the first real trading day.
                      We back-scale the synthetic series so the last
                      synthetic close equals this value.

    Returns:
        DataFrame in Investing.com format (Date, Price, Open, High, Low, Vol., Change %)
    """
    df = qqq.copy()

    # Daily return based on close-to-close
    df["qqq_return"] = df["Price"].pct_change()

    # Leveraged daily return
    df["lev_return"] = df["qqq_return"] * multiplier

    # Build cumulative price series (start with arbitrary 100, then rescale)
    prices = [100.0]
    for r in df["lev_return"].iloc[1:]:
        if np.isnan(r):
            prices.append(prices[-1])
        else:
            prices.append(prices[-1] * (1 + r))
    df["synth_close"] = prices

    # Rescale so last synthetic close = splice_price
    scale = splice_price / df["synth_close"].iloc[-1]
    df["synth_close"] = df["synth_close"] * scale

    # Derive Open/High/Low from QQQ intraday ratios
    df["qqq_open_ratio"] = df["Open"] / df["Price"]    # open / close
    df["qqq_high_ratio"] = df["High"] / df["Price"]    # high / close
    df["qqq_low_ratio"] = df["Low"] / df["Price"]      # low / close

    # For SQQQ (inverse), intraday moves are reversed:
    # When QQQ goes up intraday, SQQQ goes down
    if multiplier < 0:
        # Invert the intraday ratios around 1.0, then scale by leverage
        df["synth_open"] = df["synth_close"] * (1 + (1 - df["qqq_open_ratio"]) * abs(multiplier))
        df["synth_high"] = df[["synth_close"]].assign(
            h=df["synth_close"] * (1 + (1 - df["qqq_low_ratio"]) * abs(multiplier))
        )["h"]  # QQQ low → SQQQ high
        df["synth_low"] = df[["synth_close"]].assign(
            l=df["synth_close"] * (1 + (1 - df["qqq_high_ratio"]) * abs(multiplier))
        )["l"]  # QQQ high → SQQQ low
    else:
        df["synth_open"] = df["synth_close"] * df["qqq_open_ratio"]
        df["synth_high"] = df["synth_close"] * df["qqq_high_ratio"]
        df["synth_low"] = df["synth_close"] * df["qqq_low_ratio"]

    # Ensure High >= max(Open, Close) and Low <= min(Open, Close)
    df["synth_high"] = df[["synth_high", "synth_open", "synth_close"]].max(axis=1)
    df["synth_low"] = df[["synth_low", "synth_open", "synth_close"]].min(axis=1)

    # Compute Change %
    df["change_pct"] = (df["lev_return"] * 100).round(2).astype(str) + "%"
    df.loc[0, "change_pct"] = "0.00%"

    # Format output — use 6 decimal places to avoid rounding errors
    # on small prices (e.g. synthetic TQQQ is sub-$1 for much of 1999-2009)
    out = pd.DataFrame()
    out["Date"] = df["Date"].dt.strftime("%m/%d/%Y")
    out["Price"] = df["synth_close"].round(6)
    out["Open"] = df["synth_open"].round(6)
    out["High"] = df["synth_high"].round(6)
    out["Low"] = df["synth_low"].round(6)
    out["Vol."] = "0.00K"  # synthetic — no volume data
    out["Change %"] = df["change_pct"]

    return out


def backup_originals():
    """Back up original data files before modification."""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    for fname in ["TQQQ.csv", "SQQQ.csv", "QQQ_with_SMAs.csv",
                   "QQQ_with_SMAs_20_60.csv", "QQQ_with_SMAs_50_250.csv"]:
        src = os.path.join(DATA_DIR, fname)
        dst = os.path.join(BACKUP_DIR, fname)
        if os.path.exists(src) and not os.path.exists(dst):
            shutil.copy2(src, dst)
            print(f"  Backed up {fname}")


def recompute_sma_files(qqq: pd.DataFrame):
    """Recompute all QQQ_with_SMAs CSV files from the full QQQ data."""
    df = qqq.copy()
    df = df.sort_values("Date").reset_index(drop=True)

    configs = [
        ("QQQ_with_SMAs.csv", 50, 250),
        ("QQQ_with_SMAs_20_60.csv", 20, 60),
        ("QQQ_with_SMAs_50_250.csv", 50, 250),
    ]

    for fname, fast, slow in configs:
        out = df.copy()
        out[f"SMA_{fast}"] = out["Price"].rolling(window=fast).mean()
        out[f"SMA_{slow}"] = out["Price"].rolling(window=slow).mean()

        # Format dates back to Investing.com style
        out["Date"] = out["Date"].dt.strftime("%m/%d/%Y")

        # Select columns in original order + SMA columns
        cols = ["Date", "Price", "Open", "High", "Low", "Vol.", "Change %",
                f"SMA_{fast}", f"SMA_{slow}"]
        out = out[cols]

        path = os.path.join(DATA_DIR, fname)
        out.to_csv(path, index=False)
        print(f"  Wrote {fname}: {len(out)} rows, SMA_{fast}/SMA_{slow}")


def main():
    print("=" * 60)
    print("EXTENDING TQQQ/SQQQ DATA BACK TO 1999")
    print("=" * 60)

    # 1. Back up originals
    print("\n1. Backing up original files...")
    backup_originals()

    # 2. Load data
    print("\n2. Loading data...")
    qqq = load_qqq()
    tqqq_real = load_etf("TQQQ.csv")
    sqqq_real = load_etf("SQQQ.csv")

    tqqq_start = tqqq_real["Date"].min()
    print(f"   QQQ:  {qqq['Date'].min().date()} → {qqq['Date'].max().date()} ({len(qqq)} rows)")
    print(f"   TQQQ: {tqqq_real['Date'].min().date()} → {tqqq_real['Date'].max().date()} ({len(tqqq_real)} rows)")
    print(f"   SQQQ: {sqqq_real['Date'].min().date()} → {sqqq_real['Date'].max().date()} ({len(sqqq_real)} rows)")

    # 3. Get QQQ data for the pre-TQQQ period
    qqq_pre = qqq[qqq["Date"] < tqqq_start].copy()
    print(f"\n3. QQQ rows to synthesize (before {tqqq_start.date()}): {len(qqq_pre)}")

    # 4. Determine splice prices (first real day's open price)
    tqqq_splice_price = float(tqqq_real.iloc[0]["Open"])
    sqqq_splice_price = float(sqqq_real.iloc[0]["Open"])
    print(f"\n4. Splice prices (first real day's open):")
    print(f"   TQQQ: ${tqqq_splice_price}")
    print(f"   SQQQ: ${sqqq_splice_price:,.2f}")

    # 5. Synthesize
    print("\n5. Synthesizing leveraged ETF data...")
    synth_tqqq = synthesize_leveraged(qqq_pre, multiplier=3.0, splice_price=tqqq_splice_price)
    synth_sqqq = synthesize_leveraged(qqq_pre, multiplier=-3.0, splice_price=sqqq_splice_price)
    print(f"   Synthetic TQQQ: {len(synth_tqqq)} rows")
    print(f"   Synthetic SQQQ: {len(synth_sqqq)} rows")

    # 6. Format real data to match synthetic format (unquoted, no BOM)
    print("\n6. Formatting real data...")

    def format_real(df_real):
        out = pd.DataFrame()
        out["Date"] = df_real["Date"].dt.strftime("%m/%d/%Y")
        for col in ["Price", "Open", "High", "Low"]:
            out[col] = df_real[col]
        out["Vol."] = df_real["Vol."] if "Vol." in df_real.columns else "0.00K"
        out["Change %"] = df_real["Change %"] if "Change %" in df_real.columns else "0.00%"
        return out

    real_tqqq_fmt = format_real(tqqq_real)
    real_sqqq_fmt = format_real(sqqq_real)

    # 7. Concatenate: synthetic (oldest first) + real
    print("\n7. Splicing synthetic + real data...")
    full_tqqq = pd.concat([synth_tqqq, real_tqqq_fmt], ignore_index=True)
    full_sqqq = pd.concat([synth_sqqq, real_sqqq_fmt], ignore_index=True)
    print(f"   Full TQQQ: {len(full_tqqq)} rows")
    print(f"   Full SQQQ: {len(full_sqqq)} rows")

    # 8. Validate splice continuity
    print("\n8. Validating splice point continuity...")
    synth_last_tqqq = synth_tqqq.iloc[-1]["Price"]
    real_first_tqqq = tqqq_real.iloc[0]["Open"]
    print(f"   TQQQ: last synthetic close = ${synth_last_tqqq:.4f}, "
          f"first real open = ${real_first_tqqq:.4f}, "
          f"gap = {abs(synth_last_tqqq - real_first_tqqq) / real_first_tqqq * 100:.4f}%")

    synth_last_sqqq = synth_sqqq.iloc[-1]["Price"]
    real_first_sqqq = sqqq_real.iloc[0]["Open"]
    print(f"   SQQQ: last synthetic close = ${synth_last_sqqq:,.2f}, "
          f"first real open = ${real_first_sqqq:,.2f}, "
          f"gap = {abs(synth_last_sqqq - real_first_sqqq) / real_first_sqqq * 100:.4f}%")

    # 9. Save extended files
    print("\n9. Saving extended ETF files...")
    full_tqqq.to_csv(os.path.join(DATA_DIR, "TQQQ.csv"), index=False)
    full_sqqq.to_csv(os.path.join(DATA_DIR, "SQQQ.csv"), index=False)
    print(f"   TQQQ.csv: {len(full_tqqq)} rows")
    print(f"   SQQQ.csv: {len(full_sqqq)} rows")

    # 10. Recompute SMA files
    print("\n10. Recomputing QQQ_with_SMAs files...")
    recompute_sma_files(qqq)

    # 11. Final validation
    print("\n11. Final validation...")
    for fname in ["TQQQ.csv", "SQQQ.csv"]:
        df = pd.read_csv(os.path.join(DATA_DIR, fname))
        df["Date"] = pd.to_datetime(df["Date"])
        df = df.sort_values("Date")
        for col in ["Price", "Open", "High", "Low"]:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(",", ""), errors="coerce")
        print(f"\n   {fname}:")
        print(f"     Range: {df['Date'].min().date()} → {df['Date'].max().date()}")
        print(f"     Rows: {len(df)}")
        print(f"     NaN in Price: {df['Price'].isna().sum()}")
        print(f"     NaN in Open:  {df['Open'].isna().sum()}")
        print(f"     Negative prices: {(df['Price'] < 0).sum()}")
        print(f"     Zero prices:     {(df['Price'] == 0).sum()}")

    print("\n" + "=" * 60)
    print("DONE! Data extended back to 1999.")
    print("=" * 60)


if __name__ == "__main__":
    main()
