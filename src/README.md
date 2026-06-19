# src/

Modular, importable code (not notebooks). Not scanned by `auto_push.py`.

- `data/` — data collection & loading scripts (calls Dukascopy/FRED/ONS/yfinance, run outside Cowork; or reads CSVs already present in `data/raw/`)
- `features/` — feature engineering, technical indicator computation, lookback window construction
- `models/` — model zoo (21 models), training, 3-stage Bayesian hyperparameter search, meta-estimator stacking
- `evaluation/` — 8-fold walk-forward cross-validation, metrics (directional accuracy), cumulative profit P(t), accuracy-vs-profit comparison
- `app/` — Streamlit interface (`streamlit_app.py` — not yet created, will be added in stage 5)
