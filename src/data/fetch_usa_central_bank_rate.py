"""
Fetch USA central bank policy rate (Fed Funds Rate) release history from FRED.

Series
------
    USA: DFF — Effective Federal Funds Rate, daily. High confidence.
    Alternative: DFEDTARU (target rate upper bound) for a cleaner step-function series.

Note: DFF is a daily series. Its 3-year chunks (~1095 days each) will each produce
~1000+ rows — chunking is necessary to stay under FRED's 2000-vintage-date cap.

Output
------
    data/raw/macro/USA_central_bank_rate.csv — columns: date, realtime_start, value.
    Raw; no forward-fill or transform (sqrt applied in process_central_bank_rate.py).

Usage
-----
    python fetch_usa_central_bank_rate.py --verify-only
    python fetch_usa_central_bank_rate.py --start 2013-01-01 --end 2024-12-31
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd

from fred_common import DEFAULT_KEY_FILE, DEFAULT_RAW_DIR, fetch_indicator_releases, load_fred, save_raw_csv, verify_series_id
from pipeline_log_common import StepLogger

BLOCK = "USA"
INDICATOR = "central_bank_rate"
SERIES_ID = "DFF"
TAG = f"{BLOCK}_RATE"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", default="2013-01-01")
    parser.add_argument("--end", default=None)
    parser.add_argument("--key-file", default=str(DEFAULT_KEY_FILE))
    parser.add_argument("--out-dir", default=str(DEFAULT_RAW_DIR))
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()

    log = StepLogger(TAG)

    try:
        fred = load_fred(args.key_file)
    except FileNotFoundError as exc:
        log.error("FRED API key not found", exc)
        log.finish(mode="init", series_id=SERIES_ID)
        sys.exit(1)

    if args.verify_only:
        log.info(f"Verifying series {SERIES_ID} ...")
        verify_series_id(fred, SERIES_ID, log_fn=log.info)
        log.ok("Verify complete")
        log.finish(mode="verify-only", series_id=SERIES_ID)
        return

    end_str = args.end or "today"
    log.info(f"Series: {SERIES_ID} (daily) | range: {args.start} → {end_str}")
    log.info("Daily series — expect ~1000+ rows per 3-year chunk; this will take a moment ...")

    try:
        df = fetch_indicator_releases(
            fred, SERIES_ID,
            realtime_start=args.start,
            realtime_end=args.end,
            log_fn=log.info,
        )
        start_dt = pd.to_datetime(args.start)
        end_dt = pd.to_datetime(args.end) if args.end else pd.Timestamp.today()
        before = len(df)
        df = df[(df["date"] >= start_dt) & (df["date"] <= end_dt)]
        log.info(f"Filtered {before} → {len(df)} rows within observation window")

        out_path = save_raw_csv(df, BLOCK, INDICATOR, args.out_dir)
        log.ok(f"{len(df)} rows saved → {out_path}", rows=len(df), out_path=out_path)

    except Exception as exc:  # noqa: BLE001
        log.error("Fetch failed", exc)
        log.finish(mode="full", series_id=SERIES_ID, start=args.start, end=args.end)
        sys.exit(1)

    log.finish(mode="full", series_id=SERIES_ID, start=args.start, end=args.end)


if __name__ == "__main__":
    main()
