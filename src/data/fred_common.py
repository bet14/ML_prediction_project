"""
Shared helpers for the per-indicator fetch_*.py scripts in this folder (one script per
FRED indicator type: gdp, cpi, central_bank_rate, current_account). Holds the only
fredapi-touching logic that those scripts would otherwise each duplicate.

Composite PMI is intentionally absent from this whole fetch_*/process_* family: it is
not published on FRED for either block and must be sourced from investing.com manually
(see References/GBPUSD_ML_data_requirements_spec.md section 7).

Execution environment: needs outbound network to api.stlouisfed.org -- run on a personal
machine / Colab / Kaggle, not inside the Cowork sandbox (no network there).
"""

from pathlib import Path

import pandas as pd
from fredapi import Fred

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_KEY_FILE = PROJECT_ROOT / "Key" / "fred_key.txt"
DEFAULT_RAW_DIR = PROJECT_ROOT / "data" / "raw" / "macro"


def load_fred(api_key_file: Path = DEFAULT_KEY_FILE) -> Fred:
    api_key_file = Path(api_key_file)
    if not api_key_file.exists():
        raise FileNotFoundError(
            f"FRED API key file not found at {api_key_file}. Register a free key at "
            "https://fred.stlouisfed.org/docs/api/api_key.html and save it there "
            "(single line, no quotes)."
        )
    return Fred(api_key_file=str(api_key_file))


def fetch_indicator_releases(
    fred: Fred,
    series_id: str,
    realtime_start: str = "2000-01-01",
    realtime_end: str = None,
    chunk_years: int = 3,
    log_fn=print,
) -> pd.DataFrame:
    """Full revision history for one series: every (observation date, release date,
    value) triple. Using all-releases (not just the latest) is what lets the matching
    process_*.py script forward-fill using the date a value actually became known,
    instead of the observation period -- avoiding look-ahead bias.

    Fetched in `chunk_years`-year realtime-window chunks rather than one call over the
    full default range, for two reasons:
    1. FRED caps a single all-releases request at 2000 vintage dates; for a daily,
       barely-revised series (e.g. the Fed Funds Rate, DFF) every new daily print
       counts as its own vintage, so even a ~10-year window can exceed that cap.
    2. ALFRED (the vintage archive) doesn't have vintage data for every series going
       all the way back to `realtime_start` -- querying a window that predates a given
       series' ALFRED coverage raises "series does not exist in ALFRED" even though the
       series itself is fine. Chunks with no ALFRED coverage are skipped (not fatal);
       only fail if literally no chunk returned anything.

    log_fn: callable(str) used for chunk-level progress messages. Defaults to print so
    existing callers (old combined fetch_*.py scripts) are unaffected; pass StepLogger.info
    from per-block scripts to route messages through the structured logger.
    """
    realtime_start = pd.to_datetime(realtime_start)
    realtime_end = pd.to_datetime(realtime_end) if realtime_end else pd.Timestamp.today()

    frames = []
    chunk_num = 0
    window_start = realtime_start
    while window_start <= realtime_end:
        chunk_num += 1
        window_end = min(window_start + pd.DateOffset(years=chunk_years), realtime_end)
        try:
            chunk = fred.get_series_all_releases(
                series_id,
                realtime_start=window_start.strftime("%Y-%m-%d"),
                realtime_end=window_end.strftime("%Y-%m-%d"),
            )
        except ValueError as exc:
            log_fn(
                f"  chunk {chunk_num} ({window_start.date()} → {window_end.date()}): "
                f"no ALFRED data — skipped ({exc})"
            )
            chunk = None
        if chunk is not None and len(chunk):
            frames.append(chunk)
            log_fn(
                f"  chunk {chunk_num} ({window_start.date()} → {window_end.date()}): "
                f"{len(chunk)} rows"
            )
        elif chunk is not None:
            log_fn(
                f"  chunk {chunk_num} ({window_start.date()} → {window_end.date()}): 0 rows"
            )
        window_start = window_end + pd.Timedelta(days=1)

    if not frames:
        raise ValueError(f"No data returned for series id: {series_id} in any chunk")

    df = pd.concat(frames, ignore_index=True)
    df["date"] = pd.to_datetime(df["date"])
    df["realtime_start"] = pd.to_datetime(df["realtime_start"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.drop_duplicates(subset=["date", "realtime_start"])
    return df[["date", "realtime_start", "value"]].sort_values("realtime_start")


def save_raw_csv(df: pd.DataFrame, block: str, name: str, raw_dir: Path = DEFAULT_RAW_DIR) -> Path:
    raw_dir = Path(raw_dir)
    raw_dir.mkdir(parents=True, exist_ok=True)
    out_path = raw_dir / f"{block}_{name}.csv"
    df.to_csv(out_path, index=False)
    return out_path


def verify_series_id(fred: Fred, series_id: str, log_fn=print) -> None:
    """Print title/units/frequency for one series id -- run with --verify-only before
    trusting any id tagged 'medium' confidence in a fetch_*.py script."""
    try:
        info = fred.get_series_info(series_id)
        log_fn(
            f"  title     : {info.get('title')}\n"
            f"  units     : {info.get('units')}\n"
            f"  frequency : {info.get('frequency')}\n"
            f"  obs range : {info.get('observation_start')} .. {info.get('observation_end')}"
        )
    except Exception as exc:  # noqa: BLE001 -- surfaced to the user, not swallowed
        log_fn(f"  ERROR: {exc}")
