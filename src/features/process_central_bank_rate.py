"""
Turn raw USA/UK central bank rate release histories (from
src/data/fetch_central_bank_rate.py) into one business-day-indexed, forward-filled
panel. Applies the sqrt transform to both blocks, per
References/GBPUSD_ML_data_requirements_spec.md section 3.

Output columns: USA_central_bank_rate_value, USA_central_bank_rate_days_since_update,
USA_central_bank_rate_value_sqrt, UK_central_bank_rate_value,
UK_central_bank_rate_days_since_update, UK_central_bank_rate_value_sqrt.

Usage
-----
    python process_central_bank_rate.py --start 2014-01-01 --end 2024-12-31
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
NAME = "central_bank_rate"
SQRT_COLUMNS = {"USA_central_bank_rate_value", "UK_central_bank_rate_value"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", default="2014-01-01")
    parser.add_argument("--end", default=None)
    parser.add_argument("--raw-dir", default=str(DEFAULT_RAW_DIR))
    parser.add_argument(
        "--out", default=str(DEFAULT_INTERIM_DIR / "central_bank_rate_panel.csv")
    )
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
        panel[f"{block}_central_bank_rate_value"] = known["value"]
        panel[f"{block}_central_bank_rate_days_since_update"] = known["days_since_update"]

    if panel.shape[1] == 0:
        print(
            f"No raw CSVs found in {args.raw_dir} — run "
            "src/data/fetch_central_bank_rate.py first."
        )
        return

    for col in SQRT_COLUMNS:
        if col in panel.columns:
            panel[f"{col}_sqrt"] = np.sqrt(panel[col])

    save_panel(panel, Path(args.out))


if __name__ == "__main__":
    main()
