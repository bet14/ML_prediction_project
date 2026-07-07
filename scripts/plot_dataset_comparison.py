"""
plot_dataset_comparison.py -- Compare Dataset 1 (Basic Daily) vs Dataset 2 (90-Day
Lookback) vs Dataset 3 (Technical Indicators) across all 12 models in the registry.

Outputs (saved to reports/figures/):
  1. dataset_comparison_accuracy.png   -- CV mean accuracy per model, grouped by dataset
  2. dataset_comparison_auc.png        -- CV mean AUC-ROC per model, grouped by dataset
  3. dataset_comparison_sharpe.png     -- CV mean Sharpe proxy per model, grouped by dataset
  4. dataset_comparison_overfit_gap.png -- CV accuracy minus Final accuracy per model x dataset
                                           (positive = CV outperforms 2024 held-out, i.e. overfit)

Usage:
    python scripts/plot_dataset_comparison.py
    python scripts/plot_dataset_comparison.py --open   # open figures after saving
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CSV_PATH     = PROJECT_ROOT / "reports" / "tables" / "model_comparison.csv"
OUT_DIR      = PROJECT_ROOT / "reports" / "figures"

CV_FOLDS = ["1", "2", "3", "4", "5"]

DATASET_ORDER = ["dataset_basic_daily", "dataset_90day_lookback", "dataset_technical"]
DATASET_LABELS = {
    "dataset_basic_daily":    "Dataset 1 (Basic Daily)",
    "dataset_90day_lookback": "Dataset 2 (90-Day Lookback)",
    "dataset_technical":      "Dataset 3 (Technical Indicators)",
}
DATASET_COLORS = {
    "dataset_basic_daily":    "#4C72B0",   # blue
    "dataset_90day_lookback": "#C44E52",   # red -- flagged as weak signal
    "dataset_technical":      "#5DA271",   # green
}

MODEL_ORDER = ["LR", "Bagging_LR", "HGB", "CatBoost", "LGBM", "XGB",
               "Bagging_DT", "RF", "ET", "MLP", "KNN", "DT"]


def load() -> pd.DataFrame:
    if not CSV_PATH.exists():
        sys.exit(f"File not found: {CSV_PATH}\nRun train.py first.")
    return pd.read_csv(CSV_PATH)


def _cv_final_pivot(df: pd.DataFrame, metric: str) -> tuple:
    cv = (
        df[df["fold"].isin(CV_FOLDS)]
        .groupby(["dataset", "model"])[metric]
        .mean()
        .unstack("dataset")
    )
    final = (
        df[df["fold"] == "final"]
        .groupby(["dataset", "model"])[metric]
        .first()
        .unstack("dataset")
    )
    models_present = [m for m in MODEL_ORDER if m in cv.index]
    cv = cv.reindex(models_present)
    final = final.reindex(models_present)
    return cv, final


def _grouped_bar(cv: pd.DataFrame, title: str, ylabel: str, out_path: Path,
                  ylim=None, ref_lines=None, pct=False) -> Path:
    models = cv.index.tolist()
    datasets = [d for d in DATASET_ORDER if d in cv.columns]
    n = len(datasets)
    x = np.arange(len(models))
    w = 0.8 / n

    fig, ax = plt.subplots(figsize=(13, 6))

    for i, ds in enumerate(datasets):
        offset = (i - (n - 1) / 2) * w
        vals = cv[ds].values
        ax.bar(x + offset, vals, w, label=DATASET_LABELS[ds],
               color=DATASET_COLORS[ds], alpha=0.88)

    if ref_lines:
        for val, color, ls, label in ref_lines:
            ax.axhline(val, color=color, lw=1.2, ls=ls, label=label)

    ax.set_xticks(x)
    ax.set_xticklabels(models, rotation=20, ha="right", fontsize=9)
    if pct:
        ax.yaxis.set_major_formatter(mtick.PercentFormatter(1.0))
    if ylim:
        ax.set_ylim(*ylim)
    ax.set_ylabel(ylabel)
    ax.set_title(title, fontsize=11)
    ax.legend(fontsize=9, ncol=2)
    ax.grid(axis="y", alpha=0.3)

    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"  Saved: {out_path}")
    return out_path


def plot_accuracy(df: pd.DataFrame, out_dir: Path) -> Path:
    cv, _ = _cv_final_pivot(df, "accuracy")
    return _grouped_bar(
        cv,
        title="CV Mean Accuracy (folds 1-5) by Dataset, all 12 models\n"
              "Dataset 2 stays near-random across every model (p >> n)",
        ylabel="Accuracy", out_path=out_dir / "dataset_comparison_accuracy.png",
        ylim=(0.40, 0.90), pct=True,
        ref_lines=[(0.50, "grey", ":", "Random (50%)")],
    )


def plot_auc(df: pd.DataFrame, out_dir: Path) -> Path:
    cv, _ = _cv_final_pivot(df, "auc_roc")
    return _grouped_bar(
        cv,
        title="CV Mean AUC-ROC (folds 1-5) by Dataset, all 12 models\n"
              "Dataset 3 (technical indicators) leads for every tree/boosting model",
        ylabel="AUC-ROC", out_path=out_dir / "dataset_comparison_auc.png",
        ylim=(0.40, 1.00),
        ref_lines=[(0.50, "grey", ":", "Random (0.50)")],
    )


def plot_sharpe(df: pd.DataFrame, out_dir: Path) -> Path:
    cv, _ = _cv_final_pivot(df, "sharpe_proxy")
    return _grouped_bar(
        cv,
        title="CV Mean Sharpe Proxy (folds 1-5) by Dataset, all 12 models\n"
              "Financial usefulness -- accuracy and Sharpe do not always agree",
        ylabel="Sharpe Proxy (annualised)", out_path=out_dir / "dataset_comparison_sharpe.png",
        ref_lines=[(0.0, "black", "-", "Break-even")],
    )


def plot_overfit_gap(df: pd.DataFrame, out_dir: Path) -> Path:
    cv, final = _cv_final_pivot(df, "accuracy")
    gap = cv - final  # positive = CV accuracy higher than 2024 held-out -> overfit signal
    models = gap.index.tolist()
    datasets = [d for d in DATASET_ORDER if d in gap.columns]
    n = len(datasets)
    x = np.arange(len(models))
    w = 0.8 / n

    fig, ax = plt.subplots(figsize=(13, 6))
    for i, ds in enumerate(datasets):
        offset = (i - (n - 1) / 2) * w
        vals = gap[ds].values
        colors = [DATASET_COLORS[ds] if v >= 0 else "#E8C545" for v in vals]
        ax.bar(x + offset, vals, w, label=DATASET_LABELS[ds], color=colors, alpha=0.88)

    ax.axhline(0, color="black", lw=1.0)
    ax.set_xticks(x)
    ax.set_xticklabels(models, rotation=20, ha="right", fontsize=9)
    ax.set_ylabel("CV accuracy − Final (2024) accuracy")
    ax.set_title("Overfitting Gap by Dataset (CV mean − 2024 held-out)\n"
                 "Positive = model looked better in CV than on unseen 2024 data", fontsize=11)
    ax.legend(fontsize=9, ncol=1)
    ax.grid(axis="y", alpha=0.3)

    path = out_dir / "dataset_comparison_overfit_gap.png"
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"  Saved: {path}")
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--open", action="store_true", help="Open figures after saving")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading model_comparison.csv ...")
    df = load()
    print(f"  {len(df)} rows | datasets: {sorted(df['dataset'].unique())} | "
          f"{df['model'].nunique()} models\n")

    print("Generating dataset comparison charts ...")
    paths = [
        plot_accuracy(df, OUT_DIR),
        plot_auc(df, OUT_DIR),
        plot_sharpe(df, OUT_DIR),
        plot_overfit_gap(df, OUT_DIR),
    ]

    print(f"\nAll charts saved to {OUT_DIR}")

    if args.open:
        for p in paths:
            if sys.platform == "win32":
                os.startfile(p)
            else:
                subprocess.run(["open" if sys.platform == "darwin" else "xdg-open", str(p)])


if __name__ == "__main__":
    main()
