"""
model_registry.py -- Central registry of all ML models for GBP/USD prediction.

To add a new model:
  1. Write _build_<name>(params: dict) -> sklearn estimator
  2. Write _suggest_<name>(trial) -> dict  (Optuna search space)
  3. Add one entry to REGISTRY at the bottom

No other file needs to change.

'scale' = True  -> pipeline inserts RobustScaler before the estimator
                   (needed for distance/gradient-based models: LR, KNN, SVM, MLP)

Speed guide per fold (dataset_basic_daily, ~1300-2600 rows x 110 features):
  FAST  < 1 min : KNN, DT, ET, HGB, CatBoost, Bagging_DT, Bagging_LR, LR, RF, XGB, LGBM, MLP
  MED   1-5 min : GB, SVM_linear, Bagging_KNN
  SLOW  > 5 min : SVM_rbf, SVM_sigmoid, SVM_poly, Bagging_SVM_*  <- do not run at Cowork
"""

from sklearn.ensemble import (
    BaggingClassifier,
    ExtraTreesClassifier,
    GradientBoostingClassifier,
    HistGradientBoostingClassifier,
    RandomForestClassifier,
)
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import KNeighborsClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier

# ===========================================================================
# BUILD FUNCTIONS — return a bare (unfitted) sklearn-compatible estimator
# XGB / LGBM / CatBoost use lazy imports so registry loads even when absent
# ===========================================================================

# --- Linear / probabilistic ---

def _build_lr(p: dict):
    return LogisticRegression(
        C=p.get("C", 1.0), penalty=p.get("penalty", "l2"),
        solver="saga", max_iter=2000, random_state=42,
    )

# --- Neighbors ---

def _build_knn(p: dict):
    return KNeighborsClassifier(
        n_neighbors=p.get("n_neighbors", 5),
        metric=p.get("metric", "minkowski"),
        weights=p.get("weights", "uniform"),
        n_jobs=-1,
    )

# --- Tree ---

def _build_dt(p: dict):
    return DecisionTreeClassifier(
        max_depth=p.get("max_depth", None),
        min_samples_split=p.get("min_samples_split", 2),
        criterion=p.get("criterion", "gini"),
        random_state=42,
    )

# --- Ensembles (sklearn) ---

def _build_rf(p: dict):
    return RandomForestClassifier(
        n_estimators=p.get("n_estimators", 200),
        max_depth=p.get("max_depth", None),
        min_samples_leaf=p.get("min_samples_leaf", 1),
        random_state=42, n_jobs=-1,
    )

def _build_et(p: dict):
    return ExtraTreesClassifier(
        n_estimators=p.get("n_estimators", 200),
        max_depth=p.get("max_depth", None),
        max_features=p.get("max_features", "sqrt"),
        random_state=42, n_jobs=-1,
    )

def _build_gb(p: dict):
    return GradientBoostingClassifier(
        n_estimators=p.get("n_estimators", 100),
        learning_rate=p.get("learning_rate", 0.1),
        max_depth=p.get("max_depth", 3),
        random_state=42,
    )

def _build_hgb(p: dict):
    return HistGradientBoostingClassifier(
        max_iter=p.get("max_iter", 200),
        learning_rate=p.get("learning_rate", 0.1),
        max_depth=p.get("max_depth", None),
        l2_regularization=p.get("l2_regularization", 0.0),
        random_state=42,
    )

# --- Gradient boosting (external) ---

def _build_xgb(p: dict):
    from xgboost import XGBClassifier
    return XGBClassifier(
        n_estimators=p.get("n_estimators", 200),
        learning_rate=p.get("learning_rate", 0.05),
        max_depth=p.get("max_depth", 4),
        subsample=p.get("subsample", 0.8),
        eval_metric="logloss", random_state=42, verbosity=0,
    )

def _build_lgbm(p: dict):
    from lightgbm import LGBMClassifier
    return LGBMClassifier(
        n_estimators=p.get("n_estimators", 200),
        learning_rate=p.get("learning_rate", 0.05),
        num_leaves=p.get("num_leaves", 31),
        random_state=42, n_jobs=-1, verbose=-1,
    )

def _build_cb(p: dict):
    from catboost import CatBoostClassifier
    return CatBoostClassifier(
        iterations=p.get("iterations", 200),
        depth=p.get("depth", 6),
        learning_rate=p.get("learning_rate", 0.05),
        random_seed=42, verbose=0,
    )

