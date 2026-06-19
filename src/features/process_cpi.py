"""
Turn raw USA/UK CPI level release histories (from src/data/fetch_cpi.py) into one
business-day-indexed, forward-filled panel, plus a derived CPI YoY series. Applies the
log transform on UK CPI YoY only, per References/GBPUSD_ML_data_requirements_spec.md
section 3.

CPI YoY derivation: take the latest known value per observation month (last revision),
compute pct-change over 12 months on that clean monthly series, and assume each YoY
figure becomes known at the same time as the *current* month's first release (the
year-ago value is, by then, long since public — a simplifying assumption, not an exact
revision-by-revision replay).

Output columns: USA_cpi_value, USA_cpi_days_since_update, USA_cpi_yoy,
USA_cpi_yoy_days_since_update, UK_cpi_value, UK_cpi_days_since_update, UK_cpi_yoy,
UK_cpi_yoy_days_since_update, UK_cpi_yoy_log.

Usage
-----
    python process_cpi.py --start 2014-01-01 --end 2024-12-31
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from panel_common import (
    DEFAULT_INTERIM_DIR,
    DEFAULT_RAW_DIR,
    build_known_as_of,
    business_calendar,
    load_raw_csv,
    save_panel,
)

BLOCKS = ["USA", "UK"]
NAME = "cpi"
LOG_COLUMNS = {"UK_cpi_yoy"}


def compute_yoy_releases(level_releases: pd.DataFrame) -> pd.DataFrame:
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", default="2014-01-01")
    parser.add_argument("--end", default=None)
    parser.add_argument("--raw-dir", default=str(DEFAULT_RAW_DIR))
    parser.add_argument("--out", default=str(DEFAULT_INTERIM_DIR / "cpi_panel.csv"))
    args = parser.parse_args()

    calendar = business_calendar(args.start, args.end)
    panel = pd.DataFrame(index=calendar)
    panel.index.name = "date"

    levels = {}
    for block in BLOCKS:
        try:
            releases = load_raw_csv(block, NAME, args.raw_dir)
        except FileNotFoundError as exc:
            print(f"[{block}] SKIPPED — {exc}")
            continue
        known = build_known_as_of(releases, calendar)
        panel[f"{block}_cpi_value"] = known["value"]
        panel[f"{block}_cpi_days_since_update"] = known["days_since_update"]
        levels[block] = releases

    if panel.shape[1] == 0:
        print(f"No raw CSVs found in {args.raw_dir} — run src/data/fetch_cpi.py first.")
        return

    for block, releases in levels.items():
        yoy_releases = compute_yoy_releases(releases)
        known = build_known_as_of(yoy_releases, calendar)
        panel[f"{block}_cpi_yoy"] = known["value"]
        panel[f"{block}_cpi_yoy_days_since_update"] = known["days_since_update"]

    for col in LOG_COLUMNS:
        if col in panel.columns:
            panel[f"{col}_log"] = np.log(panel[col])

    save_panel(panel, Path(args.out))


if __name__ == "__main__":
    main()
