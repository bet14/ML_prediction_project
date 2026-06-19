"""
Fetch UK current account balance from the ONS (Office for National Statistics) v1
beta API, as a candidate replacement for the missing FRED ticker (see
fetch_current_account.py docstring: no UK series has been confirmed on FRED).

STATUS: VERIFIED 2026-06-19. The original endpoint this script targeted
(api.ons.gov.uk/timeseries/.../dataset/.../data, the "v0 API") is permanently
retired by ONS -- see https://developer.ons.gov.uk/retirement/v0api/. That is why
it returned an empty body in every earlier attempt; it was never a network problem.
The correct live endpoint is the v1 beta API below, confirmed by fetching it directly
and inspecting the real JSON (quarterly rows from "1955 Q1" onward, real GBP-million
values, dataset metadata title/cdid/unit all matching "BoP Current Account Balance SA
£m"). parse_ons_response() below has been updated to match that real shape.

Candidate series
-----------------
    UK: HBOP, dataset pnbp -- "BoP Current Account Balance SA £m" (quarterly,
        seasonally adjusted). No API key required.
    Endpoint: https://api.beta.ons.gov.uk/v1/data
              ?uri=/economy/nationalaccounts/balanceofpayments/timeseries/hbop/pnbp

Known difference vs. FRED/ALFRED
---------------------------------
The ONS v1 API does not expose a per-observation vintage/revision history the way
FRED's get_series_all_releases() does (see fred_common.py). A single call returns the
dataset's *current* values plus one dataset-level release-date field at
payload["description"]["releaseDate"] (confirmed live, e.g.
"2026-03-30T23:00:00.000Z", with payload["description"]["nextRelease"] giving the next
scheduled update). This script approximates `realtime_start` as that single release
date for every row, which is materially weaker than the true per-release ALFRED-style
history used elsewhere in this pipeline -- flag this if the UK current-account column
ends up feeding the model.

Output
------
data/raw/macro/UK_current_account.csv -- same columns as fetch_current_account.py
(date, realtime_start, value), so process_current_account.py (BLOCKS=["USA","UK"])
picks it up automatically with no code changes.

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
ONS_ENDPOINT = "https://api.beta.ons.gov.uk/v1/data"
ONS_URI = "/economy/nationalaccounts/balanceofpayments/timeseries/hbop/pnbp"


def fetch_raw_json(endpoint: str = ONS_ENDPOINT, uri: str = ONS_URI) -> dict:
    resp = requests.get(endpoint, params={"uri": uri}, timeout=30)
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
    """Parse the ONS v1 API timeseries response -- VERIFIED against a live response on
    2026-06-19. Observations are nested under 'quarters'/'months'/'years' (whichever
    matches the series frequency; the other two are present as empty lists, not
    missing keys) as a list of {"date": "1955 Q1", "value": "-22", ...} dicts; current
    account is quarterly so 'quarters' is tried first. The release date is NOT at the
    top level -- it lives at payload["description"]["releaseDate"]."""
    release_date = (payload.get("description") or {}).get("releaseDate")

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
    print(
        f"[UK] saved {len(df)} rows -> {out_path}  (verified parser against the live "
        "ONS v1 API -- still spot-check a few rows against "
        "ons.gov.uk/economy/nationalaccounts/balanceofpayments/timeseries/hbop/pnbp "
        "before trusting the full history)"
    )


if __name__ == "__main__":
    main()