# --- Neural net ---

def _build_mlp(p: dict):
    return MLPClassifier(
        hidden_layer_sizes=tuple(p.get("hidden_layer_sizes", [64, 32])),
        learning_rate_init=p.get("learning_rate_init", 0.001),
        alpha=p.get("alpha", 1e-4),
        max_iter=500, random_state=42,
    )

# --- SVM variants (SLOW on large folds — see speed guide above) ---

def _build_svm_linear(p: dict):
    return SVC(kernel="linear", C=p.get("C", 1.0),
               probability=True, random_state=42)

def _build_svm_rbf(p: dict):
    return SVC(kernel="rbf", C=p.get("C", 1.0), gamma=p.get("gamma", "scale"),
               probability=True, random_state=42)

def _build_svm_sigmoid(p: dict):
    return SVC(kernel="sigmoid", C=p.get("C", 1.0), gamma=p.get("gamma", "scale"),
               probability=True, random_state=42)

def _build_svm_poly(p: dict):
    return SVC(kernel="poly", C=p.get("C", 1.0), degree=p.get("degree", 3),
               gamma=p.get("gamma", "scale"), probability=True, random_state=42)

# --- Bagging variants ---

def _build_bagging_dt(p: dict):
    base = DecisionTreeClassifier(max_depth=p.get("max_depth", 5), random_state=42)
    return BaggingClassifier(
        estimator=base, n_estimators=p.get("n_estimators", 50),
        random_state=42, n_jobs=-1,
    )

def _build_bagging_lr(p: dict):
    # lbfgs (not saga): ~20x faster on wide feature sets (e.g. dataset_90day_lookback's
    # 9109 cols) for the same L2-penalty optimum -- saga was taking minutes per estimator.
    base = LogisticRegression(C=p.get("C", 1.0), solver="lbfgs",
                               max_iter=1000, random_state=42)
    return BaggingClassifier(
        estimator=base, n_estimators=p.get("n_estimators", 20),
        random_state=42, n_jobs=-1,
    )

def _build_bagging_knn(p: dict):
    base = KNeighborsClassifier(n_neighbors=p.get("n_neighbors", 5))
    return BaggingClassifier(
        estimator=base, n_estimators=p.get("n_estimators", 20),
        random_state=42, n_jobs=-1,
    )

def _build_bagging_svm_linear(p: dict):
    base = SVC(kernel="linear", C=p.get("C", 1.0), probability=True, random_state=42)
    return BaggingClassifier(estimator=base, n_estimators=p.get("n_estimators", 10),
                              random_state=42, n_jobs=-1)

def _build_bagging_svm_rbf(p: dict):
    base = SVC(kernel="rbf", C=p.get("C", 1.0), gamma=p.get("gamma", "scale"),
               probability=True, random_state=42)
    return BaggingClassifier(estimator=base, n_estimators=p.get("n_estimators", 10),
                              random_state=42, n_jobs=-1)

def _build_bagging_svm_sigmoid(p: dict):
    base = SVC(kernel="sigmoid", C=p.get("C", 1.0), gamma=p.get("gamma", "scale"),
               probability=True, random_state=42)
    return BaggingClassifier(estimator=base, n_estimators=p.get("n_estimators", 10),
                              random_state=42, n_jobs=-1)

def _build_bagging_svm_poly(p: dict):
    base = SVC(kernel="poly", C=p.get("C", 1.0), degree=p.get("degree", 3),
               probability=True, random_state=42)
    return BaggingClassifier(estimator=base, n_estimators=p.get("n_estimators", 10),
                              random_state=42, n_jobs=-1)


# ===========================================================================
# SUGGEST FUNCTIONS — return JSON-serialisable dict for Optuna trial
# ===========================================================================

def _suggest_lr(trial) -> dict:
    return {"C": trial.suggest_float("C", 1e-3, 10.0, log=True),
            "penalty": trial.suggest_categorical("penalty", ["l1", "l2"])}

def _suggest_knn(trial) -> dict:
    return {"n_neighbors": trial.suggest_int("n_neighbors", 1, 30),
            "metric": trial.suggest_categorical("metric", ["euclidean", "manhattan", "minkowski"]),
            "weights": trial.suggest_categorical("weights", ["uniform", "distance"])}

