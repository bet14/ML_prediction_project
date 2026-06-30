"""
bayesian_search.py -- Bayesian hyperparameter search for GBP/USD direction models.

STATUS: production

Uses Optuna to optimise hyperparameters for each model type.
Search runs on folds 1-4 (inner CV); fold 5 used as held-out validation.
Best params saved to models/search_results/{model}_{dataset}_best_params.json.
Run train.py afterwards -- it auto-loads best_params.json before fitting.

All model definitions (search spaces included) live in model_registry.py.
Adding a new model requires no changes here.

Usage:
    python src/models/bayesian_search.py                           # RF, 50 trials
    python src/models/bayesian_search.py --models LR RF --trials 100
    python src/models/bayesian_search.py --models RF XGB LGBM MLP --trials 80
"""

import argparse
import json
import os
import sys
import warnings

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.evaluation.metrics import compute_metrics
from src.evaluation.walk_forward_cv import get_folds
from src.models.model_registry import REGISTRY
from src.models.train import build_pipeline

warnings.filterwarnings("ignore")

PROCESSED_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "processed")
SEARCH_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "models", "search_results")

DATASET_FILES = {
    "dataset_basic_daily": "dataset_basic_daily.csv",
    "dataset_90day_lookback": "dataset_90day_lookback.csv",
    "dataset_technical": "dataset_technical.csv",
}

SEARCH_FOLD_INDICES = [0, 1, 2, 3]  # inner CV folds
VALID_FOLD_INDEX = 4                 # held-out validation fold


def run_search(
    model_name: str,
    dataset_name: str = "dataset_basic_daily",
    n_trials: int = 50,
    verbose: bool = True,
) -> dict:
    """
    Run Bayesian search for one model on one dataset.

    Optimises mean F1-macro across folds 1-4, validates on fold 5.
    Saves best params to models/search_results/{model}_{dataset}_best_params.json.
    Returns the best params dict.
    """
    try:
        import optuna
    except ImportError:
        raise ImportError("optuna not installed. Run: pip install optuna")

    if model_name not in REGISTRY:
        raise ValueError(f"Model {model_name!r} not in REGISTRY. Add it to model_registry.py.")

    optuna.logging.set_verbosity(optuna.logging.WARNING)

    csv_path = os.path.join(PROCESSED_DIR, DATASET_FILES[dataset_name])
    df = pd.read_csv(csv_path, index_col=0, parse_dates=True)
    folds = get_folds(df)

    if VALID_FOLD_INDEX >= len(folds):
        raise ValueError(f"Not enough folds (need >= {VALID_FOLD_INDEX + 1}, got {len(folds)})")

    search_folds = [folds[i] for i in SEARCH_FOLD_INDICES if i < len(folds)]
    X_val_train, y_val_train, X_val_test, y_val_test = folds[VALID_FOLD_INDEX]

    suggest_fn = REGISTRY[model_name]["suggest"]

    def objective(trial):
        params = suggest_fn(trial)
        scores = []
        for X_train, y_train, X_test, y_test in search_folds:
            pipe = build_pipeline(model_name, params)
            pipe.fit(X_train, y_train)
            y_pred = pipe.predict(X_test)
            scores.append(compute_metrics(y_test, y_pred)["f1_macro"])
        return float(np.mean(scores))

    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=n_trials, show_progress_bar=False)

    best_params = dict(study.best_params)

    # Validate on fold 5
    pipe = build_pipeline(model_name, best_params)
    pipe.fit(X_val_train, y_val_train)
    val_metrics = compute_metrics(y_val_test, pipe.predict(X_val_test))

    if verbose:
        print(
            f"  [{model_name}] best inner f1={study.best_value:.4f} "
            f"| val acc={val_metrics['accuracy']:.3f} f1={val_metrics['f1_macro']:.3f} "
            f"| params={best_params}"
        )

    os.makedirs(SEARCH_DIR, exist_ok=True)
    out_path = os.path.join(SEARCH_DIR, f"{model_name}_{dataset_name}_best_params.json")
    with open(out_path, "w") as f:
        json.dump(best_params, f, indent=2)

    return best_params


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bayesian hyperparameter search")
    parser.add_argument("--dataset", default="dataset_basic_daily",
                        choices=list(DATASET_FILES.keys()))
    parser.add_argument("--models", nargs="+", default=["RF"],
                        choices=list(REGISTRY.keys()))
    parser.add_argument("--trials", type=int, default=50,
                        help="Optuna trials per model (default 50)")
    args = parser.parse_args()

    print(f"Dataset : {args.dataset}")
    print(f"Models  : {args.models}")
    print(f"Trials  : {args.trials}")
    print()

    all_best = {}
    for model_name in args.models:
        print(f"Searching {model_name}...")
        all_best[model_name] = run_search(model_name, args.dataset, args.trials)

    print()
    print("=== Best params found ===")
    for m, p in all_best.items():
        print(f"  {m}: {p}")
    print(f"\nSaved to: models/search_results/")
