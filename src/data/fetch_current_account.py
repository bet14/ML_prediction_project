"""
Fetch USA current account balance release history from FRED.

Series ids
----------
    USA: IEABC   — Balance on current account (BEA). Medium confidence — run
                   --verify-only before trusting.
    UK:  none — no confirmed FRED ticker. Run fred.search('United Kingdom current
                account balance') interactively to find a candidate, or source it
                directly from ONS (see References/GBPUSD_ML_data_requirements_spec.md
                section 7). process_current_account.py leaves the UK column absent
                until a raw CSV exists.

Output
------
data/raw/macro/USA_current_account.csv — columns: date, realtime_start, value. Raw, no
forward-fill/transform (that's process_current_account.py).

Usage
-----
    python fetch_current_account.py --verify-only
    python fetch_current_account.py --start 2013-01-01 --end 2024-12-31
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

SERIES_IDS = {"USA": "IEABC"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", default="2013-01-01")
    parser.add_argument("--end", default=None)
    parser.add_argument("--key-file", default=str(DEFAULT_KEY_FILE))
    parser.add_argument("--out-dir", default=str(DEFAULT_RAW_DIR))
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()

    fred = load_fred(args.key_file)
    print("[UK] skipped — no confirmed FRED ticker, see module docstring.")

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
        out_path = save_raw_csv(df, block, "current_account", args.out_dir)
        print(f"[{block}] saved {len(df)} rows -> {out_path}")


if __name__ == "__main__":
    main()