def _suggest_dt(trial) -> dict:
    return {"max_depth": trial.suggest_int("max_depth", 2, 20),
            "min_samples_split": trial.suggest_int("min_samples_split", 2, 20),
            "criterion": trial.suggest_categorical("criterion", ["gini", "entropy"])}

def _suggest_rf(trial) -> dict:
    return {"n_estimators": trial.suggest_int("n_estimators", 100, 500),
            "max_depth": trial.suggest_int("max_depth", 3, 20),
            "min_samples_leaf": trial.suggest_int("min_samples_leaf", 1, 20)}

def _suggest_et(trial) -> dict:
    return {"n_estimators": trial.suggest_int("n_estimators", 100, 500),
            "max_depth": trial.suggest_int("max_depth", 3, 20),
            "max_features": trial.suggest_categorical("max_features", ["sqrt", "log2"])}

def _suggest_gb(trial) -> dict:
    return {"n_estimators": trial.suggest_int("n_estimators", 50, 300),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
            "max_depth": trial.suggest_int("max_depth", 2, 6)}

def _suggest_hgb(trial) -> dict:
    return {"max_iter": trial.suggest_int("max_iter", 50, 300),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
            "max_depth": trial.suggest_int("max_depth", 2, 8),
            "l2_regularization": trial.suggest_float("l2_regularization", 0.0, 10.0)}

def _suggest_xgb(trial) -> dict:
    return {"n_estimators": trial.suggest_int("n_estimators", 100, 500),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
            "max_depth": trial.suggest_int("max_depth", 2, 8),
            "subsample": trial.suggest_float("subsample", 0.5, 1.0)}

def _suggest_lgbm(trial) -> dict:
    return {"n_estimators": trial.suggest_int("n_estimators", 100, 500),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
            "num_leaves": trial.suggest_int("num_leaves", 15, 127)}

def _suggest_cb(trial) -> dict:
    return {"iterations": trial.suggest_int("iterations", 100, 500),
            "depth": trial.suggest_int("depth", 2, 8),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True)}

def _suggest_mlp(trial) -> dict:
    n = trial.suggest_int("n_layers", 1, 3)
    size = trial.suggest_int("layer_size", 32, 256)
    return {"hidden_layer_sizes": [size] * n,
            "learning_rate_init": trial.suggest_float("learning_rate_init", 1e-4, 1e-2, log=True),
            "alpha": trial.suggest_float("alpha", 1e-5, 1e-2, log=True)}

def _suggest_svm_linear(trial) -> dict:
    return {"C": trial.suggest_float("C", 1e-3, 10.0, log=True)}

def _suggest_svm_rbf(trial) -> dict:
    return {"C": trial.suggest_float("C", 1e-2, 100.0, log=True),
            "gamma": trial.suggest_float("gamma", 1e-4, 1.0, log=True)}

def _suggest_svm_sigmoid(trial) -> dict:
    return {"C": trial.suggest_float("C", 1e-3, 10.0, log=True),
            "gamma": trial.suggest_float("gamma", 1e-4, 1.0, log=True)}

def _suggest_svm_poly(trial) -> dict:
    return {"C": trial.suggest_float("C", 1e-3, 10.0, log=True),
            "degree": trial.suggest_int("degree", 2, 5)}

def _suggest_bagging_dt(trial) -> dict:
    return {"n_estimators": trial.suggest_int("n_estimators", 10, 100),
            "max_depth": trial.suggest_int("max_depth", 2, 15)}

def _suggest_bagging_lr(trial) -> dict:
    return {"n_estimators": trial.suggest_int("n_estimators", 10, 50),
            "C": trial.suggest_float("C", 1e-3, 10.0, log=True)}

def _suggest_bagging_knn(trial) -> dict:
    return {"n_estimators": trial.suggest_int("n_estimators", 10, 50),
            "n_neighbors": trial.suggest_int("n_neighbors", 3, 15)}

def _suggest_bagging_svm_linear(trial) -> dict:
    return {"n_estimators": trial.suggest_int("n_estimators", 5, 20),
            "C": trial.suggest_float("C", 1e-3, 10.0, log=True)}

def _suggest_bagging_svm_rbf(trial) -> dict:
    return {"n_estimators": trial.suggest_int("n_estimators", 5, 20),
            "C": trial.suggest_float("C", 1e-2, 100.0, log=True),
            "gamma": trial.suggest_float("gamma", 1e-4, 1.0, log=True)}

