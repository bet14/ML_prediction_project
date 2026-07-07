"""
backtest.py -- Walk-forward backtest: stitch OOS fold predictions into one
continuous 2019-2024 equity curve and compare a model-driven long/flat
strategy against buy-and-hold GBP/USD.

STATUS: production

Loads the .joblib pipelines already saved by train.py (one per fold) and
re-predicts on each fold's own test set -- no retraining here. Folds 1-5
(test years 2019-2023) plus "final" (test year 2024) are non-overlapping
and calendar-contiguous, so concatenating them by date gives one continuous
out-of-sample equity curve instead of six disconnected per-fold snippets.

Strategy: long GBP/USD (position=1) when the model predicts Direction=1,
flat (position=0) otherwise. A spread cost (in pips) can be charged on
every position change to test sensitivity to trading costs (spec item:
1-2 pip GBP/USD spread applied to cumulative P(t)).

Usage:
    python src/evaluation/backtest.py                                  # default: XGB + HGB on Dataset 1
    python src/evaluation/backtest.py --dataset dataset_technical --models XGB CatBoost
    python src/evaluation/backtest.py --models XGB --spread-pips 1.5   # sensitivity test
    python src/evaluation/backtest.py --models XGB --open
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.evaluation.metrics import compute_metrics, _annualised_sharpe, _max_drawdown
from src.evaluation.walk_forward_cv import get_folds

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
TRAINED_DIR = PROJECT_ROOT / "models" / "trained"
TABLES_DIR = PROJECT_ROOT / "reports" / "tables"
FIGURES_DIR = PROJECT_ROOT / "reports" / "figures"
SUMMARY_PATH = TABLES_DIR / "backtest_summary.csv"
SUMMARY_KEY_COLS = ["dataset", "model", "spread_pips"]

DATASET_FILES = {
    "dataset_basic_daily": "dataset_basic_daily.csv",
    "dataset_90day_lookback": "dataset_90day_lookback.csv",
    "dataset_technical": "dataset_technical.csv",
}

GBPUSD_CLOSE_COL = "GBP_USD_close"
FOLD_LABELS = ["1", "2", "3", "4", "5", "final"]  # test years 2019-2024, matches train.py naming
PIP_SIZE = 0.0001  # GBP/USD pip

C_STRATEGY = "#4C72B0"  # blue
C_BUYHOLD = "#DD8452"  # orange
C_DRAWDOWN = "#C44E52"  # red


def stitch_oos_predictions(dataset_name: str, model_name: str) -> pd.DataFrame:
    """
    Load each fold's saved pipeline, predict on that fold's own test set, and
    concatenate folds 1-5 + final into one continuous 2019-2024 daily frame.

    Returns a DataFrame indexed by date with columns: close, y_true, y_pred, y_proba.
    """
    csv_path = PROCESSED_DIR / DATASET_FILES[dataset_name]
    if not csv_path.exists():
        raise FileNotFoundError(f"Dataset not found: {csv_path}")

    df = pd.read_csv(csv_path, index_col=0, parse_dates=True)
    folds = get_folds(df)

    chunks = []
    for i, fold_label in enumerate(FOLD_LABELS):
        if i >= len(folds):
            break
        _, _, X_test, y_test = folds[i]

        model_path = TRAINED_DIR / f"{model_name}_{dataset_name}_fold{fold_label}.joblib"
        if not model_path.exists():
            print(f"  [WARN] missing {model_path.name} -- skipping fold {fold_label}")
            continue

        pipe = joblib.load(model_path)
        y_pred = pipe.predict(X_test)
        try:
            y_proba = pipe.predict_proba(X_test)[:, 1]
        except AttributeError:
            y_proba = np.full(len(X_test), np.nan)

        chunks.append(pd.DataFrame({
            "close": X_test[GBPUSD_CLOSE_COL].values.astype(float),
            "y_true": y_test.values,
            "y_pred": y_pred,
            "y_proba": y_proba,
        }, index=X_test.index))

    if not chunks:
        raise RuntimeError(f"No trained folds found for {model_name} on {dataset_name}")

    stitched = pd.concat(chunks).sort_index()
    # Computed on the stitched close series itself (not per-fold), so the
    # daily move across a fold boundary (e.g. last day of 2019 -> first day
    # of 2020) is captured instead of being zeroed out at every fold start.
    stitched["log_return"] = np.log(stitched["close"] / stitched["close"].shift(1)).fillna(0.0)
    return stitched


def simulate_strategy(stitched: pd.DataFrame, spread_pips: float = 0.0) -> pd.DataFrame:
    """
    Add position, gross/net strategy return, and equity-curve columns.

    Cost model: charge spread_pips (converted to a log-return-scale cost via
    pip_size / close) on every day the position changes (entry or exit).
    """
    out = stitched.copy()
    out["position"] = out["y_pred"].astype(int)

    position_change = out["position"].diff().fillna(out["position"].iloc[0]).abs()
    cost_per_switch = spread_pips * PIP_SIZE / out["close"]
    out["cost"] = position_change * cost_per_switch

    out["strategy_return_gross"] = out["position"] * out["log_return"]
    out["strategy_return_net"] = out["strategy_return_gross"] - out["cost"]

    out["equity_strategy"] = np.exp(out["strategy_return_net"].cumsum())
    out["equity_buyhold"] = np.exp(out["log_return"].cumsum())
    return out


def summarize(out: pd.DataFrame) -> dict:
    """Classification + trading metrics for the whole stitched 2019-2024 window."""
    has_proba = out["y_proba"].notna().all()
    clf_metrics = compute_metrics(
        out["y_true"], out["y_pred"],
        y_proba=out["y_proba"].values if has_proba else None,
    )
    n_trades = int(out["position"].diff().fillna(out["position"].iloc[0]).abs().sum())

    return {
        "accuracy": clf_metrics["accuracy"],
        "f1_macro": clf_metrics["f1_macro"],
        "auc_roc": clf_metrics["auc_roc"],
        "sharpe_gross": _annualised_sharpe(out["strategy_return_gross"].values),
        "sharpe_net": _annualised_sharpe(out["strategy_return_net"].values),
        "max_drawdown_net": _max_drawdown(out["strategy_return_net"].values),
        "total_return_strategy": float(out["equity_strategy"].iloc[-1] - 1.0),
        "total_return_buyhold": float(out["equity_buyhold"].iloc[-1] - 1.0),
        "n_trades": n_trades,
        "n_days": len(out),
    }


def _upsert_summary(record: dict) -> None:
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    row = pd.DataFrame([record])
    if SUMMARY_PATH.exists():
        existing = pd.read_csv(SUMMARY_PATH)
        key = tuple(record[c] for c in SUMMARY_KEY_COLS)
        existing = existing[~existing[SUMMARY_KEY_COLS].apply(lambda r: tuple(r) == key, axis=1)]
        row = pd.concat([existing, row], ignore_index=True)
    row.to_csv(SUMMARY_PATH, index=False)


def run_backtest(dataset_name: str, model_name: str, spread_pips: float = 0.0):
    """Stitch OOS predictions, simulate the strategy, save per-day CSV + summary row."""
    stitched = stitch_oos_predictions(dataset_name, model_name)
    out = simulate_strategy(stitched, spread_pips=spread_pips)
    metrics = summarize(out)

    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    out.to_csv(TABLES_DIR / f"backtest_{model_name}_{dataset_name}.csv")
    _upsert_summary({
        "dataset": dataset_name,
        "model": model_name,
        "spread_pips": spread_pips,
        **metrics,
    })

    return out, metrics


def plot_equity_curve(
    out: pd.DataFrame, model_name: str, dataset_name: str, spread_pips: float, out_dir: Path
) -> Path:
    fig, (ax_eq, ax_dd) = plt.subplots(
        2, 1, figsize=(12, 7), sharex=True, gridspec_kw={"height_ratios": [3, 1]},
    )

    ax_eq.plot(out.index, out["equity_strategy"], color=C_STRATEGY, lw=1.8,
               label=f"{model_name} strategy (net of {spread_pips:.1f} pip spread)")
    ax_eq.plot(out.index, out["equity_buyhold"], color=C_BUYHOLD, lw=1.4, ls="--",
               label="Buy & hold GBP/USD")
    ax_eq.axhline(1.0, color="grey", lw=0.8, ls=":")
    ax_eq.set_ylabel("Equity (start = 1.0)")
    ax_eq.set_title(
        f"Walk-forward Backtest -- {model_name} on {dataset_name}\n"
        f"Stitched OOS 2019-2024 (test folds only, no retraining)",
        fontsize=11,
    )
    ax_eq.legend(fontsize=9)
    ax_eq.grid(alpha=0.3)

    cum = out["strategy_return_net"].cumsum()
    drawdown = cum - cum.cummax()
    ax_dd.fill_between(out.index, drawdown, 0, color=C_DRAWDOWN, alpha=0.4)
    ax_dd.set_ylabel("Drawdown\n(log-return)")
    ax_dd.set_xlabel("Date")
    ax_dd.grid(alpha=0.3)

    fig.tight_layout()
    path = out_dir / f"equity_curve_{model_name}_{dataset_name}.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"  Saved: {path}")
    return path


def _fmt(value, spec=".3f"):
    return format(value, spec) if value is not None else "N/A"


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--dataset", default="dataset_basic_daily", choices=list(DATASET_FILES.keys()))
    parser.add_argument("--models", nargs="+", default=["XGB", "HGB"],
                         help="Model name(s) matching model_registry.py REGISTRY keys")
    parser.add_argument("--spread-pips", type=float, default=0.0,
                         help="Spread cost in pips charged on every position change "
                              "(sensitivity test: try 0, 1, 2)")
    parser.add_argument("--open", action="store_true", help="Open equity curve PNGs after saving")
    args = parser.parse_args()

    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Dataset      : {args.dataset}")
    print(f"Models       : {args.models}")
    print(f"Spread (pips): {args.spread_pips}\n")

    paths = []
    for model_name in args.models:
        print(f"[{model_name}] stitching walk-forward OOS predictions ...")
        try:
            out, metrics = run_backtest(args.dataset, model_name, spread_pips=args.spread_pips)
        except (FileNotFoundError, RuntimeError) as exc:
            print(f"  [SKIP] {exc}")
            continue

        print(
            f"  days={metrics['n_days']}  trades={metrics['n_trades']}  "
            f"acc={metrics['accuracy']:.3f}  "
            f"sharpe_gross={_fmt(metrics['sharpe_gross'])}  "
            f"sharpe_net={_fmt(metrics['sharpe_net'])}  "
            f"total_return: strategy={metrics['total_return_strategy']:+.1%} "
            f"vs buy&hold={metrics['total_return_buyhold']:+.1%}"
        )
        paths.append(plot_equity_curve(out, model_name, args.dataset, args.spread_pips, FIGURES_DIR))

    print(f"\nPer-day results -> reports/tables/backtest_<model>_<dataset>.csv")
    print(f"Summary metrics -> {SUMMARY_PATH}")

    if args.open:
        for p in paths:
            if sys.platform == "win32":
                os.startfile(p)
            else:
                subprocess.run(["open" if sys.platform == "darwin" else "xdg-open", str(p)])


if __name__ == "__main__":
    main()
