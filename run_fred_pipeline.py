"""
Run the full FRED pipeline: fetch_*.py for every indicator type, then process_*.py for
every indicator type — equivalent to running each pair's two scripts by hand, in order.

Indicator types: gdp, cpi, central_bank_rate, current_account (composite_pmi excluded —
not on FRED, see src/data/fred_common.py docstring).

Each fetch_*.py needs outbound network to api.stlouisfed.org. Run this on a personal
machine with internet access, not inside the Cowork sandbox.

Run logging
-----------
Every invocation appends one JSON line to reports/pipeline_run_log.jsonl: timestamp,
mode, --start/--end, per-script returncode + duration, overall success. This is the
only persisted run history in the repo (the console output itself is never saved) —
a dashboard can tail the last N lines of that file to show real "last N runs" instead
of inferring a single run from file mtimes. Logging failures never abort the pipeline.

Usage
-----
    python run_fred_pipeline.py
    python run_fred_pipeline.py --start 2014-01-01 --end 2024-12-31
    python run_fred_pipeline.py --verify-only      # sanity-check series ids, fetch/process nothing
    python run_fred_pipeline.py --skip-fetch       # only re-run processing on existing raw CSVs
"""

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "src" / "data"
FEATURES_DIR = PROJECT_ROOT / "src" / "features"
RUN_LOG_PATH = PROJECT_ROOT / "reports" / "pipeline_run_log.jsonl"

INDICATORS = ["gdp", "cpi", "central_bank_rate", "current_account"]


def run_script(script_dir: Path, script_name: str, args: list) -> dict:
    """Run one fetch_*.py/process_*.py and return a step record for the run log.
    Child stdout/stderr stream straight to the console as before (no capture) — the
    per-chunk ALFRED warnings and per-block "saved N rows" lines stay visible live."""
    cmd = [sys.executable, script_name, *args]
    print(f"\n>>> {script_name} {' '.join(args)}")
    t0 = time.monotonic()
    result = subprocess.run(cmd, cwd=script_dir)
    duration_s = round(time.monotonic() - t0, 2)
    ok = result.returncode == 0
    if not ok:
        print(f"    FAILED (exit code {result.returncode})")
    return {
        "script": script_name,
        "args": args,
        "returncode": result.returncode,
        "ok": ok,
        "duration_s": duration_s,
    }


def append_run_log(record: dict, log_path: Path = RUN_LOG_PATH) -> None:
    """Append one JSON line per pipeline invocation. Best-effort: a missing/read-only
    reports/ folder must not fail the actual data pipeline."""
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError as exc:  # noqa: BLE001 — logging must never break the pipeline
        print(f"    [run-log] could not write {log_path}: {exc}")


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
    mode = "verify-only" if args.verify_only else ("skip-fetch" if args.skip_fetch else "full")
    run_started = datetime.now(timezone.utc)
    steps: list[dict] = []

    def finish() -> None:
        append_run_log({
            "timestamp": run_started.isoformat(timespec="seconds"),
            "mode": mode,
            "start_arg": args.start,
            "end_arg": args.end,
            "steps": steps,
            "success": all(s["ok"] for s in steps),
        })

    if not args.skip_fetch:
        print("=== 1/2 FETCH (needs network) ===")
        for name in INDICATORS:
            script_args = ["--verify-only"] if args.verify_only else date_args
            steps.append(run_script(DATA_DIR, f"fetch_{name}.py", script_args))
        if args.verify_only:
            finish()
            return

    print("\n=== 2/2 PROCESS (pure pandas, no network) ===")
    for name in INDICATORS:
        steps.append(run_script(FEATURES_DIR, f"process_{name}.py", date_args))

    print("\nDone. Raw CSVs -> data/raw/macro/ ; panels -> data/interim/*_panel.csv")
    finish()


if __name__ == "__main__":
    main()
