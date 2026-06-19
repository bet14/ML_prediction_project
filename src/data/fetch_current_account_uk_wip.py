"""
WIP -- fetch UK current account balance from the ONS (Office for National Statistics)
open API, as a candidate replacement for the missing FRED ticker (see
fetch_current_account.py docstring: no UK series has been confirmed on FRED).

STATUS: UNVERIFIED. The ONS endpoint below was identified from ONS's own published
series/dataset ids during the source investigation in this project, but the live JSON
response was never successfully fetched and inspected in that session (the fetch tool
available there returned an empty body for this URL, and no browser was available to
confirm). Run this script with --raw-dump on a machine with normal network access and
READ the printed JSON before trusting parse_ons_response() below.

Candidate series
-----------------
    UK: HBOP, dataset pnbp -- "Balance of payments, current account" (quarterly, GBP
        millions). No API key required.
    Endpoint: https://api.ons.gov.uk/timeseries/hbop/dataset/pnbp/data

Known difference vs. FRED/ALFRED
---------------------------------
The ONS timeseries API does not expose a per-observation vintage/revision history the
way FRED's get_series_all_releases() does (see fred_common.py). A single call returns
the dataset's *current* values plus one dataset-level release-date field in the response
metadata (exact key name unverified -- inspect with --raw-dump). This script
approximates `realtime_start` as that single release date for every row, which is
materially weaker than the true per-release ALFRED-style history used elsewhere in this
pipeline -- flag this if the UK current-account column ends up feeding the model.

Output
------
data/raw/macro/UK_current_account.csv -- same columns as fetch_current_account.py
(date, realtime_start, value), so process_current_account.py (BLOCKS=["USA","UK"])
picks it up automatically with no code changes once this file is confirmed working.

Usage
-----
    python fetch_current_account_uk_wip.py --raw-dump      # print raw JSON, parse nothing
    python fetch_current_account_uk_wip.py --start 2013-01-01 --end 2024-12-31
"""

import argparse
import json
from pathlib import Path

import pandas as pd
import requests

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RAW_DIR = PROJECT_ROOT / "data" / "raw" / "macro"
ONS_ENDPOINT = "https://api.ons.gov.uk/timeseries/hbop/dataset/pnbp/data"


def fetch_raw_json(endpoint: str = ONS_ENDPOINT) -> dict:
    resp = requests.get(endpoint, timeout=30)
    resp.raise_for_status()
    return resp.json()


def _parse_ons_period(series: pd.Series) -> pd.Series:
    """ONS quarterly labels look like '2024 Q1' rather than ISO dates -- convert to the
    first day of the quarter. Falls back to pd.to_datetime for any other format."""

    def _one(label):
        label = str(label).strip()
        if "Q" in label:
            year_str, q_str = label.split("Q")
            year = int(year_str.strip())
            month = (int(q_str.strip()) - 1) * 3 + 1
            return pd.Timestamp(year=year, month=month, day=1)
        return pd.to_datetime(label, errors="coerce")

    return series.map(_one)


def parse_ons_response(payload: dict) -> pd.DataFrame:
    """Best-effort parse of the ONS timeseries response shape documented at
    https://developer.ons.gov.uk/ -- UNVERIFIED against a live response. ONS typically
    nests observations under 'quarters'/'months'/'years' as a list of
    {"date": "2024 Q1", "value": "..."} dicts; current account is quarterly so
    'quarters' is tried first."""
    release_date = payload.get("releaseDate") or payload.get("release_date")

    rows = None
    for key in ("quarters", "months", "years"):
        rows = payload.get(key)
        if rows:
            break
    if not rows:
        raise ValueError(
            "No 'quarters'/'months'/'years' key found in the ONS response -- the "
            "schema differs from what this script expects. Run --raw-dump and adjust "
            "parse_ons_response() to match the actual shape."
        )

    df = pd.DataFrame(rows)
    if "date" not in df.columns or "value" not in df.columns:
        raise ValueError(f"Unexpected row shape from ONS, columns found: {list(df.columns)}")

    df["date"] = _parse_ons_period(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df["realtime_start"] = pd.to_datetime(release_date) if release_date else pd.NaT
    return df[["date", "realtime_start", "value"]].dropna(subset=["date"])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", default="2013-01-01")
    parser.add_argument("--end", default=None)
    parser.add_argument("--out-dir", default=str(DEFAULT_RAW_DIR))
    parser.add_argument(
        "--raw-dump", action="store_true",
        help="print the raw ONS JSON response and exit -- inspect this before trusting "
             "parse_ons_response()",
    )
    args = parser.parse_args()

    payload = fetch_raw_json()

    if args.raw_dump:
        dumped = json.dumps(payload, indent=2)
        print(dumped[:5000])
        if len(dumped) > 5000:
            print("\n... (truncated at 5000 chars) -- inspect the full structure before parsing.")
        return

    df = parse_ons_response(payload)
    start = pd.to_datetime(args.start)
    end = pd.to_datetime(args.end) if args.end else pd.Timestamp.today()
    df = df[(df["date"] >= start) & (df["date"] <= end)]

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "UK_current_account.csv"
    df.to_csv(out_path, index=False)
    print(f"[UK] saved {len(df)} rows -> {out_path}  (UNVERIFIED parser -- spot-check the values)")


if __name__ == "__main__":
    main()
