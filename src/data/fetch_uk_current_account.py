"""
Fetch UK current account balance from the ONS v1 beta API.

Source: ONS series HBOP, dataset pnbp — "BoP Current Account Balance SA £m" (quarterly,
seasonally adjusted). No API key required.

API status: VERIFIED 2026-06-19. The old ONS v0 API endpoint is permanently retired
(https://developer.ons.gov.uk/retirement/v0api/). This script targets the v1 beta API.

Limitation: the ONS v1 API does not expose per-observation revision history (unlike
FRED's get_series_all_releases). realtime_start is approximated as the single
dataset-level release date in payload["description"]["releaseDate"] — flag this if the
UK current-account column feeds the model directly.

Output
------
    data/raw/macro/UK_current_account.csv — columns: date, realtime_start, value.
    Same schema as USA counterpart; process_current_account.py picks it up automatically.

Usage
-----
    python fetch_uk_current_account.py --raw-dump      # print raw JSON, parse nothing
    python fetch_uk_current_account.py --verify-only   # raw-dump alias, same behaviour
    python fetch_uk_current_account.py --start 2013-01-01 --end 2024-12-31
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd
import requests

from pipeline_log_common import StepLogger

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RAW_DIR = PROJECT_ROOT / "data" / "raw" / "macro"
ONS_ENDPOINT = "https://api.beta.ons.gov.uk/v1/data"
ONS_URI = "/economy/nationalaccounts/balanceofpayments/timeseries/hbop/pnbp"
TAG = "UK_CA"


def _fetch_raw_json(log: StepLogger) -> dict:
    log.info(f"GET {ONS_ENDPOINT}?uri={ONS_URI}")
    resp = requests.get(ONS_ENDPOINT, params={"uri": ONS_URI}, timeout=30)
    log.info(f"HTTP {resp.status_code} — {len(resp.content)} bytes")
    resp.raise_for_status()
    return resp.json()


def _parse_ons_period(series: pd.Series) -> pd.Series:
    def _one(label):
        label = str(label).strip()
        if "Q" in label:
            year_str, q_str = label.split("Q")
            year = int(year_str.strip())
            month = (int(q_str.strip()) - 1) * 3 + 1
            return pd.Timestamp(year=year, month=month, day=1)
        return pd.to_datetime(label, errors="coerce")
    return series.map(_one)


def _parse_ons_response(payload: dict, log: StepLogger) -> pd.DataFrame:
    release_date = (payload.get("description") or {}).get("releaseDate")
    log.info(f"Dataset release date: {release_date}")

    rows = None
    for key in ("quarters", "months", "years"):
        rows = payload.get(key)
        if rows:
            log.info(f"Observations found under '{key}' key: {len(rows)} entries")
            break

    if not rows:
        raise ValueError(
            "No 'quarters'/'months'/'years' key in ONS response — schema may have changed. "
            "Run --raw-dump and adjust _parse_ons_response() to match the actual shape."
        )

    df = pd.DataFrame(rows)
    if "date" not in df.columns or "value" not in df.columns:
        raise ValueError(f"Unexpected row shape from ONS — columns found: {list(df.columns)}")

    df["date"] = _parse_ons_period(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df["realtime_start"] = pd.to_datetime(release_date) if release_date else pd.NaT
    return df[["date", "realtime_start", "value"]].dropna(subset=["date"])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", default="2013-01-01")
    parser.add_argument("--end", default=None)
    parser.add_argument("--out-dir", default=str(DEFAULT_RAW_DIR))
    parser.add_argument("--raw-dump", action="store_true",
                        help="print raw ONS JSON and exit — inspect before trusting parser")
    parser.add_argument("--verify-only", action="store_true",
                        help="alias for --raw-dump, used by run_fred_pipeline.py")
    args = parser.parse_args()

    log = StepLogger(TAG)
    log.info("Source: ONS v1 beta API (no API key required)")
    log.warn(
        "realtime_start is approximated as the dataset-level release date (single value "
        "for all rows) — ONS API has no per-observation revision history like FRED/ALFRED."
    )

    try:
        payload = _fetch_raw_json(log)
    except Exception as exc:  # noqa: BLE001
        log.error("ONS API request failed", exc)
        log.finish(mode="fetch-error", series="HBOP", dataset="pnbp")
        sys.exit(1)

    if args.raw_dump or args.verify_only:
        dumped = json.dumps(payload, indent=2)
        print(dumped[:5000])
        if len(dumped) > 5000:
            print("\n... (truncated at 5000 chars)")
        log.ok("Raw dump complete — inspect output, then re-run without --raw-dump to save CSV")
        log.finish(mode="raw-dump", series="HBOP", dataset="pnbp")
        return

    try:
        df = _parse_ons_response(payload, log)
        total_before = len(df)

        start_dt = pd.to_datetime(args.start)
        end_dt = pd.to_datetime(args.end) if args.end else pd.Timestamp.today()
        df = df[(df["date"] >= start_dt) & (df["date"] <= end_dt)]
        log.info(f"Filtered {total_before} → {len(df)} rows within observation window")

        out_dir = Path(args.out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "UK_current_account.csv"
        df.to_csv(out_path, index=False)

        log.ok(
            f"{len(df)} rows saved → {out_path} "
            "(spot-check a few rows against ons.gov.uk/economy/nationalaccounts/"
            "balanceofpayments/timeseries/hbop/pnbp before trusting full history)",
            rows=len(df), out_path=out_path,
        )

    except Exception as exc:  # noqa: BLE001
        log.error("Parse or save failed", exc)
        log.finish(mode="full", series="HBOP", dataset="pnbp", start=args.start, end=args.end)
        sys.exit(1)

    log.finish(mode="full", series="HBOP", dataset="pnbp", start=args.start, end=args.end)


if __name__ == "__main__":
    main()
