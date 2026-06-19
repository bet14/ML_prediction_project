"""
Fetch USA + UK GDP release history from FRED.

Series ids
----------
    USA: GDP                  — Nominal GDP, SAAR, billions USD (BEA). High confidence.
    UK:  CLVMNACSCAB1GQUK     — Real GDP, OECD QNA mirror on FRED. Medium confidence —
                                 run --verify-only before trusting.

Output
------
data/raw/macro/USA_gdp.csv, data/raw/macro/UK_gdp.csv — columns: date, realtime_start,
value. Raw, no forward-fill/transform (that's process_gdp.py).

Usage
-----
    python fetch_gdp.py --verify-only
    python fetch_gdp.py --start 2013-01-01 --end 2024-12-31
"""

import argparse

import pandas as pd

from fred_common import (
    DEFAULT_KEY_FILE,
    DEFAULT_RAW_DIR,
    fetch_indicator_releases,
    load_fred,
    save_raw_csv,
    verify_series_id,
)

SERIES_IDS = {"USA": "GDP", "UK": "CLVMNACSCAB1GQUK"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", default="2013-01-01")
    parser.add_argument("--end", default=None)
    parser.add_argument("--key-file", default=str(DEFAULT_KEY_FILE))
    parser.add_argument("--out-dir", default=str(DEFAULT_RAW_DIR))
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()

    fred = load_fred(args.key_file)

    if args.verify_only:
        for block, series_id in SERIES_IDS.items():
            print(f"[{block}] {series_id}")
            verify_series_id(fred, series_id)
        return

    start = pd.to_datetime(args.start)
    end = pd.to_datetime(args.end) if args.end else pd.Timestamp.today()

    for block, series_id in SERIES_IDS.items():
        print(f"[{block}] fetching {series_id} ...")
        try:
            df = fetch_indicator_releases(fred, series_id)
        except Exception as exc:  # noqa: BLE001 — keep going to the next block
            print(f"[{block}] FAILED: {exc}")
            continue
        df = df[(df["date"] >= start) & (df["date"] <= end)]
        out_path = save_raw_csv(df, block, "gdp", args.out_dir)
        print(f"[{block}] saved {len(df)} rows -> {out_path}")


if __name__ == "__main__":
    main()
