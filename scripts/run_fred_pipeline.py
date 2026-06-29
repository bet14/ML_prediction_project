"""
Run the full macro data pipeline: fetch raw CSVs from FRED/ONS for each block and
indicator, then build interim panels for each indicator.

Fetch scripts (src/data/fetch_[block]_[indicator].py) — one script per block per
indicator, each with its own console logging and a JSON record in pipeline_run_log.jsonl.
Process scripts (src/features/process_[indicator].py) — one script per indicator,
reads whichever raw CSVs exist and produces an interim panel.

Fetch order (run sequentially — each block can fail independently):
  1. fetch_usa_gdp.py          (FRED: GDP)
  2. fetch_uk_gdp.py           (FRED: CLVMNACSCAB1GQUK — discontinued at 2020-07)
  3. fetch_usa_cpi.py          (FRED: CPIAUCSL)
  4. fetch_uk_cpi.py           (FRED: GBRCPIALLMINMEI — ~15 months stale)
  5. fetch_usa_central_bank_rate.py   (FRED: DFF, daily)
  6. fetch_uk_central_bank_rate.py    (FRED: IRSTCI01GBM156N, monthly)
  7. fetch_usa_current_account.py     (FRED: IEABC)
  8. fetch_uk_current_account.py      (ONS v1 beta API: HBOP/pnbp — no API key)

Process order:
  1. process_gdp.py            → data/interim/gdp_panel.csv
  2. process_cpi.py            → data/interim/cpi_panel.csv
  3. process_central_bank_rate.py     → data/interim/central_bank_rate_panel.csv
  4. process_current_account.py       → data/interim/current_account_panel.csv

Flags
-----
    --skip-fetch       only re-run process_*.py on existing raw CSVs (no network needed)
    --verify-only      run each fetch script in verify/raw-dump mode then exit
    --block USA|UK     restrict fetch to one block only (process always runs for both)

Network: fetch_*.py scripts need outbound network (FRED or ONS). Run on a personal
machine. process_*.py scripts are pure pandas — they run in Cowork once CSVs exist.

Each invocation appends one JSON line to reports/pipeline_run_log.jsonl with a
"pipeline": "macro" tag; individual scripts each append their own per-script record.
"""

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src" / "data"))
from pipeline_log_common import append_run_log, run_script  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "src" / "data"
FEATURES_DIR = PROJECT_ROOT / "src" / "features"

FETCH_SCRIPTS = [
    ("fetch_usa_gdp.py",             "USA"),
    ("fetch_uk_gdp.py",              "UK"),
    ("fetch_usa_cpi.py",             "USA"),
    ("fetch_uk_cpi.py",              "UK"),
    ("fetch_usa_central_bank_rate.py", "USA"),
    ("fetch_uk_central_bank_rate.py",  "UK"),
    ("fetch_usa_current_account.py", "USA"),
    ("fetch_uk_current_account.py",  "UK"),
]

PROCESS_SCRIPTS = [
    "process_gdp.py",
    "process_cpi.py",
    "process_central_bank_rate.py",
    "process_current_account.py",
]


def _divider(title: str) -> None:
    width = 60
    print(f"\n{'=' * width}")
    print(f"  {title}")
    print(f"{'=' * width}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", default="2014-01-01")
    parser.add_argument("--end", default=None)
    parser.add_argument(
        "--skip-fetch", action="store_true",
        help="only run process_*.py (no network needed) — use once raw CSVs already exist",
    )
    parser.add_argument(
        "--verify-only", action="store_true",
        help="run fetch_*.py --verify-only / --raw-dump for every script, then exit",
    )
    parser.add_argument(
        "--block", choices=["USA", "UK"], default=None,
        help="restrict fetching to one block; process scripts always run for both",
    )
    args = parser.parse_args()

    date_args = ["--start", args.start] + (["--end", args.end] if args.end else [])
    mode = "verify-only" if args.verify_only else ("skip-fetch" if args.skip_fetch else "full")
    run_started = datetime.now(timezone.utc)
    steps: list[dict] = []

    def finish() -> None:
        append_run_log({
            "timestamp": run_started.isoformat(timespec="seconds"),
            "pipeline": "macro",
            "mode": mode,
            "block_filter": args.block,
            "start_arg": args.start,
            "end_arg": args.end,
            "steps": steps,
            "success": all(s["ok"] for s in steps),
        })

    if not args.skip_fetch:
        _divider("1/2  FETCH  (needs network — FRED / ONS)")
        for script_name, block in FETCH_SCRIPTS:
            if args.block and block != args.block:
                print(f"\n  [skipped by --block {args.block}] {script_name}")
                continue
            script_args = ["--verify-only"] if args.verify_only else date_args
            steps.append(run_script(DATA_DIR, script_name, script_args))

        if args.verify_only:
            finish()
            return

    _divider("2/2  PROCESS  (pure pandas — runs in Cowork)")
    for script_name in PROCESS_SCRIPTS:
        steps.append(run_script(FEATURES_DIR, script_name, date_args))

    n_ok = sum(1 for s in steps if s["ok"])
    n_total = len(steps)
    _divider(f"DONE  {n_ok}/{n_total} steps succeeded")
    print(f"  Raw CSVs  → data/raw/macro/")
    print(f"  Panels    → data/interim/*_panel.csv")
    print(f"  Run log   → reports/pipeline_run_log.jsonl")
    finish()


if __name__ == "__main__":
    main()
