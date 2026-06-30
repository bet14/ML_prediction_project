# Goal 3 Implementation Plan — GBP/USD ML Prediction

**Branch:** branch_lee  
**Source:** Session 2026-06-29 planning discussion  
**Status:** Planning complete — implementation not yet started

---

## Overview

Goal 3 covers two sequential sub-goals:

| Sub-goal | Scope | Primary output |
|---|---|---|
| **3A** | Build `data/processed/` — 3 ML-ready dataset variants | 3 CSV files |
| **3B** | Train + evaluate models across all 3 datasets | `model_comparison.csv`, trained `.joblib` files |

---

## Sub-goal 3A — Build `data/processed/`

### Pipeline

```
data/interim/
  ├── gdp_panel.csv
  ├── cpi_panel.csv
  ├── central_bank_rate_panel.csv   →  src/features/build_dataset.py  →  data/processed/
  ├── current_account_panel.csv
  ├── forex_panel.csv
  └── equity_panel.csv
```

### Code to write: 1 file

**`src/features/build_dataset.py`**

| Step | Action | Technical detail |
|---|---|---|
| 1 | Load 6 interim panels | `pd.read_csv(..., index_col=0, parse_dates=True)` |
| 2 | Merge on date index | `pd.concat([...], axis=1).sort_index()` |
| 3 | Drop 2014-01-01 | No trading data (New Year's Day) |
| 4 | Forward-fill macro NaN | `ffill()` on `_value` and `_days_since_update` columns |
| 5 | Drop redundant equity cols | FTSE350, FTSE_ALL_SHARE, FTSE250, DJI, NASDAQ_COMPOSITE (both `_ret` and `_volume_sqrt`) |
| 6 | Verify transforms | `log(CPI_yoy)` and `sqrt(rate)` already in interim — verify presence |
| 7 | Add synthetic feature | `rate_differential = USA_central_bank_rate_value − UK_central_bank_rate_value` |
| 8 | Add date encoding — tree models | `day` (int), `month` (int), `weekday` (int 0=Mon) |
| 9 | Add date encoding — linear/MLP | `day_sin`, `day_cos`, `month_sin`, `month_cos`, `weekday_sin`, `weekday_cos` |
| 10 | Add target | `Direction = 1 if GBP_USD_close(t+1) > GBP_USD_close(t)` via `shift(-1)` → drop last row |
| 11 | Save Dataset 1 | `data/processed/dataset_basic_daily.csv` |
| 12 | Build Dataset 2 | 90 lags per feature column → `data/processed/dataset_90day_lookback.csv` |
| 13 | Build Dataset 3 | 16 technical indicator families per instrument → `data/processed/dataset_technical.csv` |

### Why drop those equity columns (EDA evidence from notebook 03)

Pearson correlations from notebook 03 section 6 (`|r| ≥ 0.85` pairs):

| Pair | r | Decision |
|---|---|---|
| FTSE100_ret ↔ FTSE_ALL_SHARE_ret | 0.993 | Drop FTSE_ALL_SHARE |
| FTSE350_ret ↔ FTSE_ALL_SHARE_ret | 0.980 | Drop FTSE350 |
| FTSE100_ret ↔ FTSE350_ret | 0.974 | Drop FTSE350 |
| FTSE250_ret ↔ FTSE_ALL_SHARE_ret | 0.872 | Drop FTSE250 |
| NASDAQ_COMPOSITE_ret ↔ NASDAQ100_ret | 0.992 | Drop NASDAQ_COMPOSITE |
| SP500_ret ↔ DJI_ret | 0.954 | Drop DJI |

Keep: FTSE100, NASDAQ100, SP500, RUSSELL2000 (retain market breadth with minimal redundancy).

### Why use CPI YoY not level (EDA evidence from notebook 01)

- ADF test: `USA_cpi_value` and `UK_cpi_value` are I(1) — non-stationary (monotone upward trend 100→130 over 11 years)
- `USA_cpi_yoy` and `UK_cpi_yoy` pass ADF — stationary, mean-reverting around inflation cycle
- Level correlation: USA_cpi_value ↔ UK_cpi_value r=0.982 (near-duplicate after trend)
- YoY breaks spurious correlation — measures what markets actually react to (inflation surprise)

### Output files

| File | Est. columns | Rows | Notes |
|---|---|---|---|
| `data/processed/dataset_basic_daily.csv` | ~120–130 | ~2,868 | Daily features + target |
| `data/processed/dataset_90day_lookback.csv` | ~11,000+ | ~2,868 | Dataset 1 + 90 lags per feature |
| `data/processed/dataset_technical.csv` | ~2,000 | ~2,868 | Dataset 1 + 16 technical indicator families |

---

## Sub-goal 3B — Train + Evaluate

### Full pipeline

```
data/processed/dataset_basic_daily.csv   (or dataset 2 / 3)
        │
        ▼
  walk_forward_cv.py          ← time-series splits (expanding window)
        │
        ├──►  train.py         ← fit LR / RF / XGB / LGBM / MLP per fold
        │       │
        │       ├── bayesian_search.py  ← tune hyperparams before final fit
        │       └── models/trained/*.joblib
        │
        └──►  backtest.py + metrics.py  ← evaluate each fold
                │
                ▼
        reports/tables/model_comparison.csv
        reports/figures/equity_curve_*.png
```

### Walk-forward CV scheme

```
Fold 1: train [2014 → 2018]  test [2019]
Fold 2: train [2014 → 2019]  test [2020]
Fold 3: train [2014 → 2020]  test [2021]
Fold 4: train [2014 → 2021]  test [2022]
Fold 5: train [2014 → 2022]  test [2023]
Final:  train [2014 → 2023]  test [2024]   ← held-out final evaluation
```

Expanding window (not rolling) — more training data in later folds mirrors real deployment.

### Code to write: 5 files

**`src/evaluation/walk_forward_cv.py`**
- Returns list of `(X_train, y_train, X_test, y_test)` tuples
- Accepts `n_test_years` param (default 1)

**`src/evaluation/metrics.py`**
- Inputs: `y_true`, `y_pred`, `y_proba` (optional), `returns` (optional)
- Outputs: dict with accuracy, f1_macro, auc_roc, sharpe_proxy, max_drawdown
- Pure function, no side effects — easy to test in isolation

**`src/models/train.py`**
- Train 5 model types per (dataset, fold):
  - Logistic Regression (sklearn) — baseline linear
  - Random Forest (sklearn) — tree ensemble
  - XGBoost (xgboost) — gradient boost
  - LightGBM (lightgbm) — fast gradient boost (better with wide Dataset 3)
  - MLP (sklearn MLPClassifier) — neural net
- Scaling: RobustScaler for LR + MLP (high kurtosis from EDA); no scaling for RF/XGB/LGBM
- Saves: `models/trained/{model}_{dataset}_fold{n}.joblib`

**`src/models/bayesian_search.py`**
- Library: `optuna` or `scikit-optimize` BayesSearchCV
- Runs on fold 1–4 combined (inner CV), optimises per model type
- Saves: `models/search_results/{model}_{dataset}_best_params.json`

| Model | Parameters to tune |
|---|---|
| RF | `n_estimators`, `max_depth`, `min_samples_leaf` |
| XGB | `n_estimators`, `learning_rate`, `max_depth`, `subsample` |
| LGBM | `n_estimators`, `learning_rate`, `num_leaves` |
| MLP | `hidden_layer_sizes`, `learning_rate_init`, `alpha` |
| LR | `C`, `penalty` |

**`src/evaluation/backtest.py`**
- Strategy: Long GBP/USD when model predicts UP; flat otherwise
- Computes: cumulative return, Sharpe ratio, max drawdown
- Outputs: `reports/figures/equity_curve_{model}_{dataset}.png`

### Metrics computed per fold

| Metric | Description |
|---|---|
| Accuracy | % directional predictions correct |
| F1-score (macro) | Balances UP/DOWN performance |
| AUC-ROC | Probability ranking quality |
| Sharpe proxy | Annualised return / std of daily strategy returns |
| Max drawdown | Worst peak-to-trough in equity curve |

### Expected results (based on Guyard & Deriaz 2024 on EUR/USD)

| Model | Expected accuracy | Notes |
|---|---|---|
| LR | 51–53% | Near-random baseline |
| RF | 53–56% | Improves with Dataset 3 |
| XGB / LGBM | 54–57% | Best with Dataset 3 + Bayesian search |
| MLP | 52–55% | Sensitive to tuning |

> Achieving 54–57% accuracy consistently is a good result given market efficiency.  
> Sharpe proxy > 0.3 is a more important target than raw accuracy.

### Final output: `reports/tables/model_comparison.csv`

Columns: `dataset`, `model`, `fold`, `accuracy`, `f1_macro`, `auc_roc`, `sharpe_proxy`, `max_drawdown`

---

## Implementation order (dependency-aware)

```
Week 1 (no network needed — works at Cowork):
  ① src/features/build_dataset.py  →  dataset1_basic_daily.csv    ← START HERE
  ② src/evaluation/walk_forward_cv.py                              ← no data dependency
  ③ src/evaluation/metrics.py                                      ← pure function

Week 2:
  ④ src/models/train.py  (LR + RF first — verify end-to-end pipeline)
  ⑤ src/models/bayesian_search.py  (after identifying promising models)
  ⑥ src/evaluation/backtest.py  (after trained models exist)

Later (compute-heavy):
  ⑦ dataset2_90day_lookback.csv  (wide — may be slow)
  ⑧ dataset3_technical.csv + re-train  (widest — Bayesian feature selection essential)
```

---

## Open decisions (to resolve during implementation)

- [ ] Clip extreme outliers before or after split? (EUR/GBP kurtosis=109, GBP/CHF kurtosis=173 — clip ±5σ per EDA)
- [ ] RobustScaler fitted on train fold only (to avoid data leakage)
- [ ] Dataset 3 Bayesian feature selection: use RF importance threshold or Optuna?
- [ ] Whether to include `days_since_update` columns in lag stack for Dataset 2
