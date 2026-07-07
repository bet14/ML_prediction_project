"""
train.py -- Model training pipeline for GBP/USD direction prediction.

STATUS: production

Trains models across walk-forward folds for a given processed dataset.
All model definitions live in model_registry.py -- no changes needed here to add models.

Usage:
    python src/models/train.py                          # Dataset 1, LR + RF, all folds
    python src/models/train.py --models LR RF XGB       # specific models
    python src/models/train.py --fold 0                 # single fold (0-based)
"""

import argparse
import json
import os
import sys
import time

import joblib
import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import RobustScaler

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.evaluation.metrics import compute_metrics
from src.evaluation.walk_forward_cv import get_folds
from src.models.model_registry import REGISTRY
from src.models.preprocessing import InfinityToNaNTransformer

PROCESSED_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "processed")
TRAINED_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "models", "trained")
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "reports", "tables")

DATASET_FILES = {
    "dataset_basic_daily": "dataset_basic_daily.csv",
    "dataset_90day_lookback": "dataset_90day_lookback.csv",
    "dataset_technical": "dataset_technical.csv",
}

GBPUSD_CLOSE_COL = "GBP_USD_close"


def build_pipeline(model_name: str, params: dict) -> Pipeline:
    """
    Build a full sklearn Pipeline for a given model.
    Steps: inf->NaN cleaner → median imputer → optional RobustScaler → estimator.
    Scale flag and estimator come from REGISTRY -- no logic here.
    """
    entry = REGISTRY[model_name]
    steps = [
        ("replace_inf", InfinityToNaNTransformer()),
        ("imputer", SimpleImputer(strategy="median")),
    ]
    if entry["scale"]:
        steps.append(("scaler", RobustScaler()))
    steps.append(("model", entry["build"](params)))
    return Pipeline(steps)


def load_best_params(model_name: str, dataset_name: str) -> dict:
    """Load Bayesian search best params if available; else return {}."""
    path = os.path.join(
        os.path.dirname(__file__), "..", "..",
        "models", "search_results",
        f"{model_name}_{dataset_name}_best_params.json",
    )
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}


def _compute_log_returns(X_test: pd.DataFrame):
    """Daily log returns of GBP/USD aligned to X_test rows (first element = 0.0)."""
    if GBPUSD_CLOSE_COL not in X_test.columns:
        return None
    close = X_test[GBPUSD_CLOSE_COL].values.astype(float)
    with np.errstate(divide="ignore", invalid="ignore"):
        daily = np.where(
            (close[:-1] > 0) & (close[1:] > 0),
            np.log(close[1:] / close[:-1]),
            0.0,
        )
    return np.concatenate([[0.0], daily])


