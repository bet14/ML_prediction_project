"""
Turn raw Composite PMI release histories (USA/UK -- from a working
src/data/fetch_composite_pmi_wip.py implementation once one exists, or from a manual
investing.com export, see that module's docstring) into one business-day-indexed,
forward-filled panel. No raw CSV exists yet for either block as of this writing -- this
script prints a message and exits without writing anything until at least one does.

No log/sqrt transform -- composite PMI is not in the transform list in
References/GBPUSD_ML_data_requirements_spec.md section 3 (revisit once the data exists
and a transform decision is made).

Output columns: USA_composite_pmi_value, USA_composite_pmi_days_since_update,
UK_composite_pmi_value, UK_composite_pmi_days_since_update (only for whichever block's
raw CSV is present -- mirrors how process_current_account.py handles the missing UK
column).

Usage
-----
    python process_composite_pmi.py --start 2014-01-01 --end 2024-12-31
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

BLOCKS = ["USA", "UK"]  # both expected missing until fetch_composite_pmi_wip.py is implemented
NAME = "composite_pmi"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", default="2014-01-01")
    parser.add_argument("--end", default=None)
    parser.add_argument("--raw-dir", default=str(DEFAULT_RAW_DIR))
    parser.add_argument(
        "--out", default=str(DEFAULT_INTERIM_DIR / "composite_pmi_panel.csv")
    )
    args = parser.parse_args()

    calendar = business_calendar(args.start, args.end)
    panel = pd.DataFrame(index=calendar)
    panel.index.name = "date"

    for block in BLOCKS:
        try:
            releases = load_raw_csv(block, NAME, args.raw_dir)
        except FileNotFoundError:
            print(
                f"[{block}] SKIPPED -- no data/raw/macro/{block}_composite_pmi.csv yet. "
                "See src/data/fetch_composite_pmi_wip.py docstring for the manual-export "
                "fallback."
            )
            continue
        known = build_known_as_of(releases, calendar)
        panel[f"{block}_composite_pmi_value"] = known["value"]
        panel[f"{block}_composite_pmi_days_since_update"] = known["days_since_update"]

    if panel.shape[1] == 0:
        print(
            f"No raw CSVs found in {args.raw_dir} -- see "
            "src/data/fetch_composite_pmi_wip.py for the manual-export fallback."
        )
        return

    save_panel(panel, Path(args.out))


if __name__ == "__main__":
    main()
