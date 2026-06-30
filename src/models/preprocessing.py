"""
preprocessing.py -- Custom sklearn-compatible transformers for GBP/USD ML pipeline.

Defined here (not inline in train.py) so fitted Pipeline objects serialised with
joblib can be loaded from any script without needing to import train.py first.
"""

import numpy as np
from sklearn.base import BaseEstimator, TransformerMixin


class InfinityToNaNTransformer(BaseEstimator, TransformerMixin):
    """
    Replace +inf and -inf with NaN so downstream SimpleImputer can fill them.
    Needed because UK_cpi_yoy_log can be -inf during deflation periods (log of negative YoY).
    """

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        X = np.array(X, dtype=float)
        X[~np.isfinite(X)] = np.nan
        return X