def train_all(
    dataset_name: str = "dataset_basic_daily",
    model_names: list = None,
    fold_indices: list = None,
    verbose: bool = True,
    skip_existing: bool = False,
) -> pd.DataFrame:
    """
    Train all requested models across specified walk-forward folds.

    Returns DataFrame with one row per (dataset, model, fold).
    Results are appended/updated in reports/tables/model_comparison.csv.
    """
    if model_names is None:
        model_names = ["LR", "RF"]

    csv_path = os.path.join(PROCESSED_DIR, DATASET_FILES[dataset_name])
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Dataset not found: {csv_path}")

    df = pd.read_csv(csv_path, index_col=0, parse_dates=True)
    folds = get_folds(df)

    if fold_indices is None:
        fold_indices = list(range(len(folds)))

    os.makedirs(TRAINED_DIR, exist_ok=True)
    os.makedirs(RESULTS_DIR, exist_ok=True)

    records = []

    for model_name in model_names:
        if model_name not in REGISTRY:
            raise ValueError(f"Model {model_name!r} not in REGISTRY. Add it to model_registry.py.")

        best_params = load_best_params(model_name, dataset_name)
        if verbose and best_params:
            print(f"  [{model_name}] loaded best_params: {best_params}")

        for fi in fold_indices:
            if fi >= len(folds):
                print(f"  [{model_name}] fold {fi} out of range (max {len(folds)-1}) -- skip")
                continue

            X_train, y_train, X_test, y_test = folds[fi]
            fold_label = "final" if fi == len(folds) - 1 else str(fi + 1)

            model_path = os.path.join(
                TRAINED_DIR,
                f"{model_name}_{dataset_name}_fold{fold_label}.joblib",
            )

            if skip_existing and os.path.exists(model_path):
                if verbose:
                    print(f"  [{model_name}] fold={fold_label:<6} SKIPPED (file exists)")
                continue

            t0 = time.time()
            pipe = build_pipeline(model_name, best_params)
            pipe.fit(X_train, y_train)
            elapsed = time.time() - t0

            y_pred = pipe.predict(X_test)
            y_proba = None
            try:
                y_proba = pipe.predict_proba(X_test)[:, 1]
            except AttributeError:
                pass

            metrics = compute_metrics(
                y_test, y_pred,
                y_proba=y_proba,
                returns=_compute_log_returns(X_test),
            )

            joblib.dump(pipe, model_path)

            record = {
                "dataset": dataset_name,
                "model": model_name,
                "fold": fold_label,
                "train_rows": len(X_train),
                "test_rows": len(X_test),
                "train_start": str(X_train.index[0].date()),
                "test_start": str(X_test.index[0].date()),
                "test_end": str(X_test.index[-1].date()),
                "elapsed_s": round(elapsed, 2),
                **metrics,
            }
            records.append(record)

            if verbose:
                auc = metrics["auc_roc"]
                sharpe = metrics["sharpe_proxy"]
                print(
                    f"  [{model_name}] fold={fold_label:<6} "
                    f"acc={metrics['accuracy']:.3f}  "
                    f"f1={metrics['f1_macro']:.3f}  "
                    f"auc={f'{auc:.3f}' if auc is not None else 'N/A':>5}  "
                    f"sharpe={f'{sharpe:.3f}' if sharpe is not None else 'N/A':>7}  "
                    f"({elapsed:.1f}s)"
                )

    results_df = pd.DataFrame(records)

    comparison_path = os.path.join(RESULTS_DIR, "model_comparison.csv")
    if os.path.exists(comparison_path):
        existing = pd.read_csv(comparison_path)
        key_cols = ["dataset", "model", "fold"]
        new_keys = results_df.set_index(key_cols).index
        existing = existing[~existing.set_index(key_cols).index.isin(new_keys)]
        results_df = pd.concat([existing, results_df], ignore_index=True)

    results_df.to_csv(comparison_path, index=False)
    return results_df


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train GBP/USD direction models")
    parser.add_argument("--dataset", default="dataset_basic_daily",
                        choices=list(DATASET_FILES.keys()))
    parser.add_argument("--models", nargs="+", default=["LR", "RF"],
                        choices=list(REGISTRY.keys()))
    parser.add_argument("--fold", type=int, default=None,
                        help="Single fold index (0-based). Default: all.")
    parser.add_argument("--skip-existing", action="store_true",
                        help="Skip folds whose .joblib file already exists (resume mode).")
    args = parser.parse_args()

    fold_indices = [args.fold] if args.fold is not None else None
    print(f"Dataset        : {args.dataset}")
    print(f"Models         : {args.models}")
    print(f"Folds          : {fold_indices or 'all'}")
    print(f"Skip existing  : {args.skip_existing}")
    print()

    results = train_all(args.dataset, args.models, fold_indices,
                        skip_existing=args.skip_existing)

    print()
    print("=== Summary ===")
    cols = ["model", "fold", "accuracy", "f1_macro", "auc_roc", "sharpe_proxy"]
    print(results[cols].to_string(index=False))
    print("\nSaved: reports/tables/model_comparison.csv")
