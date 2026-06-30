"""
Build data/processed/dataset_basic_daily.csv — Dataset 1 (Basic Daily, ~130 cols).

Merges 6 interim panels into one ML-ready CSV.

Steps
-----
 1  Load 6 interim panels (index=date, already on business calendar).
 2  Merge on date index via pd.concat; reindex to bdate_range to guarantee completeness.
 3  Drop 2014-01-01 (New Year's Day — forex market closed, no GBP_USD_close for target).
 4  Forward-fill macro columns (_value, _yoy, _yoy_log, _sqrt, _days_since_update).
 5  Drop level CPI cols (non-stationary I(1)); keep YoY forms only.
 6  Compute equity log returns: {INDEX}_ret = log(close_t / close_{t-1}).
 7  Drop all columns of redundant equity indices (multicollinearity evidence: notebook 03).
 8  Verify required transform columns exist in merged frame.
 9  Add rate_differential = USA_central_bank_rate_value - UK_central_bank_rate_value.
10  Add date encodings: day/month/weekday (int) + sin/cos cyclical variants.
11  Add Direction target: 1 if GBP_USD_close(t+1) > GBP_USD_close(t), else 0.
    Drop last row (no next-day close available for target).
12  Save to data/processed/dataset_basic_daily.csv.

Usage
-----
    python src/features/build_dataset.py
    python src/features/build_dataset.py --start 2014-01-01 --end 2024-12-31
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INTERIM_DIR = PROJECT_ROOT / "data" / "interim"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

PANEL_FILES = {
    "gdp":    INTERIM_DIR / "gdp_panel.csv",
    "cpi":    INTERIM_DIR / "cpi_panel.csv",
    "rate":   INTERIM_DIR / "central_bank_rate_panel.csv",
    "ca":     INTERIM_DIR / "current_account_panel.csv",
    "forex":  INTERIM_DIR / "forex_panel.csv",
    "equity": INTERIM_DIR / "equity_panel.csv",
}

# Level CPI cols are non-stationary I(1) — ADF test: notebook 01 section 4.
# USA/UK cpi_value trend monotonically 100→130 over 11 years.
# Drop them; keep only YoY forms (stationary, mean-reverting).
CPI_LEVEL_COLS = [
    "USA_cpi_value",
    "USA_cpi_days_since_update",
    "UK_cpi_value",
    "UK_cpi_days_since_update",
]

# All 9 equity indices in the interim panel.
EQUITY_INDICES = [
    "USA_SP500", "USA_NASDAQ_COMPOSITE", "USA_NASDAQ100",
    "USA_RUSSELL2000", "USA_DJI",
    "UK_FTSE100", "UK_FTSE250", "UK_FTSE350", "UK_FTSE_ALL_SHARE",
]

# Indices to drop entirely — multicollinearity, notebook 03 section 6.
# USA_DJI: r=0.954 with USA_SP500
# USA_NASDAQ_COMPOSITE: r=0.992 with USA_NASDAQ100
# UK_FTSE250: r=0.872 with UK_FTSE_ALL_SHARE
# UK_FTSE350: r=0.974 with UK_FTSE100
# UK_FTSE_ALL_SHARE: r=0.993 with UK_FTSE100
# Keep: USA_SP500, USA_NASDAQ100, USA_RUSSELL2000, UK_FTSE100.
REDUNDANT_INDICES = [
    "USA_DJI",
    "USA_NASDAQ_COMPOSITE",
    "UK_FTSE250",
    "UK_FTSE350",
    "UK_FTSE_ALL_SHARE",
]

# Columns that process_*.py already computed and should exist in the merged frame.
REQUIRED_TRANSFORM_COLS = [
    "UK_cpi_yoy_log",                   # from cpi_panel
    "USA_central_bank_rate_value_sqrt",  # from central_bank_rate_panel
    "UK_central_bank_rate_value_sqrt",   # from central_bank_rate_panel
]

# Column suffix patterns that need forward-fill (macro indicators release infrequently).
FFILL_SUFFIXES = ("_value", "_yoy", "_yoy_log", "_sqrt", "_days_since_update")


# ---------------------------------------------------------------------------
# Step helpers
# ---------------------------------------------------------------------------

def load_panels() -> dict[str, pd.DataFrame]:
    panels: dict[str, pd.DataFrame] = {}
    for name, path in PANEL_FILES.items():
        if not path.exists():
            print(f"  [ERROR] Missing interim panel: {path}", file=sys.stderr)
            sys.exit(1)
        df = pd.read_csv(path, index_col="date", parse_dates=True)
        df.index = pd.DatetimeIndex(df.index).normalize()
        panels[name] = df
        print(f"  [OK] {name:6s}  {df.shape[0]} rows x {df.shape[1]} cols")
    return panels


def merge_panels(panels: dict[str, pd.DataFrame], start: str, end: str) -> pd.DataFrame:
    calendar = pd.bdate_range(pd.to_datetime(start), pd.to_datetime(end))
    combined = pd.concat(list(panels.values()), axis=1)
    combined = combined.reindex(calendar)
    combined.index.name = "date"
    return combined


def ffill_macro_cols(df: pd.DataFrame) -> pd.DataFrame:
    cols = [c for c in df.columns if any(c.endswith(s) for s in FFILL_SUFFIXES)]
    df[cols] = df[cols].ffill()
    return df


def compute_equity_returns(df: pd.DataFrame) -> pd.DataFrame:
    for idx in EQUITY_INDICES:
        close_col = f"{idx}_close"
        if close_col in df.columns:
            df[f"{idx}_ret"] = np.log(df[close_col] / df[close_col].shift(1))
    return df


def drop_redundant_equity(df: pd.DataFrame) -> pd.DataFrame:
    to_drop = []
    for idx in REDUNDANT_INDICES:
        to_drop.extend(c for c in df.columns if c.startswith(f"{idx}_"))
    existing = [c for c in to_drop if c in df.columns]
    df = df.drop(columns=existing)
    print(f"  Dropped {len(existing)} cols ({len(REDUNDANT_INDICES)} redundant indices: "
          f"{', '.join(REDUNDANT_INDICES)})")
    return df


def verify_transforms(df: pd.DataFrame) -> None:
    missing = [c for c in REQUIRED_TRANSFORM_COLS if c not in df.columns]
    if missing:
        print(f"  [WARN] Required transform cols not found: {missing}", file=sys.stderr)
    else:
        print(f"  [OK] All {len(REQUIRED_TRANSFORM_COLS)} required transform cols present")


def add_rate_differential(df: pd.DataFrame) -> pd.DataFrame:
    usa_col = "USA_central_bank_rate_value"
    uk_col = "UK_central_bank_rate_value"
    if usa_col not in df.columns or uk_col not in df.columns:
        print("  [WARN] Cannot compute rate_differential — rate cols missing", file=sys.stderr)
        return df
    df["rate_differential"] = df[usa_col] - df[uk_col]
    return df


def add_date_encodings(df: pd.DataFrame) -> pd.DataFrame:
    idx = df.index
    # Integer encodings for tree-based models
    df["day"] = idx.day.astype(int)
    df["month"] = idx.month.astype(int)
    df["weekday"] = idx.weekday.astype(int)  # 0=Monday, 4=Friday
    # Cyclical sin/cos encodings for linear models and MLP
    df["day_sin"] = np.sin(2 * np.pi * idx.day / 31)
    df["day_cos"] = np.cos(2 * np.pi * idx.day / 31)
    df["month_sin"] = np.sin(2 * np.pi * idx.month / 12)
    df["month_cos"] = np.cos(2 * np.pi * idx.month / 12)
    df["weekday_sin"] = np.sin(2 * np.pi * idx.weekday / 5)
    df["weekday_cos"] = np.cos(2 * np.pi * idx.weekday / 5)
    return df


def add_direction_target(df: pd.DataFrame) -> pd.DataFrame:
    if "GBP_USD_close" not in df.columns:
        print("  [ERROR] GBP_USD_close not found — cannot build Direction target", file=sys.stderr)
        sys.exit(1)
    close = df["GBP_USD_close"]
    # Direction(t) = 1 if close(t+1) > close(t), else 0
    df["Direction"] = (close.shift(-1) > close).astype(int)
    # Drop last row — no next-day close available, Direction = NaN before cast
    df = df.iloc[:-1]
    return df


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", default="2014-01-01")
    parser.add_argument("--end", default="2024-12-31")
    parser.add_argument("--out", default=str(PROCESSED_DIR / "dataset_basic_daily.csv"))
    args = parser.parse_args()

    print("=" * 60)
    print("build_dataset.py — Dataset 1: Basic Daily")
    print("=" * 60)

    print("\n[Step 1] Loading 6 interim panels...")
    panels = load_panels()

    print("\n[Step 2] Merging on business calendar...")
    df = merge_panels(panels, args.start, args.end)
    print(f"  Merged: {df.shape[0]} rows x {df.shape[1]} cols  "
          f"({args.start} to {args.end})")

    print("\n[Step 3] Dropping 2014-01-01 (New Year's Day)...")
    df = df.loc[df.index > pd.Timestamp("2014-01-01")]
    print(f"  Rows remaining: {df.shape[0]}")

    print("\n[Step 4] Forward-filling macro columns...")
    df = ffill_macro_cols(df)
    nan_after_ffill = df.isna().sum().sum()
    print(f"  Remaining NaN cells after ffill: {nan_after_ffill:,}")

    print("\n[Step 5] Dropping level CPI cols (non-stationary I(1))...")
    existing_cpi_level = [c for c in CPI_LEVEL_COLS if c in df.columns]
    df = df.drop(columns=existing_cpi_level)
    print(f"  Dropped: {existing_cpi_level}")

    print("\n[Step 6] Computing equity log returns...")
    df = compute_equity_returns(df)
    ret_cols = [c for c in df.columns if c.endswith("_ret")]
    print(f"  Computed {len(ret_cols)} return cols: {ret_cols}")

    print("\n[Step 7] Dropping redundant equity indices...")
    df = drop_redundant_equity(df)
    print(f"  Cols remaining: {df.shape[1]}")

    print("\n[Step 8] Verifying required transform columns...")
    verify_transforms(df)

    print("\n[Step 9] Adding rate_differential...")
    df = add_rate_differential(df)
    if "rate_differential" in df.columns:
        stats = df["rate_differential"].describe()
        print(f"  rate_differential: mean={stats['mean']:.3f}  "
              f"min={stats['min']:.3f}  max={stats['max']:.3f}")

    print("\n[Step 10] Adding date encodings...")
    df = add_date_encodings(df)
    print(f"  Added: day, month, weekday + 6 sin/cos cols")

    print("\n[Step 11] Adding Direction target (drop last row)...")
    df = add_direction_target(df)
    balance = df["Direction"].value_counts(normalize=True).sort_index()
    print(f"  Direction balance: UP={balance.get(1, 0):.1%}  "
          f"DOWN={balance.get(0, 0):.1%}  "
          f"(rows: {len(df)})")

    print("\n[Step 12] Saving Dataset 1...")
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path)

    # Summary
    nan_pct = df.isna().mean().mean() * 100
    print(f"\n{'=' * 60}")
    print(f"DONE")
    print(f"  Output : {out_path}")
    print(f"  Shape  : {df.shape[0]} rows x {df.shape[1]} cols")
    print(f"  NaN    : {nan_pct:.2f}% overall")

    nan_counts = df.isna().sum()
    cols_with_nan = nan_counts[nan_counts > 0]
    if len(cols_with_nan) > 0:
        print(f"\n  Columns with NaN ({len(cols_with_nan)} cols):")
        top = cols_with_nan.sort_values(ascending=False).head(15)
        for col, n in top.items():
            print(f"    {col}: {n} ({n / len(df):.1%})")
        if len(cols_with_nan) > 15:
            print(f"    ... and {len(cols_with_nan) - 15} more")
    else:
        print("  No NaN values — dataset is complete.")
    print("=" * 60)


if __name__ == "__main__":
    main()
