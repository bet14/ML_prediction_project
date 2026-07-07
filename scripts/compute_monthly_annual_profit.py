"""
compute_monthly_annual_profit.py -- Reproduce the paper's two evaluation schemes
(Guyard & Deriaz 2024, Section 5.3) for Accuracy and Profit, on the 2024 held-out
year, for all 12 models x 3 datasets.

STATUS: scratch / one-off (populates the Evaluation slide's Monthly + Annual table)

Two schemes, both evaluated on the full 2024 test year:

  Annual  -- fit once on 2014-2023, predict the whole of 2024 in one shot.
             (Same pipeline already saved as *_foldfinal.joblib by train.py.)

  Monthly -- fit on 2014-2023, predict January 2024; then refit on
             2014-2023 + January 2024 (using the *real* January labels), predict
             February 2024; and so on through December. The 12 monthly
             out-of-sample chunks are concatenated back into one 2024 series
             before computing Accuracy/Profit, so Monthly and Annual are
             comparable like-for-like (both are "how did the whole of 2024 go").

Uses each model's existing Bayesian-searched best_params (no new search) --
only the model's own hyperparameters are fixed; the training data changes.

Profit formula (P(0) = 0, product starts at 1.0 so profit_pct = (P(t)-1)*100):

    P(t) = prod_{i=1..t} [ 1{y_pred(i)=1} * C(i)/C(i-1) + 1{y_pred(i)=0} * C(i-1)/C(i) ]

Usage:
    python scripts/compute_monthly_annual_profit.py
    python scripts/compute_monthly_annual_profit.py --datasets dataset_basic_daily --models LR XGB
"""

import argparse
import os
import sys
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.evaluation.walk_forward_cv import get_folds
from src.models.train import build_pipeline, load_best_params

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
TRAINED_DIR = PROJECT_ROOT / "models" / "trained"
TABLES_DIR = PROJECT_ROOT / "reports" / "tables"
OUT_PATH = TABLES_DIR / "monthly_annual_profit_2024.csv"

DATASET_FILES = {
    "dataset_basic_daily": "dataset_basic_daily.csv",
    "dataset_90day_lookback": "dataset_90day_lookback.csv",
    "dataset_technical": "dataset_technical.csv",
}

ALL_MODELS = [
    "LR", "Bagging_LR", "RF", "ET", "DT", "Bagging_DT",
    "KNN", "MLP", "XGB", "LGBM", "HGB", "CatBoost",
]

CLOSE_COL = "GBP_USD_close"


def paper_profit_pct(y_pred: np.ndarray, closes: np.ndarray) -> float:
    """closes has length len(y_pred) + 1; closes[0] is the close price the day before
    the first predicted day."""
    p = 1.0
    for i, pred in enumerate(y_pred):
        c_prev, c_curr = closes[i], closes[i + 1]
        p *= (c_curr / c_prev) if pred == 1 else (c_prev / c_curr)
    return (p - 1.0) * 100.0


def _upsert(rows: list[dict]) -> None:
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    new = pd.DataFrame(rows)
    if OUT_PATH.exists():
        existing = pd.read_csv(OUT_PATH)
        key_cols = ["dataset", "model"]
        keys = set(map(tuple, new[key_cols].values.tolist()))
        existing = existing[~existing[key_cols].apply(lambda r: tuple(r) in keys, axis=1)]
        new = pd.concat([existing, new], ignore_index=True)
    new.to_csv(OUT_PATH, index=False)


def run_dataset(dataset_name: str, model_names: list, verbose: bool = True) -> list:
    csv_path = PROCESSED_DIR / DATASET_FILES[dataset_name]
    df = pd.read_csv(csv_path, index_col=0, parse_dates=True)
    folds = get_folds(df)
    X_train_final, y_train_final, X_test, y_test = folds[-1]

    prev_close_0 = float(df.loc[X_train_final.index[-1], CLOSE_COL])

    year_months = sorted({(d.year, d.month) for d in X_test.index})

    rows = []
    for model_name in model_names:
        t_start = time.time()
        best_params = load_best_params(model_name, dataset_name)

        # --- Annual: reuse the pipeline already trained by train.py -------------
        model_path = TRAINED_DIR / f"{model_name}_{dataset_name}_foldfinal.joblib"
        if not model_path.exists():
            print(f"  [SKIP] missing {model_path.name}")
            continue
        pipe_annual = joblib.load(model_path)
        y_pred_annual = pipe_annual.predict(X_test)
        acc_annual = accuracy_score(y_test, y_pred_annual)
        closes_annual = np.concatenate([[prev_close_0], X_test[CLOSE_COL].values.astype(float)])
        profit_annual = paper_profit_pct(np.asarray(y_pred_annual), closes_annual)

        # --- Monthly: refit each month on train + all realized months so far -----
        cum_X, cum_y = X_train_final.copy(), y_train_final.copy()
        y_true_chunks, y_pred_chunks = [], []
        closes_monthly = [prev_close_0]

        for (yr, mo) in year_months:
            mask = (X_test.index.year == yr) & (X_test.index.month == mo)
            X_month, y_month = X_test.loc[mask], y_test.loc[mask]

            pipe = build_pipeline(model_name, best_params)
            pipe.fit(cum_X, cum_y)
            y_pred_month = pipe.predict(X_month)

            y_true_chunks.append(y_month.values)
            y_pred_chunks.append(np.asarray(y_pred_month))
            closes_monthly.extend(X_month[CLOSE_COL].values.astype(float).tolist())

            cum_X = pd.concat([cum_X, X_month])
            cum_y = pd.concat([cum_y, y_month])

        y_true_monthly = np.concatenate(y_true_chunks)
        y_pred_monthly = np.concatenate(y_pred_chunks)
        acc_monthly = accuracy_score(y_true_monthly, y_pred_monthly)
        profit_monthly = paper_profit_pct(y_pred_monthly, np.array(closes_monthly))

        elapsed = time.time() - t_start
        row = {
            "dataset": dataset_name,
            "model": model_name,
            "acc_annual": acc_annual,
            "profit_annual_pct": profit_annual,
            "acc_monthly": acc_monthly,
            "profit_monthly_pct": profit_monthly,
            "elapsed_s": round(elapsed, 1),
        }
        rows.append(row)
        _upsert([row])
        if verbose:
            print(
                f"[{dataset_name:<24} {model_name:<12}] "
                f"annual acc={acc_annual:.3f} profit={profit_annual:+.2f}%  |  "
                f"monthly acc={acc_monthly:.3f} profit={profit_monthly:+.2f}%  "
                f"({elapsed:.1f}s)"
            )
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--datasets", nargs="+", default=list(DATASET_FILES.keys()))
    parser.add_argument("--models", nargs="+", default=ALL_MODELS)
    args = parser.parse_args()

    for dataset_name in args.datasets:
        print(f"\n=== {dataset_name} ===")
        run_dataset(dataset_name, args.models)

    print(f"\nSaved -> {OUT_PATH}")


if __name__ == "__main__":
    main()
