"""
Run the full FRED pipeline: fetch_*.py for every indicator type, then process_*.py for
every indicator type — equivalent to running each pair's two scripts by hand, in order.

Indicator types: gdp, cpi, central_bank_rate, current_account (composite_pmi excluded —
not on FRED, see src/data/fred_common.py docstring).

Each fetch_*.py needs outbound network to api.stlouisfed.org. Run this on a personal
machine with internet access, not inside the Cowork sandbox.

Usage
-----
    python run_fred_pipeline.py
    python run_fred_pipeline.py --start 2014-01-01 --end 2024-12-31
    python run_fred_pipeline.py --verify-only      # sanity-check series ids, fetch/process nothing
    python run_fred_pipeline.py --skip-fetch       # only re-run processing on existing raw CSVs
"""

import argparse
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "src" / "data"
FEATURES_DIR = PROJECT_ROOT / "src" / "features"

INDICATORS = ["gdp", "cpi", "central_bank_rate", "current_account"]


def run_script(script_dir: Path, script_name: str, args: list) -> bool:
    cmd = [sys.executable, script_name, *args]
    print(f"\n>>> {script_name} {' '.join(args)}")
    result = subprocess.run(cmd, cwd=script_dir)
    if result.returncode != 0:
        print(f"    FAILED (exit code {result.returncode})")
        return False
    return True


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
        help="only run fetch_*.py --verify-only against every series id, then exit",
    )
    args = parser.parse_args()

    date_args = ["--start", args.start] + (["--end", args.end] if args.end else [])

    if not args.skip_fetch:
        print("=== 1/2 FETCH (needs network) ===")
        for name in INDICATORS:
            script_args = ["--verify-only"] if args.verify_only else date_args
            run_script(DATA_DIR, f"fetch_{name}.py", script_args)
        if args.verify_only:
            return

    print("\n=== 2/2 PROCESS (pure pandas, no network) ===")
    for name in INDICATORS:
        run_script(FEATURES_DIR, f"process_{name}.py", date_args)

    print("\nDone. Raw CSVs -> data/raw/macro/ ; panels -> data/interim/*_panel.csv")


if __name__ == "__main__":
    main()
