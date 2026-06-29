"""
Parse the ONS UK GDP timeseries (ABMI — Gross Domestic Product: chained volume measures,
seasonally adjusted £m) from a manually-downloaded ONS CSV and write it to the standard
raw-data format used by the rest of the pipeline.

Replaces fetch_uk_gdp.py for the 2014-2024 window after the FRED mirror
(CLVMNACSCAB1GQUK) was discontinued at 2020-07-01.

Input
-----
    data/raw/macro/UK_gdp_ons_raw.csv — raw ONS download.
    File format: 8 metadata header rows, then annual rows ("YYYY"), then quarterly rows
    ("YYYY Q#"). Only the quarterly section is extracted.
    Download source: https://www.ons.gov.uk/economy/grossdomesticproductgdp/timeseries/abmi

realtime_start approximation
-----------------------------
The ONS CSV is a single-snapshot download with no per-observation revision history
(unlike FRED/ALFRED). realtime_start is approximated per row as:
    end_of_quarter + 60 days
ONS typically publishes the second GDP estimate ~55 days after quarter end; 60 days is a
conservative lag that avoids look-ahead bias.

Output
------
    data/raw/macro/UK_gdp.csv — columns: date, realtime_start, value.
    Same schema as the FRED-sourced file; process_gdp.py picks it up automatically.

Usage
-----
    python fetch_uk_gdp_ons.py --start 2013-01-01 --end 2024-12-31
    python fetch_uk_gdp_ons.py                          # defaults: 2013-01-01 to today
"""

import argparse
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RAW_DIR = PROJECT_ROOT / "data" / "raw" / "macro"
DEFAULT_INPUT = DEFAULT_RAW_DIR / "UK_gdp_ons_raw.csv"
RELEASE_LAG_DAYS = 60


def parse_ons_gdp_csv(path: Path) -> pd.DataFrame:
    """Extract quarterly rows from the ONS GDP timeseries CSV.

    Skips the first 8 metadata header lines and annual rows (no 'Q' in label).
    Row format: "YYYY Q#","value"
    """
    rows = []
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i < 8:
                continue
            line = line.strip()
            if not line:
                continue
            parts = line.split('","')
            if len(parts) != 2:
                continue
            label = parts[0].strip('"')
            value_str = parts[1].strip('"')
            if "Q" not in label:
                continue
            try:
                year_str, q_str = label.split("Q")
                year = int(year_str.strip())
                quarter = int(q_str.strip())
                month = (quarter - 1) * 3 + 1
                date = pd.Timestamp(year=year, month=month, day=1)
                value = float(value_str.replace(",", ""))
            except (ValueError, TypeError):
                continue
            rows.append({"date": date, "value": value})
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", default="2013-01-01")
    parser.add_argument("--end", default=None)
    parser.add_argument("--input", default=str(DEFAULT_INPUT))
    parser.add_argument("--out-dir", default=str(DEFAULT_RAW_DIR))
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"ERROR: input file not found: {input_path}")
        print("       Download ABMI from ons.gov.uk and save as UK_gdp_ons_raw.csv")
        sys.exit(1)

    print(f"Parsing {input_path.name} ...")
    df = parse_ons_gdp_csv(input_path)
    if df.empty:
        print("ERROR: no quarterly rows found — check file format")
        sys.exit(1)
    print(f"  Extracted {len(df)} quarterly rows ({df['date'].min().date()} to {df['date'].max().date()})")

    df["realtime_start"] = df["date"] + pd.offsets.QuarterEnd(0) + pd.Timedelta(days=RELEASE_LAG_DAYS)

    start_dt = pd.to_datetime(args.start)
    end_dt = pd.to_datetime(args.end) if args.end else pd.Timestamp.today()
    before = len(df)
    df = df[(df["date"] >= start_dt) & (df["date"] <= end_dt)]
    print(f"  Filtered {before} -> {len(df)} rows for {args.start} to {end_dt.date()}")

    df = df[["date", "realtime_start", "value"]].sort_values("date").reset_index(drop=True)

    out_path = Path(args.out_dir) / "UK_gdp.csv"
    df.to_csv(out_path, index=False)
    print(f"  Saved -> {out_path}")
    print(f"  date range     : {df['date'].min().date()} to {df['date'].max().date()}")
    print(f"  realtime_start : {df['realtime_start'].min().date()} to {df['realtime_start'].max().date()}")
    print(f"  value range    : {df['value'].min():.0f} to {df['value'].max():.0f} (£m, chained vol.)")


if __name__ == "__main__":
    main()
