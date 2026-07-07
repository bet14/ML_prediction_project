"""
Build data/processed/dataset_technical.csv -- Dataset 3 (Technical Indicators).

Merges Dataset 1 (Basic Daily) with technical indicators computed independently
for all 17 instruments (13 forex pairs + 4 equity indices) via
src/features/technical_indicators.py.

Steps
-----
 1  Load data/processed/dataset_basic_daily.csv (defines the target date index).
 2  Load data/interim/forex_panel.csv (13 pairs, OHLC) and
    data/interim/equity_panel.csv (9 indices, OHLCV), then drop the 5
    redundant equity indices (multicollinearity evidence: notebook 03 --
    same REDUNDANT_INDICES list applied in build_dataset.py for Dataset 1),
    leaving 4 equity indices.
 3  For each of the 17 instruments, compute its ~60/72 technical-indicator
    columns (see technical_indicators.py) and prefix column names with the
    instrument name.
 4  Concatenate all instrument indicator blocks + Dataset 1, reindexed to
    Dataset 1's date index.
 5  Drop the first 90 rows (indicators need up to 90 days of lookback to be
    valid -- decision Q2 in References/DATASET_2_3_PLAN.md).
 6  Save to data/processed/dataset_technical.csv.

Expected shape: ~2,778 rows x ~1,178 cols
    (4 equity x 72 + 13 forex x 60 = 1,068 technical cols + 110 Dataset 1 cols)

Usage
-----
    python src/features/build_dataset_technical.py
"""

import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INTERIM_DIR = PROJECT_ROOT / "data" / "interim"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

sys.path.insert(0, str(PROJECT_ROOT))
from src.features.build_dataset import REDUNDANT_INDICES  # noqa: E402
from src.features.technical_indicators import compute_technical_indicators  # noqa: E402

BASIC_DAILY_PATH = PROCESSED_DIR / "dataset_basic_daily.csv"
FOREX_PANEL_PATH = INTERIM_DIR / "forex_panel.csv"
EQUITY_PANEL_PATH = INTERIM_DIR / "equity_panel.csv"
OUT_PATH = PROCESSED_DIR / "dataset_technical.csv"

DROP_FIRST_N_ROWS = 90  # Q2 decision: rows without full 90-day indicator lookback


def instruments_from_panel(panel: pd.DataFrame, suffix: str) -> list[str]:
    """Extract instrument prefixes from a panel's '{prefix}_{suffix}' columns."""
    return sorted({c[: -len(f"_{suffix}")] for c in panel.columns if c.endswith(f"_{suffix}")})


def extract_ohlc(panel: pd.DataFrame, instrument: str, has_volume: bool) -> pd.DataFrame:
    cols = {
        "open": f"{instrument}_open",
        "high": f"{instrument}_high",
        "low": f"{instrument}_low",
        "close": f"{instrument}_close",
    }
    if has_volume:
        cols["volume"] = f"{instrument}_volume"
    df = panel[list(cols.values())].copy()
    df.columns = list(cols.keys())
    return df


def build_instrument_block(panel: pd.DataFrame, instrument: str, has_volume: bool) -> pd.DataFrame:
    ohlc = extract_ohlc(panel, instrument, has_volume)
    indicators = compute_technical_indicators(ohlc, has_volume=has_volume)
    indicators.columns = [f"{instrument}_{c}" for c in indicators.columns]
    return indicators


def main() -> None:
    print("=" * 60)
    print("build_dataset_technical.py -- Dataset 3: Technical Indicators")
    print("=" * 60)

    print("\n[Step 1] Loading Dataset 1 (Basic Daily)...")
    if not BASIC_DAILY_PATH.exists():
        print(f"  [ERROR] Missing {BASIC_DAILY_PATH} -- run build_dataset.py first", file=sys.stderr)
        sys.exit(1)
    basic = pd.read_csv(BASIC_DAILY_PATH, index_col=0, parse_dates=True)
    print(f"  Loaded: {basic.shape[0]} rows x {basic.shape[1]} cols "
          f"({basic.index[0].date()} to {basic.index[-1].date()})")

    print("\n[Step 2] Loading interim forex/equity panels...")
    forex_panel = pd.read_csv(FOREX_PANEL_PATH, index_col="date", parse_dates=True)
    equity_panel = pd.read_csv(EQUITY_PANEL_PATH, index_col="date", parse_dates=True)
    forex_pairs = instruments_from_panel(forex_panel, "close")
    equity_indices_all = instruments_from_panel(equity_panel, "close")
    equity_indices = [idx for idx in equity_indices_all if idx not in REDUNDANT_INDICES]
    print(f"  Forex panel : {forex_panel.shape[0]} rows, {len(forex_pairs)} pairs")
    print(f"  Equity panel: {equity_panel.shape[0]} rows, {len(equity_indices_all)} indices "
          f"-> {len(equity_indices)} after dropping {len(REDUNDANT_INDICES)} redundant "
          f"(multicollinear) indices: {', '.join(sorted(set(equity_indices_all) - set(equity_indices)))}")

    print(f"\n[Step 3] Computing technical indicators for {len(forex_pairs)} forex pairs "
          "(no volume, 60 cols each)...")
    blocks = []
    for pair in forex_pairs:
        blocks.append(build_instrument_block(forex_panel, pair, has_volume=False))
        print(f"  [OK] {pair}")

    print(f"\n[Step 4] Computing technical indicators for {len(equity_indices)} equity indices "
          "(with volume, 72 cols each)...")
    for idx in equity_indices:
        blocks.append(build_instrument_block(equity_panel, idx, has_volume=True))
        print(f"  [OK] {idx}")

    print("\n[Step 5] Merging all indicator blocks with Dataset 1...")
    tech_df = pd.concat(blocks, axis=1)
    tech_df = tech_df.reindex(basic.index)
    combined = pd.concat([tech_df, basic], axis=1)
    print(f"  Technical cols: {tech_df.shape[1]}  |  Dataset 1 cols: {basic.shape[1]}  "
          f"|  Combined: {combined.shape[1]} cols")

    print(f"\n[Step 6] Dropping first {DROP_FIRST_N_ROWS} rows (indicator lookback warm-up)...")
    combined = combined.iloc[DROP_FIRST_N_ROWS:]
    print(f"  Rows remaining: {combined.shape[0]} "
          f"({combined.index[0].date()} to {combined.index[-1].date()})")

    print("\n[Step 7] Saving Dataset 3...")
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    combined.to_csv(OUT_PATH)

    nan_pct = combined.isna().mean().mean() * 100
    print(f"\n{'=' * 60}")
    print("DONE")
    print(f"  Output : {OUT_PATH}")
    print(f"  Shape  : {combined.shape[0]} rows x {combined.shape[1]} cols")
    print(f"  NaN    : {nan_pct:.2f}% overall")
    print("=" * 60)


if __name__ == "__main__":
    main()
