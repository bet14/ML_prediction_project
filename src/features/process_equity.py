"""
Build data/interim/equity_panel.csv from the 9 raw OHLCV CSVs in data/raw/equity/.

Each raw file has columns: date, open, high, low, close, volume
Volume is included for equity (unlike forex) and sqrt-transformed per
References/GBPUSD_ML_data_requirements_spec.md section 3.

Output: one row per business day (pd.bdate_range), 9 indices x 5 OHLCV cols = 45 columns,
plus 9 sqrt-transformed volume columns = 54 columns total.
Non-trading days (weekends, market holidays) are forward-filled from the last trading day.

Usage
-----
    python process_equity.py --start 2014-01-01 --end 2024-12-31
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RAW_DIR = PROJECT_ROOT / "data" / "raw" / "equity"
DEFAULT_OUT_PATH = PROJECT_ROOT / "data" / "interim" / "equity_panel.csv"

OHLCV_COLS = ["open", "high", "low", "close", "volume"]

INDICES = [
    "USA_SP500", "USA_NASDAQ_COMPOSITE", "USA_NASDAQ100",
    "USA_RUSSELL2000", "USA_DJI",
    "UK_FTSE100", "UK_FTSE250", "UK_FTSE350", "UK_FTSE_ALL_SHARE",
]


def load_index(name: str, raw_dir: Path) -> pd.DataFrame:
    path = raw_dir / f"{name}.csv"
    if not path.exists():
        raise FileNotFoundError(f"{path} not found — run fetch_equity_wip.py first.")
    df = pd.read_csv(path, parse_dates=["date"], index_col="date")
    # Normalize timezone-naive timestamps (equity CSVs may have "2014-01-02 00:00:00")
    df.index = pd.DatetimeIndex(df.index).normalize()
    missing = [c for c in OHLCV_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"{name}: missing columns {missing}")
    return df[OHLCV_COLS]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", default="2014-01-01")
    parser.add_argument("--end", default="2024-12-31")
    parser.add_argument("--raw-dir", default=str(DEFAULT_RAW_DIR))
    parser.add_argument("--out", default=str(DEFAULT_OUT_PATH))
    args = parser.parse_args()

    start = pd.to_datetime(args.start)
    end = pd.to_datetime(args.end)
    raw_dir = Path(args.raw_dir)
    calendar = pd.bdate_range(start, end)

    panel = pd.DataFrame(index=calendar)
    panel.index.name = "date"

    skipped = []
    for name in INDICES:
        try:
            df = load_index(name, raw_dir)
        except FileNotFoundError as exc:
            print(f"  [SKIP] {name} — {exc}")
            skipped.append(name)
            continue

        df_aligned = df.reindex(calendar, method="ffill")

        for col in OHLCV_COLS:
            panel[f"{name}_{col}"] = df_aligned[col]

        # sqrt transform on volume per spec section 3
        vol_col = f"{name}_volume"
        panel[f"{vol_col}_sqrt"] = np.sqrt(panel[vol_col].clip(lower=0))

        n_missing = df_aligned["close"].isna().sum()
        print(f"  [{name}] {len(df)} raw rows → {len(df_aligned)} aligned"
              f"  (ffilled {n_missing} non-trading days)")

    if panel.shape[1] == 0:
        print("No indices loaded — check data/raw/equity/.")
        return

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    panel.to_csv(out_path)

    n_indices = len(INDICES) - len(skipped)
    print(f"\nSaved equity panel: {panel.shape[0]} rows x {panel.shape[1]} cols "
          f"({n_indices}/9 indices) -> {out_path}")
    if skipped:
        print(f"Skipped: {skipped}")


if __name__ == "__main__":
    main()
