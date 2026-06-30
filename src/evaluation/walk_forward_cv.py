"""
walk_forward_cv.py -- Expanding-window time-series cross-validation for GBP/USD prediction.

STATUS: production

Splits a DataFrame by year into expanding train/test folds:
  Fold 1: train [2014-2018]  test [2019]
  Fold 2: train [2014-2019]  test [2020]
  Fold 3: train [2014-2020]  test [2021]
  Fold 4: train [2014-2021]  test [2022]
  Fold 5: train [2014-2022]  test [2023]
  Final:  train [2014-2023]  test [2024]  <- held-out final evaluation

Usage:
    from src.evaluation.walk_forward_cv import get_folds, describe_folds
    folds = get_folds(df)
    describe_folds(folds)
"""

import pandas as pd
from typing import List, Tuple


FoldType = Tuple[pd.DataFrame, pd.Series, pd.DataFrame, pd.Series]


def get_folds(
    df: pd.DataFrame,
    target_col: str = "Direction",
    first_test_year: int = 2019,
    n_test_years: int = 1,
) -> List[FoldType]:
    """
    Generate expanding-window train/test splits by year.

    Parameters
    ----------
    df : DataFrame with DatetimeIndex, already cleaned (NaN rows in target dropped)
    target_col : column name for the prediction target
    first_test_year : first year used as test set (default 2019)
    n_test_years : number of consecutive years per test window (default 1)

    Returns
    -------
    List of (X_train, y_train, X_test, y_test) tuples, ordered by test year.
    The last tuple is the held-out final evaluation (test = last year in data).
    Rows where target is NaN are dropped before splitting.
    """
    df = df.dropna(subset=[target_col]).copy()
    feature_cols = [c for c in df.columns if c != target_col]

    years = sorted(df.index.year.unique())
    last_year = years[-1]

    folds: List[FoldType] = []
    test_start = first_test_year

    while test_start <= last_year:
        test_end = test_start + n_test_years - 1
        if test_end > last_year:
            break

        train_mask = df.index.year < test_start
        test_mask = (df.index.year >= test_start) & (df.index.year <= test_end)

        if train_mask.sum() == 0 or test_mask.sum() == 0:
            test_start += n_test_years
            continue

        X_train = df.loc[train_mask, feature_cols]
        y_train = df.loc[train_mask, target_col].astype(int)
        X_test = df.loc[test_mask, feature_cols]
        y_test = df.loc[test_mask, target_col].astype(int)

        folds.append((X_train, y_train, X_test, y_test))
        test_start += n_test_years

    return folds


def describe_folds(folds: List[FoldType]) -> None:
    """Print a human-readable summary of each fold's date range and size."""
    for i, (X_train, y_train, X_test, y_test) in enumerate(folds):
        label = "Final " if i == len(folds) - 1 else f"Fold {i + 1}"
        print(
            f"{label}: "
            f"train {X_train.index[0].date()} -> {X_train.index[-1].date()} "
            f"({len(X_train):>4} rows) | "
            f"test  {X_test.index[0].date()} -> {X_test.index[-1].date()} "
            f"({len(X_test):>4} rows)"
        )


if __name__ == "__main__":
    import sys
    import os

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

    DATA_PATH = os.path.join(
        os.path.dirname(__file__), "..", "..", "data", "processed", "dataset_basic_daily.csv"
    )
    df = pd.read_csv(DATA_PATH, index_col=0, parse_dates=True)
    folds = get_folds(df)
    print(f"Total folds: {len(folds)}")
    describe_folds(folds)
