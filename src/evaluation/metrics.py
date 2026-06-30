"""
metrics.py -- Pure evaluation metrics for GBP/USD direction prediction.

STATUS: production

All functions are stateless with no side effects -- safe to call in any order.

Usage:
    from src.evaluation.metrics import compute_metrics
    result = compute_metrics(y_true, y_pred, y_proba=proba_col, returns=log_returns)
    # result: {'accuracy': 0.54, 'f1_macro': 0.54, 'auc_roc': 0.55,
    #          'sharpe_proxy': 0.31, 'max_drawdown': -0.08}
"""

import numpy as np
from typing import Dict, Any, Optional
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score


def compute_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_proba: Optional[np.ndarray] = None,
    returns: Optional[np.ndarray] = None,
    trading_days_per_year: int = 252,
) -> Dict[str, Any]:
    """
    Compute all evaluation metrics for a single (model, fold) combination.

    Parameters
    ----------
    y_true  : true Direction labels, shape (n,), values in {0, 1}
    y_pred  : predicted Direction labels, shape (n,), values in {0, 1}
    y_proba : predicted probability of class 1, shape (n,) -- needed for auc_roc
    returns : daily log returns of GBP/USD on test days, shape (n,)
              Strategy: long when y_pred==1, flat otherwise.
              Needed for sharpe_proxy and max_drawdown.
    trading_days_per_year : annualisation factor for Sharpe (default 252)

    Returns
    -------
    dict with keys: accuracy, f1_macro, auc_roc, sharpe_proxy, max_drawdown
    Keys are None (not NaN) when the required input was not provided.
    """
    y_true = np.asarray(y_true, dtype=int)
    y_pred = np.asarray(y_pred, dtype=int)

    result: Dict[str, Any] = {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "f1_macro": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
        "auc_roc": None,
        "sharpe_proxy": None,
        "max_drawdown": None,
    }

    if y_proba is not None:
        y_proba = np.asarray(y_proba, dtype=float)
        try:
            result["auc_roc"] = float(roc_auc_score(y_true, y_proba))
        except ValueError:
            result["auc_roc"] = None

    if returns is not None:
        returns = np.asarray(returns, dtype=float)
        strategy_returns = np.where(y_pred == 1, returns, 0.0)
        result["sharpe_proxy"] = _annualised_sharpe(strategy_returns, trading_days_per_year)
        result["max_drawdown"] = _max_drawdown(strategy_returns)

    return result


def _annualised_sharpe(
    strategy_returns: np.ndarray,
    trading_days_per_year: int = 252,
) -> Optional[float]:
    """Annualised Sharpe ratio assuming risk-free rate = 0."""
    std = float(np.std(strategy_returns, ddof=1))
    if std == 0.0:
        return None
    mean = float(np.mean(strategy_returns))
    return mean / std * float(np.sqrt(trading_days_per_year))


def _max_drawdown(strategy_returns: np.ndarray) -> float:
    """
    Maximum peak-to-trough drawdown of the cumulative log-return equity curve.
    Returns a negative number (or 0 if no drawdown).
    """
    cumulative = np.cumsum(strategy_returns)
    running_max = np.maximum.accumulate(cumulative)
    drawdown = cumulative - running_max
    return float(np.min(drawdown))


if __name__ == "__main__":
    rng = np.random.default_rng(42)
    n = 252
    y_true = rng.integers(0, 2, n)
    y_pred = rng.integers(0, 2, n)
    y_proba = rng.uniform(0, 1, n)
    returns = rng.normal(0, 0.005, n)

    result = compute_metrics(y_true, y_pred, y_proba=y_proba, returns=returns)
    for k, v in result.items():
        print(f"  {k:<20} {v}")
