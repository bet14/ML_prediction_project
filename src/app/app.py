"""
app.py -- Streamlit interface for GBP/USD direction prediction.

STATUS: production

Loads trained model pipelines from models/trained/ and lets the user:
  - pick a model + walk-forward fold
  - see that fold's metrics (accuracy, F1, AUC, Sharpe proxy, max drawdown)
  - see predicted vs actual direction over the test period
  - see feature importance (tree-based models only)
  - browse the full model comparison table + pre-generated comparison charts

Usage:
    streamlit run src/app/app.py
"""

import os
import sys

import joblib
import numpy as np
import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.evaluation.walk_forward_cv import get_folds
from src.models.model_registry import REGISTRY

ROOT_DIR = os.path.join(os.path.dirname(__file__), "..", "..")
PROCESSED_DIR = os.path.join(ROOT_DIR, "data", "processed")
TRAINED_DIR = os.path.join(ROOT_DIR, "models", "trained")
COMPARISON_CSV = os.path.join(ROOT_DIR, "reports", "tables", "model_comparison.csv")
FIGURES_DIR = os.path.join(ROOT_DIR, "reports", "figures")

DATASET_FILES = {
    "dataset_basic_daily": "dataset_basic_daily.csv",
}

FOLD_LABELS = ["1", "2", "3", "4", "5", "final"]


@st.cache_data
def load_dataset(dataset_name: str) -> pd.DataFrame:
    path = os.path.join(PROCESSED_DIR, DATASET_FILES[dataset_name])
    return pd.read_csv(path, index_col=0, parse_dates=True)


@st.cache_data
def load_comparison() -> pd.DataFrame:
    if not os.path.exists(COMPARISON_CSV):
        return pd.DataFrame()
    return pd.read_csv(COMPARISON_CSV)


@st.cache_resource
def load_pipeline(model_name: str, dataset_name: str, fold_label: str):
    path = os.path.join(TRAINED_DIR, f"{model_name}_{dataset_name}_fold{fold_label}.joblib")
    if not os.path.exists(path):
        return None
    return joblib.load(path)


def available_models(dataset_name: str) -> list:
    models = set()
    for fname in os.listdir(TRAINED_DIR):
        prefix = f"_{dataset_name}_fold"
        if prefix in fname and fname.endswith(".joblib"):
            models.add(fname.split(prefix)[0])
    return sorted(m for m in models if m in REGISTRY)


st.set_page_config(page_title="GBP/USD Direction Prediction", layout="wide")
st.title("GBP/USD Next-Day Direction Prediction")
st.caption("Walk-forward CV, 2014-2024 daily data. Adapted from Guyard & Deriaz (2024).")

dataset_name = "dataset_basic_daily"
df = load_dataset(dataset_name)
comparison = load_comparison()
models = available_models(dataset_name)

if not models:
    st.error(f"No trained models found in models/trained/ for {dataset_name}.")
    st.stop()

with st.sidebar:
    st.header("Model selection")
    model_name = st.selectbox("Model", models)
    fold_label = st.selectbox("Fold", FOLD_LABELS, index=len(FOLD_LABELS) - 1)
    st.caption("Fold 'final' = held-out 2024 test set (never used in training/tuning).")

pipe = load_pipeline(model_name, dataset_name, fold_label)
if pipe is None:
    st.warning(f"No trained file for {model_name} / fold {fold_label}. Train it first with train.py.")
    st.stop()

folds = get_folds(df)
fold_index = 5 if fold_label == "final" else int(fold_label) - 1
X_train, y_train, X_test, y_test = folds[fold_index]

st.subheader(f"{model_name} -- fold {fold_label}")

row = comparison[
    (comparison["model"] == model_name) & (comparison["fold"] == fold_label)
] if not comparison.empty else pd.DataFrame()

metric_cols = st.columns(5)
if not row.empty:
    r = row.iloc[0]
    metric_cols[0].metric("Accuracy", f"{r['accuracy']:.1%}")
    metric_cols[1].metric("F1-macro", f"{r['f1_macro']:.3f}")
    auc = r.get("auc_roc")
    metric_cols[2].metric("AUC-ROC", f"{auc:.3f}" if pd.notna(auc) else "N/A")
    sharpe = r.get("sharpe_proxy")
    metric_cols[3].metric("Sharpe proxy", f"{sharpe:.2f}" if pd.notna(sharpe) else "N/A")
    dd = r.get("max_drawdown")
    metric_cols[4].metric("Max drawdown", f"{dd:.1%}" if pd.notna(dd) else "N/A")
else:
    st.info("No row in model_comparison.csv for this model/fold yet.")

y_pred = pipe.predict(X_test)
try:
    y_proba = pipe.predict_proba(X_test)[:, 1]
except AttributeError:
    y_proba = None

pred_df = pd.DataFrame(
    {"actual": y_test.values, "predicted": y_pred},
    index=X_test.index,
)
if y_proba is not None:
    pred_df["p_up"] = y_proba
pred_df["correct"] = pred_df["actual"] == pred_df["predicted"]

st.markdown("#### Predicted vs actual direction (test period)")
st.line_chart(pred_df[["actual", "predicted"]])

st.markdown("#### Latest predictions")
st.dataframe(pred_df.tail(20).sort_index(ascending=False), use_container_width=True)

model_step = pipe.named_steps.get("model")
if hasattr(model_step, "feature_importances_"):
    st.markdown("#### Feature importance (top 15)")
    feature_cols = [c for c in df.columns if c != "Direction"]
    importances = pd.Series(model_step.feature_importances_, index=feature_cols)
    st.bar_chart(importances.sort_values(ascending=False).head(15))

st.markdown("---")
st.markdown("### All models -- comparison")
if not comparison.empty:
    st.dataframe(
        comparison.sort_values(["model", "fold"]).reset_index(drop=True),
        use_container_width=True,
    )
else:
    st.info("reports/tables/model_comparison.csv not found yet.")

st.markdown("### Comparison charts")
chart_files = [
    ("cv_vs_final_accuracy.png", "CV vs Final 2024 Accuracy"),
    ("auc_by_model.png", "AUC-ROC by model"),
    ("accuracy_per_fold.png", "Accuracy per fold"),
    ("sharpe_by_model.png", "Sharpe proxy by model"),
]
cols = st.columns(2)
for i, (fname, caption) in enumerate(chart_files):
    path = os.path.join(FIGURES_DIR, fname)
    if os.path.exists(path):
        cols[i % 2].image(path, caption=caption, use_container_width=True)
