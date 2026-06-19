"""
Collect raw US/UK macroeconomic indicators from FRED for the GBP/USD direction-prediction
project. See References/GBPUSD_ML_data_requirements_spec.md section 2.1 for the indicator
list and rationale.

IMPORTANT — execution environment
----------------------------------
This script makes outbound HTTPS calls to api.stlouisfed.org. It CANNOT run inside the
Cowork sandbox (no outbound network access — verified, see checklist_en.html). Run it on
a personal machine, Google Colab, or Kaggle, then copy the resulting CSVs into
data/raw/macro/ in this repo.

Setup
-----
    pip install fredapi pandas
    # FRED API key already saved at: ML_prediction_project/Key/fred_key.txt
    # (free key: https://fred.stlouisfed.org/docs/api/api_key.html)

Usage
-----
    python fetch_fred.py --verify-only          # sanity-check every series id first
    python fetch_fred.py --start 2014-01-01 --end 2024-12-31

Output
------
One CSV per indicator in data/raw/macro/, named "{BLOCK}_{indicator}.csv", with columns:
    date            observation period (e.g. month-end or quarter-end)
    realtime_start  date the value was actually published/revised (release date)
    value           the reported value, raw scale, no transforms applied

Raw data is saved as-is (no forward-fill, no transforms) — that belongs to
src/features/build_macro_panel.py, run as a separate step.
"""

import argparse
from pathlib import Path

import pandas as pd
from fredapi import Fred

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_KEY_FILE = PROJECT_ROOT / "Key" / "fred_key.txt"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "raw" / "macro"

# ---------------------------------------------------------------------------
# Series configuration
# ---------------------------------------------------------------------------
# "confidence" is the author's confidence that the FRED series id below is correct,
# based on general knowledge of FRED's catalogue — NOT verified against a live API call
# (this environment has no network access). Run with --verify-only before trusting
# anything tagged "medium" or "low": it prints each series' real title/units/frequency
# via fred.get_series_info() so the ids can be eyeballed before a full download.
#
# id = None means "not available as a clean FRED series" — source it separately
# (see References/GBPUSD_ML_data_requirements_spec.md section 7).
SERIES_IDS = {
    "USA": {
        "gdp": {
            "id": "GDP",
            "freq": "Q",
            "confidence": "high",
            "note": "Nominal GDP, SAAR, billions USD (BEA via FRED).",
        },
        "cpi": {
            "id": "CPIAUCSL",
            "freq": "M",
            "confidence": "high",
            "note": "CPI-U, all items, seasonally adjusted. CPI YoY is derived from this "
                    "in build_macro_panel.py, not fetched as a separate series.",
        },
        "central_bank_rate": {
            "id": "DFF",
            "freq": "D",
            "confidence": "high",
            "note": "Effective Federal Funds Rate, daily. Swap for DFEDTARU (target rate "
                    "upper bound) if a cleaner step-function series is preferred.",
        },
        "current_account": {
            "id": "IEABC",
            "freq": "Q",
            "confidence": "medium",
            "note": "Balance on current account (BEA). Verify with --verify-only.",
        },
        "composite_pmi": {
            "id": None,
            "freq": "M",
            "confidence": "n/a",
            "note": "Composite PMI is a markit/ISM product, not published on FRED for "
                    "either block. Source from investing.com (manual download).",
        },
    },
    "UK": {
        "gdp": {
            "id": "CLVMNACSCAB1GQUK",
            "freq": "Q",
            "confidence": "medium",
            "note": "Real GDP, OECD Quarterly National Accounts mirror on FRED. Verify "
                    "with --verify-only — OECD country-suffix conventions vary.",
        },
        "cpi": {
            "id": "GBRCPIALLMINMEI",
            "freq": "M",
            "confidence": "medium",
            "note": "CPI all items, OECD MEI mirror on FRED. Verify with --verify-only.",
        },
        "central_bank_rate": {
            "id": "IRSTCI01GBM156N",
            "freq": "M",
            "confidence": "medium",
            "note": "OECD 'immediate rate' series used as a proxy for the BoE Bank Rate "
                    "— monthly only, less granular than the US DFF series. Verify with "
                    "--verify-only; consider scraping bankofengland.co.uk directly for a "
                    "true event-dated Bank Rate series instead.",
        },
        "current_account": {
            "id": None,
            "freq": "Q",
            "confidence": "n/a",
            "note": "No confirmed FRED ticker. Run fred.search('United Kingdom current "
                    "account balance') interactively to find one, or source from ONS "
                    "directly (see spec doc section 7).",
        },
        "composite_pmi": {
            "id": None,
            "freq": "M",
            "confidence": "n/a",
            "note": "Not published on FRED. Source from investing.com (manual download).",
        },
    },
}


