"""
Build data/processed/dataset_90day_lookback.csv -- Dataset 2 (90-Day Lookback).

Extends Dataset 1 (Basic Daily) by adding, for every lag-eligible feature
column, 90 lagged copies ({col}_lag1 .. {col}_lag90).

Steps
-----
 1  Load data/processed/dataset_basic_daily.csv.
 2  Split columns into lag-eligible (100 cols) vs. excluded:
    - Direction (target, never lagged)
    - 9 date-encoding cols (day/month/weekday + 6 sin/cos) -- decision Q1 in
      References/DATASET_2_3_PLAN.md: past calendar values are directly
      derivable from the current date, so lagging them adds no information.
 3  For each lag-eligible column, create lag1..lag90 via .shift(1..90).
 4  Concatenate original Dataset 1 columns + all lag columns.
 5  Drop the first 90 rows (lag90 undefined before that) -- decision Q2.
 6  Save to data/processed/dataset_90day_lookback.csv.

Expected shape: ~2,778 rows x ~9,110 cols
    (100 lag-eligible cols x 90 lags = 9,000 lag cols + 110 Dataset 1 cols)

Usage
-----
    python src/features/build_dataset_90day.py
"""

import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

BASIC_DAILY_PATH = PROCESSED_DIR / "dataset_basic_daily.csv"
OUT_PATH = PROCESSED_DIR / "dataset_90day_lookback.csv"

TARGET_COL = "Direction"
DATE_ENCODING_COLS = [
    "day", "month", "weekday",
    "day_sin", "day_cos", "month_sin", "month_cos", "weekday_sin", "weekday_cos",
]
N_LAGS = 90
DROP_FIRST_N_ROWS = 90  # Q2 decision: rows without full 90-day lag history


def main() -> None:
    print("=" * 60)
    print("build_dataset_90day.py -- Dataset 2: 90-Day Lookback")
    print("=" * 60)

    print("\n[Step 1] Loading Dataset 1 (Basic Daily)...")
    if not BASIC_DAILY_PATH.exists():
        print(f"  [ERROR] Missing {BASIC_DAILY_PATH} -- run build_dataset.py first", file=sys.stderr)
        sys.exit(1)
    basic = pd.read_csv(BASIC_DAILY_PATH, index_col=0, parse_dates=True)
    print(f"  Loaded: {basic.shape[0]} rows x {basic.shape[1]} cols "
          f"({basic.index[0].date()} to {basic.index[-1].date()})")

    print("\n[Step 2] Identifying lag-eligible columns...")
    excluded = set(DATE_ENCODING_COLS) | {TARGET_COL}
    lag_cols = [c for c in basic.columns if c not in excluded]
    missing_date_cols = [c for c in DATE_ENCODING_COLS if c not in basic.columns]
    if missing_date_cols:
        print(f"  [WARN] Expected date-encoding cols not found: {missing_date_cols}", file=sys.stderr)
    print(f"  Lag-eligible: {len(lag_cols)} cols  |  "
          f"Excluded: {len(DATE_ENCODING_COLS)} date-encoding + 1 target")

    print(f"\n[Step 3] Creating lag1..lag{N_LAGS} for each lag-eligible column...")
    lag_data = {}
    for col in lag_cols:
        series = basic[col]
        for lag in range(1, N_LAGS + 1):
            lag_data[f"{col}_lag{lag}"] = series.shift(lag)
    lag_df = pd.DataFrame(lag_data, index=basic.index)
    print(f"  Created {lag_df.shape[1]} lag columns")

    print("\n[Step 4] Concatenating Dataset 1 columns + lag columns...")
    combined = pd.concat([basic, lag_df], axis=1)
    print(f"  Combined: {combined.shape[1]} cols "
          f"({basic.shape[1]} original + {lag_df.shape[1]} lag)")

    print(f"\n[Step 5] Dropping first {DROP_FIRST_N_ROWS} rows (lag{N_LAGS} warm-up)...")
    combined = combined.iloc[DROP_FIRST_N_ROWS:]
    print(f"  Rows remaining: {combined.shape[0]} "
          f"({combined.index[0].date()} to {combined.index[-1].date()})")

    print("\n[Step 6] Saving Dataset 2...")
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    combined.to_csv(OUT_PATH)

    nan_pct = combined.isna().mean().mean() * 100
    print(f"\n{'=' * 60}")
    print("DONE")
    print(f"  Output : {OUT_PATH}")
    print(f"  Shape  : {combined.shape[0]} rows x {combined.shape[1]} cols")
    print(f"  NaN    : {nan_pct:.2f}% overall")
    print("=" * 60)


if __name__ == "__main__":
    main()
