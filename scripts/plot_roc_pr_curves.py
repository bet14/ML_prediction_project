"""
plot_roc_pr_curves.py -- ROC and Precision-Recall curves on the 2024 held-out test fold.

Loads trained pipelines from models/trained/{model}_dataset_basic_daily_foldfinal.joblib,
predicts on the final walk-forward fold (train 2014-2023 / test 2024 -- never touched
during training or Bayesian search), and plots ROC + PR curves side by side.

Output: reports/figures/roc_pr_curves.png

Usage:
    python scripts/plot_roc_pr_curves.py                           # default 4 models
    python scripts/plot_roc_pr_curves.py --models XGB HGB CatBoost  # custom selection
    python scripts/plot_roc_pr_curves.py --models all               # all trained models
    python scripts/plot_roc_pr_curves.py --open                     # open figure after saving
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

import joblib
import matplotlib.pyplot as plt
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    precision_recall_curve,
    roc_auc_score,
    roc_curve,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.evaluation.walk_forward_cv import get_folds

DATA_PATH   = PROJECT_ROOT / "data" / "processed" / "dataset_basic_daily.csv"
TRAINED_DIR = PROJECT_ROOT / "models" / "trained"
OUT_DIR     = PROJECT_ROOT / "reports" / "figures"
DATASET_NAME = "dataset_basic_daily"

DEFAULT_MODELS = ["XGB", "HGB", "Bagging_LR", "LGBM"]


def resolve_models(requested: list) -> list:
    if requested == ["all"]:
        paths = TRAINED_DIR.glob(f"*_{DATASET_NAME}_foldfinal.joblib")
        return sorted(p.name.split(f"_{DATASET_NAME}")[0] for p in paths)
    return requested


def load_final_fold():
    df = pd.read_csv(DATA_PATH, index_col=0, parse_dates=True)
    folds = get_folds(df)
    X_test, y_test = folds[-1][2], folds[-1][3]
    return X_test, y_test


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models", nargs="+", default=DEFAULT_MODELS,
                        help=f"Model names to plot, or 'all'. Default: {DEFAULT_MODELS}")
    parser.add_argument("--open", action="store_true", help="Open figure after saving")
    args = parser.parse_args()

    models = resolve_models(args.models)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading final fold (train 2014-2023 / test 2024) ...")
    X_test, y_test = load_final_fold()
    print(f"  test rows: {len(X_test)}\n")

    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))
    baseline = y_test.mean()

    for model_name in models:
        model_path = TRAINED_DIR / f"{model_name}_{DATASET_NAME}_foldfinal.joblib"
        if not model_path.exists():
            print(f"  [{model_name}] SKIPPED -- not found: {model_path.name}")
            continue

        pipe = joblib.load(model_path)
        try:
            y_proba = pipe.predict_proba(X_test)[:, 1]
        except AttributeError:
            print(f"  [{model_name}] SKIPPED -- no predict_proba")
            continue

        fpr, tpr, _ = roc_curve(y_test, y_proba)
        auc = roc_auc_score(y_test, y_proba)
        precision, recall, _ = precision_recall_curve(y_test, y_proba)
        ap = average_precision_score(y_test, y_proba)

        axes[0].plot(fpr, tpr, lw=2, label=f"{model_name} (AUC = {auc:.3f})")
        axes[1].plot(recall, precision, lw=2, label=f"{model_name} (AP = {ap:.3f})")
        print(f"  [{model_name}] AUC-ROC = {auc:.3f}  AP = {ap:.3f}")

    axes[0].plot([0, 1], [0, 1], linestyle="--", color="grey", label="Chance")
    axes[0].set_xlabel("False Positive Rate")
    axes[0].set_ylabel("True Positive Rate")
    axes[0].set_title("ROC Curve -- 2024 Held-Out Test")
    axes[0].legend(loc="lower right", fontsize=8)
    axes[0].grid(alpha=0.3)

    axes[1].axhline(baseline, linestyle="--", color="grey",
                     label=f"Baseline (positive rate = {baseline:.3f})")
    axes[1].set_xlabel("Recall")
    axes[1].set_ylabel("Precision")
    axes[1].set_title("Precision-Recall Curve -- 2024 Held-Out Test")
    axes[1].legend(loc="lower left", fontsize=8)
    axes[1].grid(alpha=0.3)

    fig.tight_layout()
    path = OUT_DIR / "roc_pr_curves.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"\nSaved: {path}")

    if args.open:
        if sys.platform == "win32":
            os.startfile(path)
        else:
            subprocess.run(["open" if sys.platform == "darwin" else "xdg-open", str(path)])


if __name__ == "__main__":
    main()
