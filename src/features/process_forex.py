"""
Build data/interim/forex_panel.csv from the 13 raw OHLC CSVs in data/raw/forex/.

Each raw file has columns: date, open, high, low, close, volume
Volume is excluded (yfinance FX volume = 0; spot FX has no consolidated tape — see
References/GBPUSD_ML_data_requirements_spec.md section 2.3 and References/CLAUDE.md item 7).

Output: one row per business day (pd.bdate_range), 13 pairs x 4 OHLC cols = 52 columns.
Non-trading days (weekends, market holidays) are forward-filled from the last trading day.

No look-ahead bias concern: market prices are publicly available intraday on the trading day.

Usage
-----
    python process_forex.py --start 2014-01-01 --end 2024-12-31
"""

import argparse
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RAW_DIR = PROJECT_ROOT / "data" / "raw" / "forex"
DEFAULT_OUT_PATH = PROJECT_ROOT / "data" / "interim" / "forex_panel.csv"

OHLC_COLS = ["open", "high", "low", "close"]

PAIRS = [
    "AUD_USD", "EUR_USD", "EUR_GBP",
    "GBP_AUD", "GBP_CAD", "GBP_CHF", "GBP_JPY", "GBP_NZD", "GBP_USD",
    "NZD_USD", "USD_CAD", "USD_CHF", "USD_JPY",
]


def load_pair(name: str, raw_dir: Path) -> pd.DataFrame:
    path = raw_dir / f"{name}.csv"
    if not path.exists():
        raise FileNotFoundError(f"{path} not found — run fetch_forex_wip.py first.")
    df = pd.read_csv(path, parse_dates=["date"], index_col="date")
    missing = [c for c in OHLC_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"{name}: missing columns {missing}")
    return df[OHLC_COLS]


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
    for name in PAIRS:
        try:
            df = load_pair(name, raw_dir)
        except FileNotFoundError as exc:
            print(f"  [SKIP] {name} — {exc}")
            skipped.append(name)
            continue

        # Align to business-day calendar; ffill to cover non-trading days / holidays
        df_aligned = df.reindex(calendar, method="ffill")

        for col in OHLC_COLS:
            panel[f"{name}_{col}"] = df_aligned[col]

        n_missing = df_aligned[OHLC_COLS[0]].isna().sum()
        print(f"  [{name}] {len(df)} raw rows → {len(df_aligned)} aligned"
              f"  (ffilled {n_missing} non-trading days)")

    if panel.shape[1] == 0:
        print("No pairs loaded — check data/raw/forex/.")
        return

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    panel.to_csv(out_path)

    n_pairs = len(PAIRS) - len(skipped)
    print(f"\nSaved forex panel: {panel.shape[0]} rows x {panel.shape[1]} cols "
          f"({n_pairs}/13 pairs) -> {out_path}")
    if skipped:
        print(f"Skipped: {skipped}")


if __name__ == "__main__":
    main()
