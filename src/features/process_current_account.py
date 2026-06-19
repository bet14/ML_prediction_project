"""
Turn the raw USA current account release history (from
src/data/fetch_current_account.py) into one business-day-indexed, forward-filled panel.
No log/sqrt transform — current account is not in the transform list in
References/GBPUSD_ML_data_requirements_spec.md section 3.

UK current account is absent on purpose: no confirmed FRED ticker exists (see
src/data/fetch_current_account.py docstring). The UK_current_account_value /
UK_current_account_days_since_update columns are simply not produced until a raw CSV
for it exists at data/raw/macro/UK_current_account.csv — add it there (sourced from ONS
or a verified FRED id) and this script will pick it up automatically.

Output columns: USA_current_account_value, USA_current_account_days_since_update.

Usage
-----
    python process_current_account.py --start 2014-01-01 --end 2024-12-31
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

BLOCKS = ["USA", "UK"]  # UK is expected to be missing today; see module docstring.
NAME = "current_account"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", default="2014-01-01")
    parser.add_argument("--end", default=None)
    parser.add_argument("--raw-dir", default=str(DEFAULT_RAW_DIR))
    parser.add_argument(
        "--out", default=str(DEFAULT_INTERIM_DIR / "current_account_panel.csv")
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
        panel[f"{block}_current_account_value"] = known["value"]
        panel[f"{block}_current_account_days_since_update"] = known["days_since_update"]

    if panel.shape[1] == 0:
        print(
            f"No raw CSVs found in {args.raw_dir} — run "
            "src/data/fetch_current_account.py first."
        )
        return

    save_panel(panel, Path(args.out))


if __name__ == "__main__":
    main()
