"""
Turn raw USA/UK GDP release histories (from src/data/fetch_gdp.py) into one
business-day-indexed, forward-filled panel. No log/sqrt transform — GDP is not in the
transform list in References/GBPUSD_ML_data_requirements_spec.md section 3.

Output columns: USA_gdp_value, USA_gdp_days_since_update, UK_gdp_value,
UK_gdp_days_since_update.

Usage
-----
    python process_gdp.py --start 2014-01-01 --end 2024-12-31
"""

import argparse
from pathlib import Path

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
NAME = "gdp"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", default="2014-01-01")
    parser.add_argument("--end", default=None)
    parser.add_argument("--raw-dir", default=str(DEFAULT_RAW_DIR))
    parser.add_argument("--out", default=str(DEFAULT_INTERIM_DIR / "gdp_panel.csv"))
    args = parser.parse_args()

    calendar = business_calendar(args.start, args.end)
    panel = pd.DataFrame(index=calendar)
    panel.index.name = "date"

    for block in BLOCKS:
        try:
            releases = load_raw_csv(block, NAME, args.raw_dir)
        except FileNotFoundError as exc:
            print(f"[{block}] SKIPPED — {exc}")
            continue
        known = build_known_as_of(releases, calendar)
        panel[f"{block}_gdp_value"] = known["value"]
        panel[f"{block}_gdp_days_since_update"] = known["days_since_update"]

    if panel.shape[1] == 0:
        print(f"No raw CSVs found in {args.raw_dir} — run src/data/fetch_gdp.py first.")
        return

    save_panel(panel, Path(args.out))


if __name__ == "__main__":
    main()
