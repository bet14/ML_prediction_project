"""
Turn the raw per-indicator release histories saved by src/data/fetch_fred.py into one
business-day-indexed macro panel: forward-filled, "days since last update" added,
CPI YoY derived, and the log/sqrt transforms from
References/GBPUSD_ML_data_requirements_spec.md (section 3) applied.

Look-ahead bias
----------------
Forward-fill uses `realtime_start` (the date a value was actually published), not the
observation period. A value is only visible to the model on or after the day it was
really released — matching checklist_en.html stage s2: "Use release date for macro
indicators (avoid look-ahead bias)".

Execution environment
----------------------
Pure pandas, no network calls — this script CAN run inside the Cowork sandbox, as long
as the CSVs from fetch_fred.py already exist in data/raw/macro/ (copy them in after
running fetch_fred.py on a personal machine).

Usage
-----
    python build_macro_panel.py --start 2014-01-01 --end 2024-12-31
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RAW_DIR = PROJECT_ROOT / "data" / "raw" / "macro"
DEFAULT_OUT_PATH = PROJECT_ROOT / "data" / "interim" / "macro_panel.csv"

# Indicators present as raw CSVs from fetch_fred.py (id=None ones — PMI, UK current
# account — are simply absent and skipped here; add them once sourced separately).
INDICATORS = {
    "USA": ["gdp", "cpi", "central_bank_rate", "current_account"],
    "UK": ["gdp", "cpi", "central_bank_rate"],
}

# Transform rules from the spec doc, section 3.
LOG_COLUMNS = {"UK_cpi_yoy"}
SQRT_COLUMNS = {"USA_central_bank_rate_value", "UK_central_bank_rate_value"}


def load_releases(block: str, name: str, raw_dir: Path) -> pd.DataFrame:
    path = raw_dir / f"{block}_{name}.csv"
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found — run src/data/fetch_fred.py on a machine with network "
            "access first, then copy the CSVs into data/raw/macro/."
        )
    df = pd.read_csv(path, parse_dates=["date", "realtime_start"])
    return df


def build_known_as_of(releases: pd.DataFrame, calendar: pd.DatetimeIndex) -> pd.DataFrame:
    """For each calendar day, attach the latest value whose realtime_start (release
    date) is on or before that day, plus how many days ago it was released."""
    rel = (
        releases.dropna(subset=["realtime_start", "value"])
        .sort_values("realtime_start")
        .drop_duplicates(subset="realtime_start", keep="last")
    )
    cal_df = pd.DataFrame({"asof_date": pd.DatetimeIndex(calendar)}).sort_values("asof_date")
    merged = pd.merge_asof(
        cal_df,
        rel[["realtime_start", "value"]],
        left_on="asof_date",
        right_on="realtime_start",
        direction="backward",
    )
    merged["days_since_update"] = (merged["asof_date"] - merged["realtime_start"]).dt.days
    return merged.set_index("asof_date")[["value", "days_since_update"]]


def compute_yoy_releases(level_releases: pd.DataFrame) -> pd.DataFrame:
    """Derive a YoY-growth release table from a monthly index-level release table.

    Approach: take the latest known value per observation month (last revision),
    compute pct-change over 12 months on that clean monthly series, and assume each
    YoY figure becomes known at the same time as the *current* month's first release
    (the year-ago value is, by then, long since public — a standard simplifying
    assumption, not an exact revision-by-revision replay).
    """
    monthly_level = (
        level_releases.sort_values("realtime_start")
        .groupby("date", as_index=True)
        .last()["value"]
        .sort_index()
    )
    yoy = monthly_level.pct_change(12) * 100.0

    first_release_date = (
        level_releases.sort_values("realtime_start").groupby("date")["realtime_start"].min()
    )

    out = pd.DataFrame({"date": yoy.index, "value": yoy.values})
    out["realtime_start"] = out["date"].map(first_release_date)
    return out.dropna(subset=["realtime_start", "value"])


def apply_transforms(panel: pd.DataFrame) -> pd.DataFrame:
    for col in LOG_COLUMNS:
        if col in panel.columns:
            panel[f"{col}_log"] = np.log(panel[col])
    for col in SQRT_COLUMNS:
        if col in panel.columns:
            panel[f"{col}_sqrt"] = np.sqrt(panel[col])
    return panel


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", default="2014-01-01")
    parser.add_argument("--end", default=None)
    parser.add_argument("--raw-dir", default=str(DEFAULT_RAW_DIR))
    parser.add_argument("--out", default=str(DEFAULT_OUT_PATH))
    args = parser.parse_args()

    start = pd.to_datetime(args.start)
    end = pd.to_datetime(args.end) if args.end else pd.Timestamp.today()
    raw_dir = Path(args.raw_dir)
    calendar = pd.bdate_range(start, end)

    panel = pd.DataFrame(index=calendar)
    panel.index.name = "date"

    cpi_levels = {}
    for block, names in INDICATORS.items():
        for name in names:
            try:
                releases = load_releases(block, name, raw_dir)
            except FileNotFoundError as exc:
                print(f"[{block}/{name}] SKIPPED — {exc}")
                continue
            known = build_known_as_of(releases, calendar)
            panel[f"{block}_{name}_value"] = known["value"]
            panel[f"{block}_{name}_days_since_update"] = known["days_since_update"]
            if name == "cpi":
                cpi_levels[block] = releases

    if panel.shape[1] == 0:
        print(
            f"No raw CSVs found at all in {raw_dir} — run src/data/fetch_fred.py on a "
            "machine with network access first (see its docstring), then copy the "
            "resulting CSVs here before re-running this script."
        )
        return

    for block, releases in cpi_levels.items():
        yoy_releases = compute_yoy_releases(releases)
        known = build_known_as_of(yoy_releases, calendar)
        panel[f"{block}_cpi_yoy"] = known["value"]
        panel[f"{block}_cpi_yoy_days_since_update"] = known["days_since_update"]

    panel = apply_transforms(panel)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    panel.to_csv(out_path)
    print(f"Saved macro panel: {panel.shape[0]} rows x {panel.shape[1]} cols -> {out_path}")


if __name__ == "__main__":
    main()