def _suggest_bagging_svm_sigmoid(trial) -> dict:
    return {"n_estimators": trial.suggest_int("n_estimators", 5, 20),
            "C": trial.suggest_float("C", 1e-3, 10.0, log=True),
            "gamma": trial.suggest_float("gamma", 1e-4, 1.0, log=True)}

def _suggest_bagging_svm_poly(trial) -> dict:
    return {"n_estimators": trial.suggest_int("n_estimators", 5, 20),
            "C": trial.suggest_float("C", 1e-3, 10.0, log=True),
            "degree": trial.suggest_int("degree", 2, 5)}


# ===========================================================================
# REGISTRY — single source of truth
#
# Speed:  F = fast (<1 min/fold)   M = medium (1-5 min)   S = slow (>5 min)
# To add a new model: write _build_X + _suggest_X above, then add entry here.
# ===========================================================================

REGISTRY: dict = {
    # --- Already trained ---
    "LR":               {"build": _build_lr,               "suggest": _suggest_lr,               "scale": True,  "speed": "F"},
    "RF":               {"build": _build_rf,               "suggest": _suggest_rf,               "scale": False, "speed": "F"},
    "XGB":              {"build": _build_xgb,              "suggest": _suggest_xgb,              "scale": False, "speed": "F"},
    "LGBM":             {"build": _build_lgbm,             "suggest": _suggest_lgbm,             "scale": False, "speed": "F"},
    "MLP":              {"build": _build_mlp,              "suggest": _suggest_mlp,              "scale": True,  "speed": "F"},

    # --- New: fast ---
    "KNN":              {"build": _build_knn,              "suggest": _suggest_knn,              "scale": True,  "speed": "F"},
    "DT":               {"build": _build_dt,               "suggest": _suggest_dt,               "scale": False, "speed": "F"},
    "ET":               {"build": _build_et,               "suggest": _suggest_et,               "scale": False, "speed": "F"},
    "HGB":              {"build": _build_hgb,              "suggest": _suggest_hgb,              "scale": False, "speed": "F"},
    "CatBoost":         {"build": _build_cb,               "suggest": _suggest_cb,               "scale": False, "speed": "F"},
    "Bagging_DT":       {"build": _build_bagging_dt,       "suggest": _suggest_bagging_dt,       "scale": False, "speed": "F"},
    "Bagging_LR":       {"build": _build_bagging_lr,       "suggest": _suggest_bagging_lr,       "scale": True,  "speed": "F"},

    # --- New: medium (1-5 min/fold) ---
    "GB":               {"build": _build_gb,               "suggest": _suggest_gb,               "scale": False, "speed": "M"},
    "SVM_linear":       {"build": _build_svm_linear,       "suggest": _suggest_svm_linear,       "scale": True,  "speed": "M"},
    "Bagging_KNN":      {"build": _build_bagging_knn,      "suggest": _suggest_bagging_knn,      "scale": True,  "speed": "M"},

    # --- New: slow (>5 min/fold) — do not run at Cowork ---
    "SVM_rbf":          {"build": _build_svm_rbf,          "suggest": _suggest_svm_rbf,          "scale": True,  "speed": "S"},
    "SVM_sigmoid":      {"build": _build_svm_sigmoid,      "suggest": _suggest_svm_sigmoid,      "scale": True,  "speed": "S"},
    "SVM_poly":         {"build": _build_svm_poly,         "suggest": _suggest_svm_poly,         "scale": True,  "speed": "S"},
    "Bagging_SVM_linear":  {"build": _build_bagging_svm_linear,  "suggest": _suggest_bagging_svm_linear,  "scale": True,  "speed": "S"},
    "Bagging_SVM_rbf":     {"build": _build_bagging_svm_rbf,     "suggest": _suggest_bagging_svm_rbf,     "scale": True,  "speed": "S"},
    "Bagging_SVM_sigmoid": {"build": _build_bagging_svm_sigmoid, "suggest": _suggest_bagging_svm_sigmoid, "scale": True,  "speed": "S"},
    "Bagging_SVM_poly":    {"build": _build_bagging_svm_poly,    "suggest": _suggest_bagging_svm_poly,    "scale": True,  "speed": "S"},
}

FAST_MODELS   = [k for k, v in REGISTRY.items() if v["speed"] == "F"]
MEDIUM_MODELS = [k for k, v in REGISTRY.items() if v["speed"] == "M"]
SLOW_MODELS   = [k for k, v in REGISTRY.items() if v["speed"] == "S"]
