"""
WIP -- fetch an alternative UK CPI series directly from the ONS (Office for National
Statistics) v1 beta API, as a candidate replacement for the stale FRED-sourced UK leg
of fetch_cpi.py (FRED series GBRCPIALLMINMEI, currently ~15 months behind the USA
file -- see fetch_cpi.py docstring and README.md's data/raw/macro/ table).

STATUS: API schema VERIFIED 2026-06-19; this specific series' full response NOT fully
inspected end-to-end. Endpoint and series id were confirmed real (ONS publishes D7BT
under dataset mm23, titled "CPI INDEX 00: ALL ITEMS 2015=100", monthly, currently
released through June 2026). A live fetch of this exact URL returned real monthly rows
("1988 JAN" = 48.4, "2013 FEB" = 97.8, ...) confirming the row shape and date-label
format -- but the response is long enough (~38 years of monthly data) that the fetch
tool used during this investigation truncated it before reaching the
payload["description"] block at the tail, so the releaseDate field was not directly
observed for THIS series. That field's location (payload["description"]["releaseDate"])
*was* directly confirmed for two other series on the same v1 API (the official docs'
worked example, and this project's own fetch_current_account_uk_wip.py target) -- same
endpoint, same response contract -- so parse_ons_response() below relies on that as a
verified-by-analogy assumption, not a per-series-unique guess. Run --raw-dump on a
machine with normal network access and grep the tail of the output for "description"
to close this last gap before fully trusting the release-date column.

Candidate series
-----------------
    UK: D7BT, dataset mm23 -- "CPI INDEX 00: ALL ITEMS 2015=100" (monthly, index level,
        base 2015=100). No API key required.
    Endpoint: https://api.beta.ons.gov.uk/v1/data
              ?uri=/economy/inflationandpriceindices/timeseries/d7bt/mm23

Why this is NOT wired into the pipeline yet
--------------------------------------------
fetch_cpi.py's UK series (GBRCPIALLMINMEI, an OECD MEI mirror on FRED) and this ONS
D7BT series almost certainly use different base years / rebasing conventions, so the
raw index *levels* are not directly comparable -- only CPI YoY (computed downstream in
process_cpi.py from pct-change) should be expected to roughly agree. Swapping this in
to replace the stale UK_cpi.csv is therefore a deliberate decision for a human to make
after comparing the two series' YoY figures over an overlapping window, not something
this script does automatically:

    1. Run this script -- it writes data/raw/macro/UK_cpi_ons_alt.csv, a SEPARATE file
       from UK_cpi.csv (does not overwrite the existing FRED-sourced data).
    2. Compare YoY derived from both sources over a shared date range.
    3. If acceptable, either rename this output to UK_cpi.csv (overwriting the stale
       FRED copy) or change fetch_cpi.py to call this script for the UK leg --
       process_cpi.py itself needs no change either way since it just reads whatever
       is at data/raw/macro/UK_cpi.csv.

Known difference vs. FRED/ALFRED
---------------------------------
Same caveat as fetch_current_account_uk_wip.py: the ONS v1 API has no per-observation
ALFRED-style revision history. `realtime_start` is approximated as a single
dataset-level release date for every row.

Output
------
data/raw/macro/UK_cpi_ons_alt.csv -- columns date, realtime_start, value. Intentionally
NOT named UK_cpi.csv -- see "Why this is NOT wired into the pipeline yet" above.

Usage
-----
    python fetch_cpi_uk_alt_wip.py --raw-dump      # print raw JSON, parse nothing
    python fetch_cpi_uk_alt_wip.py --start 2013-01-01 --end 2024-12-31
"""

import argparse
import json
from pathlib import Path

import pandas as pd
import requests

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RAW_DIR = PROJECT_ROOT / "data" / "raw" / "macro"
ONS_ENDPOINT = "https://api.beta.ons.gov.uk/v1/data"
ONS_URI = "/economy/inflationandpriceindices/timeseries/d7bt/mm23"


def fetch_raw_json(endpoint: str = ONS_ENDPOINT, uri: str = ONS_URI) -> dict:
    resp = requests.get(endpoint, params={"uri": uri}, timeout=30)
    resp.raise_for_status()
    return resp.json()


def _parse_ons_period(series: pd.Series) -> pd.Series:
    """ONS monthly labels look like '1988 JAN' rather than ISO dates; quarterly labels
    look like '2024 Q1'. pandas.to_datetime parses the monthly 'YYYY MON' form directly
    (verified: '1988 JAN' -> 1988-01-01), so only the quarterly form needs a manual
    branch. CPI is monthly, so the fallback branch is what actually fires in practice,
    but both are handled for parity with fetch_current_account_uk_wip.py."""

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
    """Parse the ONS v1 API timeseries response. Row shape and date-label format
    VERIFIED against a live response on 2026-06-19 (see module docstring); the
    release-date field location is verified-by-analogy against two sibling series on
    the same API, not directly observed for this specific series."""
    release_date = (payload.get("description") or {}).get("releaseDate")

    rows = None
    for key in ("months", "quarters", "years"):
        rows = payload.get(key)
        if rows:
            break
    if not rows:
        raise ValueError(
            "No 'months'/'quarters'/'years' key found in the ONS response -- the "
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
             "parse_ons_response(), and specifically check the tail for the "
             "'description' block to confirm releaseDate for this series",
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
    out_path = out_dir / "UK_cpi_ons_alt.csv"
    df.to_csv(out_path, index=False)
    print(
        f"[UK] saved {len(df)} rows -> {out_path}  (does NOT overwrite UK_cpi.csv -- "
        "compare YoY against the existing FRED-sourced file before deciding whether to "
        "swap it in; see module docstring)"
    )


if __name__ == "__main__":
    main()
