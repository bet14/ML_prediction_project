"""
plot_model_comparison.py -- Generate model comparison charts from model_comparison.csv.

Outputs (saved to reports/figures/):
  1. cv_vs_final_accuracy.png   -- CV accuracy vs Final 2024 accuracy per model
  2. auc_by_model.png           -- Mean AUC-ROC across folds 1-5, per model
  3. accuracy_per_fold.png      -- Accuracy trend across folds (shows consistency over time)
  4. sharpe_by_model.png        -- Mean Sharpe proxy per model (financial usefulness)

Usage:
    python scripts/plot_model_comparison.py
    python scripts/plot_model_comparison.py --open   # open figures after saving
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

# Folds used for CV summary (exclude final — that is the held-out test)
CV_FOLDS = ["1", "2", "3", "4", "5"]

# Display order: best CV accuracy first, then rest
MODEL_ORDER = ["Bagging_LR", "LR", "HGB", "CatBoost", "Bagging_DT", "RF", "ET", "KNN", "DT"]

# Colors
C_CV    = "#4C72B0"   # blue  -- CV bars
C_FINAL = "#DD8452"   # orange -- Final 2024 bars
C_PAPER = "#C44E52"   # red    -- paper baseline line
C_FLAG  = "#E8C545"   # yellow -- flag color for LR / Bagging_LR
FLAGGED = {"LR", "Bagging_LR"}

PAPER_BASELINE = 0.545   # mid-point of 53-56% reported by Guyard & Deriaz (2024)
AUC_LITERATURE = 0.62    # typical upper bound in FX direction prediction literature


def load() -> pd.DataFrame:
    if not CSV_PATH.exists():
        sys.exit(f"File not found: {CSV_PATH}\nRun train.py first.")
    return pd.read_csv(CSV_PATH)


def reorder(df_indexed: pd.DataFrame) -> pd.DataFrame:
    """Reorder rows to MODEL_ORDER, keeping any model not listed at the end."""
    present  = [m for m in MODEL_ORDER if m in df_indexed.index]
    leftover = [m for m in df_indexed.index if m not in MODEL_ORDER]
    return df_indexed.loc[present + leftover]


# ---------------------------------------------------------------------------
# Chart 1 -- CV Accuracy vs Final 2024
# ---------------------------------------------------------------------------

def plot_cv_vs_final(df: pd.DataFrame, out_dir: Path) -> Path:
    cv    = df[df["fold"].isin(CV_FOLDS)].groupby("model")["accuracy"].mean()
    final = df[df["fold"] == "final"].groupby("model")["accuracy"].first()

    summary = pd.DataFrame({"cv": cv, "final": final}).dropna()
    summary = reorder(summary)

    models = summary.index.tolist()
    x      = np.arange(len(models))
    w      = 0.35

    fig, ax = plt.subplots(figsize=(12, 6))

    bars_cv    = ax.bar(x - w/2, summary["cv"],    w, label="CV mean (folds 1–5)", color=C_CV,    alpha=0.85)
    bars_final = ax.bar(x + w/2, summary["final"], w, label="Final test (2024)",   color=C_FINAL, alpha=0.85)

    # Yellow outline for flagged models
    for i, m in enumerate(models):
        if m in FLAGGED:
            for bars in (bars_cv, bars_final):
                bars[i].set_edgecolor(C_FLAG)
                bars[i].set_linewidth(2.5)

    # Paper baseline
    ax.axhline(PAPER_BASELINE, color=C_PAPER, lw=1.5, ls="--", label=f"Paper baseline ~{PAPER_BASELINE:.0%}")
    ax.axhline(0.50,           color="grey",  lw=1.0, ls=":",  label="Random (50%)")

    # Value labels
    for bar in list(bars_cv) + list(bars_final):
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2, h + 0.005,
                f"{h:.1%}", ha="center", va="bottom", fontsize=7.5)

    ax.set_xticks(x)
    ax.set_xticklabels(models, rotation=20, ha="right", fontsize=9)
    ax.yaxis.set_major_formatter(mtick.PercentFormatter(1.0))
    ax.set_ylim(0.40, 0.86)
    ax.set_ylabel("Accuracy")
    ax.set_title("CV Accuracy (folds 1–5) vs Final Test Accuracy (2024)\n"
                 "Yellow outline = anomalously high — flagged for investigation", fontsize=11)
    ax.legend(fontsize=9)
    ax.grid(axis="y", alpha=0.3)

    path = out_dir / "cv_vs_final_accuracy.png"
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"  Saved: {path}")
    return path


# ---------------------------------------------------------------------------
# Chart 2 -- Mean AUC-ROC per model
# ---------------------------------------------------------------------------

def plot_auc(df: pd.DataFrame, out_dir: Path) -> Path:
    cv_auc = (
        df[df["fold"].isin(CV_FOLDS)]
        .groupby("model")["auc_roc"]
        .mean()
        .dropna()
    )
    cv_auc = reorder(cv_auc.to_frame()).squeeze()

    fig, ax = plt.subplots(figsize=(11, 5))

    colors = [C_FLAG if m in FLAGGED else C_CV for m in cv_auc.index]
    bars   = ax.bar(cv_auc.index, cv_auc.values, color=colors, alpha=0.85, edgecolor="white")

    # Reference lines
    ax.axhline(0.50,             color="grey",  lw=1.0, ls=":",  label="Random (0.50)")
    ax.axhline(AUC_LITERATURE,   color=C_PAPER, lw=1.5, ls="--",
               label=f"Literature upper bound ~{AUC_LITERATURE:.2f}")
    ax.axhline(0.80,             color="#A8C4E0", lw=1.2, ls="-.",
               label="0.80 — suspicious for FX data")

    for bar, val in zip(bars, cv_auc.values):
        ax.text(bar.get_x() + bar.get_width() / 2, val + 0.005,
                f"{val:.3f}", ha="center", va="bottom", fontsize=8)

    ax.set_ylim(0.45, 0.95)
    ax.set_ylabel("AUC-ROC")
    ax.set_title("Mean AUC-ROC across CV Folds 1–5\n"
                 "Yellow = flagged (0.85 far exceeds literature ~0.55–0.65)", fontsize=11)
    ax.tick_params(axis="x", rotation=20)
    ax.legend(fontsize=9)
    ax.grid(axis="y", alpha=0.3)

    path = out_dir / "auc_by_model.png"
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"  Saved: {path}")
    return path


# ---------------------------------------------------------------------------
# Chart 3 -- Accuracy per fold (consistency over time)
# ---------------------------------------------------------------------------

def plot_per_fold(df: pd.DataFrame, out_dir: Path) -> Path:
    pivot = (
        df[df["fold"].isin(CV_FOLDS)]
        .pivot_table(index="fold", columns="model", values="accuracy")
    )
    # Reorder columns to MODEL_ORDER
    cols = [m for m in MODEL_ORDER if m in pivot.columns]
    pivot = pivot[cols]

    fold_years = {"1": "2019", "2": "2020", "3": "2021", "4": "2022", "5": "2023"}
    pivot.index = [fold_years.get(f, f) for f in pivot.index]

    fig, ax = plt.subplots(figsize=(12, 6))

    for model in pivot.columns:
        lw    = 2.5 if model in FLAGGED else 1.4
        ls    = "-"  if model not in FLAGGED else "--"
        color = C_FLAG if model in FLAGGED else None
        ax.plot(pivot.index, pivot[model], marker="o", lw=lw, ls=ls,
                color=color, label=model, markersize=5)

    ax.axhline(PAPER_BASELINE, color=C_PAPER, lw=1.2, ls=":", label="Paper baseline")
    ax.axhline(0.50,           color="grey",  lw=0.9, ls=":", alpha=0.6)

    ax.set_ylabel("Accuracy")
    ax.set_xlabel("Test year (fold)")
    ax.set_title("Accuracy per CV Fold by Model\n"
                 "Dashed yellow = flagged models · Dotted red = paper baseline", fontsize=11)
    ax.legend(fontsize=8, bbox_to_anchor=(1.01, 1), loc="upper left")
    ax.yaxis.set_major_formatter(mtick.PercentFormatter(1.0))
    ax.set_ylim(0.40, 0.85)
    ax.grid(alpha=0.3)

    path = out_dir / "accuracy_per_fold.png"
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"  Saved: {path}")
    return path


# ---------------------------------------------------------------------------
# Chart 4 -- Sharpe proxy (financial usefulness)
# ---------------------------------------------------------------------------

def plot_sharpe(df: pd.DataFrame, out_dir: Path) -> Path:
    cv_sharpe = (
        df[df["fold"].isin(CV_FOLDS)]
        .groupby("model")["sharpe_proxy"]
        .mean()
        .dropna()
    )
    cv_sharpe = reorder(cv_sharpe.to_frame()).squeeze()

    fig, ax = plt.subplots(figsize=(11, 5))

    colors = ["#5DA271" if v >= 0 else "#C44E52" for v in cv_sharpe.values]
    bars   = ax.bar(cv_sharpe.index, cv_sharpe.values, color=colors, alpha=0.85, edgecolor="white")

    ax.axhline(0, color="black", lw=1.0)
    ax.axhline(0.5,  color="#5DA271", lw=1.2, ls="--", alpha=0.6, label="Sharpe 0.5 (decent strategy)")
    ax.axhline(-0.5, color="#C44E52", lw=1.2, ls="--", alpha=0.6, label="Sharpe −0.5")

    for bar, val in zip(bars, cv_sharpe.values):
        offset = 0.03 if val >= 0 else -0.06
        ax.text(bar.get_x() + bar.get_width() / 2, val + offset,
                f"{val:.2f}", ha="center", va="bottom", fontsize=8)

    ax.set_ylabel("Sharpe Proxy (annualised)")
    ax.set_title("Mean Sharpe Proxy across CV Folds 1–5\n"
                 "Green = strategy would have made money on average · Red = lost money", fontsize=11)
    ax.tick_params(axis="x", rotation=20)
    ax.legend(fontsize=9)
    ax.grid(axis="y", alpha=0.3)

    path = out_dir / "sharpe_by_model.png"
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"  Saved: {path}")
    return path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--open", action="store_true", help="Open figures after saving")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading model_comparison.csv ...")
    df = load()
    print(f"  {len(df)} rows · {df['model'].nunique()} models · folds: {sorted(df['fold'].unique())}\n")

    print("Generating charts ...")
    paths = [
        plot_cv_vs_final(df, OUT_DIR),
        plot_auc(df, OUT_DIR),
        plot_per_fold(df, OUT_DIR),
        plot_sharpe(df, OUT_DIR),
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
