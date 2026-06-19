"""
Shared helpers for the per-indicator process_*.py scripts in this folder (one script
per FRED indicator type: gdp, cpi, central_bank_rate, current_account). Holds the
forward-fill logic that those scripts would otherwise each duplicate.

Look-ahead bias
----------------
Forward-fill uses `realtime_start` (the date a value was actually published), not the
observation period. A value is only visible to a model on or after the day it was
really released — matching checklist_en.html stage s2: "Use release date for macro
indicators (avoid look-ahead bias)".

Execution environment: pure pandas, no network calls — process_*.py scripts CAN run
inside the Cowork sandbox, as long as the matching raw CSVs already exist in
data/raw/macro/ (copy them in after running the matching fetch_*.py on a machine with
network access).
"""

from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RAW_DIR = PROJECT_ROOT / "data" / "raw" / "macro"
DEFAULT_INTERIM_DIR = PROJECT_ROOT / "data" / "interim"


def load_raw_csv(block: str, name: str, raw_dir: Path = DEFAULT_RAW_DIR) -> pd.DataFrame:
    path = Path(raw_dir) / f"{block}_{name}.csv"
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found — run src/data/fetch_{name}.py on a machine with network "
            "access first, then copy the CSV into data/raw/macro/."
        )
    return pd.read_csv(path, parse_dates=["date", "realtime_start"])


def business_calendar(start, end=None) -> pd.DatetimeIndex:
    end = pd.to_datetime(end) if end else pd.Timestamp.today()
    return pd.bdate_range(pd.to_datetime(start), end)


def build_known_as_of(releases: pd.DataFrame, calendar: pd.DatetimeIndex) -> pd.DataFrame:
    """For each calendar day, attach the latest value whose realtime_start (release
    date) is on or before that day, plus how many days ago it was released."""
    rel = (
        releases.dropna(subset=["realtime_start", "value"])
        .sort_values("realtime_start")
        .drop_duplicates(subset="realtime_start", keep="last")
    )
    cal_df = pd.DataFrame({"asof_date": pd.DatetimeIndex(calendar)}).sort_values("asof_date")
    merged = pd.merge_asof(
        cal_df,
        rel[["realtime_start", "value"]],
        left_on="asof_date",
        right_on="realtime_start",
        direction="backward",
    )
    merged["days_since_update"] = (merged["asof_date"] - merged["realtime_start"]).dt.days
    return merged.set_index("asof_date")[["value", "days_since_update"]]


def save_panel(panel: pd.DataFrame, out_path: Path) -> None:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    panel.to_csv(out_path)
    print(f"Saved panel: {panel.shape[0]} rows x {panel.shape[1]} cols -> {out_path}")