def load_fred(api_key_file: Path) -> Fred:
    if not api_key_file.exists():
        raise FileNotFoundError(
            f"FRED API key file not found at {api_key_file}. Register a free key at "
            "https://fred.stlouisfed.org/docs/api/api_key.html and save it there "
            "(single line, no quotes)."
        )
    return Fred(api_key_file=str(api_key_file))


def verify_series_ids(fred: Fred) -> None:
    """Print title/units/frequency for every configured series id so they can be
    eyeballed against expectations before a full download. Series with id=None are
    skipped (already flagged as needing a non-FRED source)."""
    for block, indicators in SERIES_IDS.items():
        print(f"\n=== {block} ===")
        for name, cfg in indicators.items():
            series_id = cfg["id"]
            if series_id is None:
                print(f"  [{name}] SKIPPED — {cfg['note']}")
                continue
            try:
                info = fred.get_series_info(series_id)
                print(
                    f"  [{name}] {series_id} (confidence={cfg['confidence']})\n"
                    f"      title     : {info.get('title')}\n"
                    f"      units     : {info.get('units')}\n"
                    f"      frequency : {info.get('frequency')}\n"
                    f"      obs range : {info.get('observation_start')} .. "
                    f"{info.get('observation_end')}"
                )
            except Exception as exc:  # noqa: BLE001 — surfaced to the user, not swallowed
                print(f"  [{name}] {series_id} -> ERROR: {exc}")


def fetch_indicator_releases(fred: Fred, series_id: str) -> pd.DataFrame:
    """Fetch the full revision history for one series: every (observation date,
    release date, value) triple. Using all-releases (not just the latest) is what
    lets build_macro_panel.py forward-fill using the date a value actually became
    known, instead of the observation period — avoiding look-ahead bias."""
    df = fred.get_series_all_releases(series_id)
    df = df.rename(columns={"date": "date", "realtime_start": "realtime_start"})
    df["date"] = pd.to_datetime(df["date"])
    df["realtime_start"] = pd.to_datetime(df["realtime_start"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    return df[["date", "realtime_start", "value"]].sort_values("realtime_start")


def save_indicator(df: pd.DataFrame, block: str, name: str, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"{block}_{name}.csv"
    df.to_csv(out_path, index=False)
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", default="2013-01-01", help="Observation start date (YYYY-MM-DD)")
    parser.add_argument("--end", default=None, help="Observation end date (YYYY-MM-DD), default = today")
    parser.add_argument("--key-file", default=str(DEFAULT_KEY_FILE), help="Path to the FRED API key file")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUTPUT_DIR), help="Output directory for raw CSVs")
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Only print series info for sanity-checking, do not download or save anything",
    )
    args = parser.parse_args()

    fred = load_fred(Path(args.key_file))

    if args.verify_only:
        verify_series_ids(fred)
        return

    start = pd.to_datetime(args.start)
    end = pd.to_datetime(args.end) if args.end else pd.Timestamp.today()
    out_dir = Path(args.out_dir)

    for block, indicators in SERIES_IDS.items():
        for name, cfg in indicators.items():
            series_id = cfg["id"]
            if series_id is None:
                print(f"[{block}/{name}] skipped — {cfg['note']}")
                continue
            print(f"[{block}/{name}] fetching {series_id} ...")
            try:
                df = fetch_indicator_releases(fred, series_id)
            except Exception as exc:  # noqa: BLE001
                print(f"[{block}/{name}] FAILED: {exc}")
                continue
            df = df[(df["date"] >= start) & (df["date"] <= end)]
            out_path = save_indicator(df, block, name, out_dir)
            print(f"[{block}/{name}] saved {len(df)} rows -> {out_path}")


if __name__ == "__main__":
    main()
