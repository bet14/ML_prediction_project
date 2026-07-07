"""
plot_variance_tradeoff.py -- Bias-variance trade-off, one scatter per dataset, built
from the real walk-forward CV fold numbers (not accuracy-vs-Sharpe). Draft support
material for Slide 8b ("Evaluation: accuracy and profit") in presentation_outline.md.

Each point = one of the 12 models on that dataset:
  x = fold-to-fold accuracy std-dev across inner CV folds 1-5 ("variance" -- how much
      the model's accuracy swings year to year during tuning)
  y = final (2024 held-out) accuracy ("bias" proxy -- low accuracy = underfit / high bias,
      regardless of how stable the model was across folds)

Reference lines: horizontal at 0.50 (coin flip -- underfit / high-bias threshold),
vertical at the median fold-to-fold std across all 12 models on that dataset (typical
variance for this dataset -- points to the right are less stable than average).
Ideal quadrant = top-left (high final accuracy, low variance). To keep the chart
readable, individual models are NOT all labeled -- only the 3 extremes per dataset
(highest final accuracy, lowest final accuracy, highest variance) are annotated;
the rest are plain dots colored by model family, per the legend.

Outputs (saved to reports/figures/):
  variance_tradeoff_dataset1_basic_daily.png
  variance_tradeoff_dataset2_90day_lookback.png
  variance_tradeoff_dataset3_technical.png

Usage:
    python scripts/plot_variance_tradeoff.py
    python scripts/plot_variance_tradeoff.py --open
"""

import argparse
import subprocess
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CSV_PATH     = PROJECT_ROOT / "reports" / "tables" / "model_comparison.csv"
OUT_DIR      = PROJECT_ROOT / "reports" / "figures"

CV_FOLDS = ["1", "2", "3", "4", "5"]

DATASETS = [
    ("dataset_basic_daily",    "Dataset 1 (Basic Daily)",         "variance_tradeoff_dataset1_basic_daily.png"),
    ("dataset_90day_lookback", "Dataset 2 (90-Day Lookback)",     "variance_tradeoff_dataset2_90day_lookback.png"),
    ("dataset_technical",      "Dataset 3 (Technical Indicators)", "variance_tradeoff_dataset3_technical.png"),
]

FAMILY = {
    "LR": "Linear", "Bagging_LR": "Linear",
    "DT": "Tree / Bagging", "RF": "Tree / Bagging", "ET": "Tree / Bagging", "Bagging_DT": "Tree / Bagging",
    "XGB": "Boosting", "LGBM": "Boosting", "HGB": "Boosting", "CatBoost": "Boosting",
    "KNN": "Other", "MLP": "Other",
}
FAMILY_COLORS = {
    "Linear": "#4C72B0",
    "Tree / Bagging": "#DD8452",
    "Boosting": "#55A868",
    "Other": "#8172B2",
}


def load() -> pd.DataFrame:
    if not CSV_PATH.exists():
        sys.exit(f"File not found: {CSV_PATH}\nRun train.py first.")
    return pd.read_csv(CSV_PATH, dtype={"fold": str})


def build_summary(df: pd.DataFrame, dataset: str) -> pd.DataFrame:
    sub = df[df["dataset"] == dataset]
    cv = sub[sub["fold"].isin(CV_FOLDS)].groupby("model")["accuracy"].std().rename("cv_std")
    final = sub[sub["fold"] == "final"].set_index("model")["accuracy"].rename("final_accuracy")
    out = pd.concat([cv, final], axis=1).dropna().reset_index().rename(columns={"index": "model"})
    out["family"] = out["model"].map(FAMILY)
    return out


def plot_one(summary: pd.DataFrame, label: str, filename: str) -> Path:
    median_std = summary["cv_std"].median()

    fig, ax = plt.subplots(figsize=(7.5, 6.5))

    for family, color in FAMILY_COLORS.items():
        fam_rows = summary[summary["family"] == family]
        if fam_rows.empty:
            continue
        ax.scatter(fam_rows["cv_std"], fam_rows["final_accuracy"], s=90, color=color,
                   edgecolor="black", linewidth=0.6, zorder=3, label=family)

    # Annotate only 4 points per dataset -- highest/lowest final accuracy, highest
    # variance, and the best "sweet spot" (highest accuracy among below-median-
    # variance models) -- to keep the other ~8 models as uncluttered plain dots.
    below_median = summary[summary["cv_std"] <= median_std]
    extremes = {
        summary.loc[summary["final_accuracy"].idxmax(), "model"],
        summary.loc[summary["final_accuracy"].idxmin(), "model"],
        summary.loc[summary["cv_std"].idxmax(), "model"],
        below_median.loc[below_median["final_accuracy"].idxmax(), "model"],
    }
    sweet_spot = below_median.loc[below_median["final_accuracy"].idxmax(), "model"]
    for _, row in summary[summary["model"].isin(extremes)].iterrows():
        text = f"{row['model']} (best trade-off)" if row["model"] == sweet_spot else row["model"]
        ax.annotate(text, (row["cv_std"], row["final_accuracy"]),
                    xytext=(6, 6), textcoords="offset points", fontsize=9, fontweight="bold")

    ax.axhline(0.50, color="grey", ls=":", lw=1.2, label="Coin flip (50%) -- high-bias threshold")
    ax.axvline(median_std, color="black", ls="--", lw=1.0,
               label=f"Median fold-to-fold {chr(963)} = {median_std:.3f}")

    ax.yaxis.set_major_formatter(mtick.PercentFormatter(1.0))
    ax.set_xlabel(f"Variance -- fold-to-fold accuracy std-dev, CV folds 1-5 ({chr(963)})")
    ax.set_ylabel("Bias proxy -- final (2024 held-out) accuracy")
    ax.set_title(f"Bias-Variance Trade-off -- {label}\n"
                 "Top-left = ideal (high accuracy, low variance); bottom = high bias (underfit)",
                 fontsize=10.5)
    ax.legend(fontsize=8, loc="best")
    ax.grid(alpha=0.3)

    fig.tight_layout()
    out_path = OUT_DIR / filename
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"  Saved: {out_path}")
    return out_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--open", action="store_true", help="Open figures after saving")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading model_comparison.csv ...")
    df = load()
    print(f"  {df['dataset'].nunique()} datasets, {df['model'].nunique()} models\n")

    print("Generating bias-variance trade-off scatter plots ...")
    paths = []
    for dataset, label, filename in DATASETS:
        summary = build_summary(df, dataset)
        if summary.empty:
            print(f"  WARNING: no data for {dataset}, skipping.")
            continue
        paths.append(plot_one(summary, label, filename))

    if args.open:
        opener = "start" if sys.platform.startswith("win") else (
            "open" if sys.platform == "darwin" else "xdg-open")
        for p in paths:
            subprocess.run([opener, str(p)], shell=sys.platform.startswith("win"))

    print("\nDone.")


if __name__ == "__main__":
    main()
