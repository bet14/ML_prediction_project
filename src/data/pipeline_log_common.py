"""
Shared run-logging helpers for every fetch/process pipeline in this project (macro,
forex, equity, ...). Extracted 2026-06-19 from run_fred_pipeline.py (which had its own
private copies of append_run_log()/run_script()) so the new forex/equity WIP scripts
can append to the same log file without duplicating this logic a third time.

Design
------
One shared file, reports/pipeline_run_log.jsonl, one JSON line per invocation, for ALL
domains -- not one log file per domain. Each record carries a "pipeline" field
("macro" | "forex" | "equity") so a dashboard (or `grep`) can filter by domain while
still being able to see everything in chronological order in a single file. This
mirrors exactly what run_fred_pipeline.py already did for macro, just generalized.

STATUS as of 2026-06-19: extracted and used by run_fred_pipeline.py (macro, refactored
to import from here instead of defining its own copies -- behavior unchanged) and
referenced by fetch_forex_wip.py / fetch_equity_wip.py (each calls append_run_log()
directly from its own main(), tagged "forex"/"equity" -- there is no run_forex_pipeline.py
/ run_equity_pipeline.py orchestrator yet, since those fetch scripts are themselves still
WIP/unverified end-to-end; see each script's own STATUS docstring line).
"""

import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUN_LOG_PATH = PROJECT_ROOT / "reports" / "pipeline_run_log.jsonl"


def run_script(script_dir: Path, script_name: str, args: list) -> dict:
    """Run one fetch_*.py/process_*.py as a subprocess and return a step record for
    the run log. Child stdout/stderr stream straight to the console (no capture)."""
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
    reports/ folder must never fail the actual data pipeline."""
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError as exc:  # noqa: BLE001 -- logging must never break the pipeline
        print(f"    [run-log] could not write {log_path}: {exc}")


def make_run_record(pipeline: str, mode: str, steps: list, **extra) -> dict:
    """Build the standard record shape with a 'pipeline' tag so reports/pipeline_run_log.jsonl
    stays a single shared file across macro/forex/equity instead of fragmenting into
    one log per domain. `extra` is merged in as-is (e.g. start_arg, end_arg, pair, ticker)."""
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "pipeline": pipeline,
        "mode": mode,
        "steps": steps,
        "success": all(s.get("ok", False) for s in steps) if steps else None,
    }
    record.update(extra)
    return record


class StepLogger:
    """Per-script console logger + log-file appender.

    Prints timestamped messages to stdout so the operator can see exactly which step
    is running and whether it succeeded or failed. Appends one structured JSON record
    to reports/pipeline_run_log.jsonl when finish() is called.

    Usage
    -----
        log = StepLogger("USA_GDP")
        log.info("Fetching series GDP ...")
        log.info("  chunk 1/4: 2014-01-01 → 2016-12-31 ... 42 rows")
        log.ok("146 rows saved", rows=146, out_path=Path("data/raw/macro/USA_gdp.csv"))
        log.finish(series_id="GDP", start="2014-01-01", end="2024-12-31")
    """

    _LEVELS = {"INFO": "INFO ", "WARN": "WARN ", "OK": "OK   ", "ERROR": "ERROR"}

    def __init__(self, tag: str, pipeline: str = "macro") -> None:
        self._tag = tag
        self._pipeline = pipeline
        self._t0 = time.monotonic()
        self._ts_start = datetime.now(timezone.utc)
        self._ok: bool | None = None
        self._rows: int | None = None
        self._out_path: str | None = None
        self._error: str | None = None

    def _emit(self, level: str, msg: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        label = self._LEVELS.get(level, level)
        print(f"[{ts}] [{self._tag}] {label} {msg}", flush=True)

    def info(self, msg: str) -> None:
        self._emit("INFO", msg)

    def warn(self, msg: str) -> None:
        self._emit("WARN", msg)

    def ok(self, msg: str, rows: int | None = None, out_path=None) -> None:
        self._ok = True
        self._rows = rows
        self._out_path = str(out_path) if out_path else None
        self._emit("OK", msg)

    def error(self, msg: str, exc: Exception | None = None) -> None:
        self._ok = False
        detail = f"{msg}: {exc}" if exc else msg
        self._error = detail
        self._emit("ERROR", detail)

    def finish(self, **extra) -> dict:
        """Append structured record to pipeline_run_log.jsonl and return it."""
        elapsed = round(time.monotonic() - self._t0, 2)
        record: dict = {
            "timestamp": self._ts_start.isoformat(timespec="seconds"),
            "pipeline": self._pipeline,
            "tag": self._tag,
            "ok": self._ok,
            "elapsed_s": elapsed,
        }
        if self._rows is not None:
            record["rows"] = self._rows
        if self._out_path:
            record["out_path"] = self._out_path
        if self._error:
            record["error"] = self._error
        record.update(extra)
        append_run_log(record)
        return record
