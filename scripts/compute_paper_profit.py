"""
compute_paper_profit.py -- Compute Profit exactly as defined in the reference paper
(Guyard & Deriaz 2024, Section 5.3) for the 2024 held-out fold.

STATUS: scratch / one-off (used to populate the "Evaluation: Accuracy & Profit"
slide of reports/draft_final_presentation.html with a real Profit number instead
of the Sharpe proxy that was mislabeled as "Profit").

Formula (paper, P(0) = 0, product starts at 1.0 here so profit_pct = (P(t)-1)*100):

    P(t) = prod_{i=1..t} [ 1{y_pred(i)=1} * C(i)/C(i-1) + 1{y_pred(i)=0} * C(i-1)/C(i) ]

This is a long/short (always-in-market) strategy: predict UP -> go long for that
day, predict DOWN -> go short for that day. Different from src/evaluation/backtest.py,
which simulates a long/flat strategy on log returns -- this script reproduces the
paper's own metric so the numbers are directly comparable to Table 2-4 of the PDF.

Usage:
    python scripts/compute_paper_profit.py
"""

import os
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.evaluation.walk_forward_cv import get_folds

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
TRAINED_DIR = PROJECT_ROOT / "models" / "trained"
TABLES_DIR = PROJECT_ROOT / "reports" / "tables"

DATASET_FILES = {
    "dataset_basic_daily": "dataset_basic_daily.csv",
    "dataset_90day_lookback": "dataset_90day_lookback.csv",
    "dataset_technical": "dataset_technical.csv",
}

MODELS = [
    "LR", "Bagging_LR", "RF", "ET", "DT", "Bagging_DT",
    "KNN", "MLP", "XGB", "LGBM", "HGB", "CatBoost",
]

CLOSE_COL = "GBP_USD_close"


def paper_profit_pct(y_pred: np.ndarray, closes: np.ndarray) -> float:
    """
    closes must have length len(y_pred) + 1: closes[0] is C(0), the close price
    on the day immediately before the first predicted day.
    """
    p = 1.0
    for i, pred in enumerate(y_pred):
        c_prev = closes[i]
        c_curr = closes[i + 1]
        if pred == 1:
            p *= c_curr / c_prev
        else:
            p *= c_prev / c_curr
    return (p - 1.0) * 100.0


def main():
    rows = []
    for dataset_name, filename in DATASET_FILES.items():
        csv_path = PROCESSED_DIR / filename
        df = pd.read_csv(csv_path, index_col=0, parse_dates=True)
        folds = get_folds(df)
        X_train_final, y_train_final, X_test, y_test = folds[-1]

        # C(0): close price on the last training day, immediately before the
        # first test day -- needed so the first day's ratio is well-defined.
        prev_close = df.loc[X_train_final.index[-1], CLOSE_COL]
        closes = np.concatenate([[prev_close], X_test[CLOSE_COL].values.astype(float)])

        for model_name in MODELS:
            model_path = TRAINED_DIR / f"{model_name}_{dataset_name}_foldfinal.joblib"
            if not model_path.exists():
                print(f"  [WARN] missing {model_path.name}")
                continue

            pipe = joblib.load(model_path)
            y_pred = pipe.predict(X_test)

            acc = accuracy_score(y_test, y_pred)
            profit = paper_profit_pct(np.asarray(y_pred), closes)

            rows.append({
                "dataset": dataset_name,
                "model": model_name,
                "accuracy": acc,
                "profit_pct": profit,
            })
            print(f"{dataset_name:<24} {model_name:<12} acc={acc:.4f}  profit={profit:+.2f}%")

    out = pd.DataFrame(rows)
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    out_path = TABLES_DIR / "paper_profit_2024.csv"
    out.to_csv(out_path, index=False)
    print(f"\nSaved -> {out_path}")


if __name__ == "__main__":
    main()
