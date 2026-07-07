"""
plot_bias_variance.py -- Bias-variance tradeoff scatter for all 12 trained models (Dataset 1).

Proxies (no repeated-resampling bias-variance decomposition available, so we use
the same walk-forward CV numbers already narrated on Slide 8):
  Bias proxy     (x-axis) = 1 - mean CV accuracy (folds 1-5)      -- higher = more underfit
  Variance proxy (y-axis) = max(0, mean CV accuracy - Final 2024) -- how much CV accuracy
                             overestimates the true held-out result (0 if Final >= CV mean,
                             since that is not an overfitting signal)

Output: reports/figures/bias_variance_tradeoff.png

Usage:
    python scripts/plot_bias_variance.py
    python scripts/plot_bias_variance.py --open
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CSV_PATH     = PROJECT_ROOT / "reports" / "tables" / "model_comparison.csv"
OUT_DIR      = PROJECT_ROOT / "reports" / "figures"
DATASET      = "dataset_basic_daily"
CV_FOLDS     = ["1", "2", "3", "4", "5"]

FLAGGED = {"LR", "Bagging_LR"}   # high-variance / overfit flag, matches Slide 8
UNDERFIT = {"DT"}                 # high-bias flag, matches Slide 8

FAMILY = {
    "LR": "Linear", "Bagging_LR": "Linear",
    "DT": "Tree", "RF": "Tree", "ET": "Tree", "Bagging_DT": "Tree",
    "XGB": "Boosting", "LGBM": "Boosting", "HGB": "Boosting", "CatBoost": "Boosting",
    "KNN": "Other", "MLP": "Other",
}
FAMILY_COLOR = {
    "Linear": "#C44E52", "Tree": "#55A868", "Boosting": "#4C72B0", "Other": "#8172B2",
}


def load() -> pd.DataFrame:
    if not CSV_PATH.exists():
        sys.exit(f"File not found: {CSV_PATH}\nRun train.py first.")
    return pd.read_csv(CSV_PATH)


def build_summary(df: pd.DataFrame) -> pd.DataFrame:
    d1 = df[df["dataset"] == DATASET]
    cv = d1[d1["fold"].isin(CV_FOLDS)].groupby("model")["accuracy"].mean()
    final = d1[d1["fold"] == "final"].groupby("model")["accuracy"].first()

    summary = pd.DataFrame({"cv_mean": cv, "final": final}).dropna()
    summary["bias"] = 1 - summary["cv_mean"]
    summary["variance"] = (summary["cv_mean"] - summary["final"]).clip(lower=0)
    return summary


def plot(summary: pd.DataFrame, out_dir: Path) -> Path:
    fig, ax = plt.subplots(figsize=(9, 7))

    for model, row in summary.iterrows():
        family = FAMILY.get(model, "Other")
        color = FAMILY_COLOR[family]
        edge, lw, size = "white", 1.0, 160
        if model in FLAGGED:
            edge, lw = "#E8C545", 2.5
        elif model in UNDERFIT:
            edge, lw = "#333333", 2.5

        ax.scatter(row["bias"], row["variance"], s=size, color=color,
                   edgecolor=edge, linewidth=lw, zorder=3)
        ax.annotate(model, (row["bias"], row["variance"]),
                   textcoords="offset points", xytext=(7, 5), fontsize=9)

    # Quadrant guide lines at the median of each axis
    ax.axvline(summary["bias"].median(), color="grey", lw=0.8, ls=":", alpha=0.6)
    ax.axhline(summary["variance"].median(), color="grey", lw=0.8, ls=":", alpha=0.6)

    ax.set_xlabel("Bias proxy  ->  1 - mean CV accuracy (folds 1-5)\n(higher = more underfit)")
    ax.set_ylabel("Variance proxy  ->  max(0, CV mean - Final 2024)\n(higher = CV accuracy overestimates true generalization)")
    ax.set_title("Bias-Variance Tradeoff Across 12 Models (Dataset 1)\n"
                 "Yellow outline = flagged overfit (LR, Bagging_LR) - Black outline = flagged underfit (DT)",
                 fontsize=11)

    # Legend for model families
    handles = [plt.Line2D([0], [0], marker="o", color="w", markerfacecolor=c, markersize=10, label=fam)
              for fam, c in FAMILY_COLOR.items()]
    ax.legend(handles=handles, title="Model family", fontsize=9, loc="upper right")

    ax.grid(alpha=0.25)
    fig.tight_layout()

    path = out_dir / "bias_variance_tradeoff.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"  Saved: {path}")
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--open", action="store_true", help="Open figure after saving")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading model_comparison.csv ...")
    df = load()
    summary = build_summary(df)
    print(f"  {len(summary)} models on {DATASET}\n")
    print(summary.sort_values("variance", ascending=False))

    print("\nGenerating chart ...")
    path = plot(summary, OUT_DIR)

    if args.open:
        if sys.platform == "win32":
            os.startfile(path)
        else:
            subprocess.run(["open" if sys.platform == "darwin" else "xdg-open", str(path)])


if __name__ == "__main__":
    main()
