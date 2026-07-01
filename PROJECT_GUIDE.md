# Project Guide: GBP/USD Direction Prediction

> **Read this file first** at the start of every new session.
> Then read `SESSION_LOG.md` to see where work left off.

---

## Goals

### Course Goals (4 required)

| # | Goal |
|---|---|
| 1 | **Data collection** from multiple sources (API, scraping, open data) |
| 2 | **Data analysis**, define the prediction target |
| 3 | **Build model**, training/prediction pipeline, select metrics |
| 4 | **Build interface** (Streamlit) and integrate the model into UX |

### Specific ML Objective

Predict the next-day direction of GBP/USD (up / not up) using Machine Learning.
Adapted from Guyard & Deriaz (2024) on EUR/USD. European Area → UK.

```
Direction(t) = 1  if close(t+1) > close(t)
Direction(t) = 0  if close(t+1) <= close(t)
```

**Data:** 2014-01-01 → 2024-12-31 (≈ 11 years, daily).

### Outstanding Work (priority order)

**Goal 1 — Data (finish up):**
- [ ] UK GDP: find replacement for discontinued FRED series (ONS direct)
- [ ] Composite PMI USA + UK: find historical source 2014–2024 (BLOCKED)
- [ ] Build `data/interim/forex_panel.csv` — need to create `src/features/process_forex.py`
- [ ] Build `data/interim/equity_panel.csv` — need to create `src/features/process_equity.py`
- [ ] Swap UK CPI to ONS alt source, rebuild `cpi_panel.csv`
- [ ] Integrate UK current account into `current_account_panel.csv`

**Goal 2 — EDA & Analysis (`notebooks/`):**
- [ ] `01_eda_macro.ipynb` — macro indicators analysis, missing values, stationarity
- [ ] `02_eda_forex_equity.ipynb` — OHLCV analysis, correlation, target distribution
- [ ] `03_feature_analysis.ipynb` — feature importance, multicollinearity
- [ ] Visualize target balance (class imbalance check)

**Goal 3 — Model pipeline (`src/models/`, `src/evaluation/`):**
- [ ] Build `data/processed/` — 3 dataset variants (Basic / 90-Day / Technical)
- [ ] `src/models/train.py` — training pipeline (LR, RF, XGB, LGBM, MLP)
- [ ] `src/models/bayesian_search.py` — hyperparameter optimization
- [ ] `src/evaluation/walk_forward_cv.py` — walk-forward cross-validation
- [ ] `src/evaluation/backtest.py` + `metrics.py` — accuracy, F1, AUC, Sharpe proxy
- [ ] `reports/tables/model_comparison.csv`

**Goal 4 — Streamlit interface (`src/app/`):**
- [ ] `src/app/app.py` — load trained model, input form, predict direction
- [ ] Visualize: feature importance, recent predictions vs actual, confidence

---

## Folder Structure

```
ML_prediction_project/
│
├── data/
│   ├── raw/
│   │   ├── macro/          # Macro indicators (FRED, ONS) — CSV: date, realtime_start, value
│   │   ├── forex/          # 13 FX pairs, OHLC daily — CSV: date, open, high, low, close (volume col present but = 0, excluded from model)
│   │   └── equity/         # 9 equity indices (yfinance) — CSV: date, open, high, low, close, volume
│   ├── interim/            # Intermediate panel CSVs: forward-filled to trading days
│   └── processed/          # (not yet) Final training datasets: Basic / 90-Day / Technical
│
├── src/
│   ├── data/               # Data fetch scripts (requires network) + shared helpers
│   ├── features/           # Process/transform raw → interim panel
│   ├── models/             # (scaffold) Training, Bayesian search, meta-stacking
│   ├── evaluation/         # (scaffold) Walk-forward CV, backtest, metrics
│   └── app/                # (scaffold) Streamlit interface
│
├── models/
│   ├── trained/            # Trained models (.joblib/.pkl)
│   └── search_results/     # Bayesian hyperparameter search results
│
├── reports/
│   ├── macro_data_status.html   # Dashboard: raw/interim macro, errors, alternative APIs
│   ├── forex_data_status.html   # Dashboard: 13 FX pairs, Dukascopy vs yfinance
│   ├── equity_data_status.html  # Dashboard: 9 indices, per-ticker confidence
│   ├── pipeline_run_log.jsonl   # Append-only: 1 JSON line per pipeline run
│   ├── figures/                 # Charts (feature importance, backtest)
│   └── tables/                  # model_comparison.csv, ...
│
├── notebooks/              # EDA (numbered: 01_eda.ipynb, 02_...)
├── References/
│   ├── *.pdf               # 11 research papers (FX/AML/ML)
│   ├── GBPUSD_ML_data_requirements_spec.md   # Full data spec
│   ├── CLAUDE.md           # Lessons learned, conventions (important!)
│   └── eurusd-forex-prediction.html
├── configs/                # .env.example (FRED_API_KEY, ONS_API_KEY)
├── Key/                    # fred_key.txt (gitignored — do not commit)
│
├── run_fred_pipeline.py    # Run the full macro pipeline (fetch + process)
├── run_fred_pipeline.bat   # Bat wrapper for run_fred_pipeline.py
├── run_equity_wip.bat      # Bat wrapper for fetch_equity_wip.py
├── run_forex_wip.bat       # Bat wrapper for fetch_forex_wip.py
├── auto_push.py / push.bat # Auto git add/commit/push + rebuild index.html
├── checklist.html          # Progress checklist (Vietnamese)
├── checklist_en.html       # Progress checklist (English)
└── requirements.txt        # Python deps (install on personal machine, not Cowork)
```

---

## Environment & Constraints

| Environment | Network? | What can be done? |
|---|---|---|
| **Cowork sandbox** | NO | Read code, process existing data, train models, edit scripts |
| **Personal machine** | YES | Fetch data (`src/data/`), `pip install`, `push.bat` |
| **Google Colab / Kaggle** | YES | Fetch data + train heavy models |

> When using Claude Code in Cowork: cannot run `fetch_*.py`, cannot `pip install`.
> Run on personal machine → copy CSVs into `data/raw/` → commit.

---

## Running the Main Pipelines

### Macro pipeline (FRED)
```bash
python run_fred_pipeline.py --start 2014-01-01 --end 2024-12-31
# Flags:
#   --verify-only  # check series IDs only, no fetch
#   --skip-fetch   # run process_*.py on existing raw CSVs only
```

### Equity pipeline (yfinance)
```bash
run_equity_wip.bat                    # fetch all 9 indices
run_equity_wip.bat --index FTAS       # fetch a single index
run_equity_wip.bat --append           # append to existing file
```

### Forex pipeline
```bash
run_forex_wip.bat --source yfinance                     # yfinance OHLC (volume col = 0, not used)
run_forex_wip.bat --pair GBPUSD --source yfinance --append
```

---

## Important Conventions

### File naming
- `fetch_*.py` — stable fetch scripts, called by `run_fred_pipeline.py`
- `fetch_*_wip.py` — Work In Progress: schema verified but **not yet run for real** or not yet integrated into the main pipeline
- `process_*.py` — process raw CSV → interim panel (can run in Cowork)

### Before using a `_wip.py` script
1. Read docstring → check STATUS on the first line
2. Run `--verify-only` or `--raw-dump` to inspect the raw response before parsing
3. Run for real → check output → if OK, decide whether to integrate into main pipeline

### `reports/pipeline_run_log.jsonl`
Each script run appends one JSON line: timestamp, `pipeline` ("macro"/"forex"/"equity"), mode, per-step result. This is the only persisted run history in the repo.

---

## 3 Final Datasets to Build (not yet)

Once `data/raw/` is complete, build `data/processed/`:

| Dataset | Description | Estimated columns |
|---|---|---|
| **Dataset 1 — Basic Daily** | macro panel + OHLCV index/forex + date encoding | ~130 |
| **Dataset 2 — 90-Day Lookback** | Dataset 1 + 90-day lags per feature | many |
| **Dataset 3 — Technical** | Dataset 1 + 16 groups of technical indicators per instrument | ~2000 (Bayesian feature selection) |

---

## Cross-Validation & Train/Test Strategy

### Why not a standard train/test split?

GBP/USD is a **time series**: observations are ordered chronologically and correlated across time. A random split (e.g., sklearn's `train_test_split`) would allow the model to see future dates during training and predict past dates during testing — a form of **data leakage** that inflates apparent accuracy.

### Walk-Forward Cross-Validation (Expanding Window)

This project uses **expanding-window walk-forward CV**, implemented in `src/evaluation/walk_forward_cv.py`.

```
Fold 1:  Train [2014–2018]  →  Test [2019]   (1 303 rows train / 261 test)
Fold 2:  Train [2014–2019]  →  Test [2020]
Fold 3:  Train [2014–2020]  →  Test [2021]
Fold 4:  Train [2014–2021]  →  Test [2022]
Fold 5:  Train [2014–2022]  →  Test [2023]
Final:   Train [2014–2023]  →  Test [2024]   ← held-out, never touched until final evaluation
```

**Rules enforced by design:**
- The training window always starts at 2014 and grows by one year at a time.
- The test window is always the **year immediately after** the last training year → no future data ever leaks into training.
- The **Final fold (2024)** is a true held-out set: it is not used for model selection or hyperparameter tuning.

### Where does the validation set fit in?

There is no static validation split. Validation is performed **inside the Bayesian hyperparameter search** (`src/models/bayesian_search.py`):

```
Folds 1–4  →  Inner CV: Optuna optimises mean F1-macro across these folds
Fold 5     →  Outer validation: best params are evaluated here
Final      →  Held-out test: final accuracy / F1 / AUC / Sharpe reported here
```

### Expanding window vs. sliding window — why expanding?

| | Expanding window | Sliding window |
|---|---|---|
| Train size | Grows with each fold | Fixed length |
| Uses all history | Yes | No (drops old data) |
| Best when | Long-term macro trends matter | Recent regime change dominates |
| Used here | **Yes** | No |

This project uses **expanding window** because macroeconomic indicators (GDP growth, CPI, interest rates) carry meaningful long-term structure. Discarding older data (sliding window) would waste signal and reduce stability. This choice follows Guyard & Deriaz (2024).

### Full timeline diagram

```
2014                                                        2023  2024
 |──── Fold 1–5: walk-forward CV (model selection & tuning) ────|─Final─|
                                                                    ↑
                                             held-out test set — evaluated last
```

---

## Glossary — Key Metrics and Concepts

### CV Accuracy (Cross-Validation Accuracy)
The average prediction accuracy measured across folds 1–5 of the walk-forward CV scheme.
Each fold trains on data up to year N and tests on year N+1 (2019 through 2023).
This metric is used to **compare and select models** — but because the model selection
process itself has seen these years indirectly, CV accuracy tends to be optimistic.
Do not use CV accuracy as the final reported result.

### Final 2024 Accuracy
Accuracy measured on the true held-out test set: the model is trained on 2014–2023 and
tested on 2024 for the very first time. This data was never used in training, fold selection,
or hyperparameter tuning. **This is the number to report as the project result.**

### AUC-ROC (Area Under the ROC Curve)
Measures how well the model separates UP days from DOWN days regardless of the
classification threshold. An AUC of 0.50 is equivalent to random guessing (coin flip).
An AUC of 1.00 means perfect separation.

For FX direction prediction, the literature typically reports AUC in the range 0.55–0.65.
Values above 0.80 are considered suspicious for financial time-series data and should be
investigated for data leakage or spurious linear correlations before being reported.

Reference thresholds:
  0.50   Random baseline
  0.55–0.65  Typical for FX direction prediction (literature)
  0.70+  Good — uncommon in this domain
  0.85+  Flagged — requires investigation

### F1-Macro
The average of F1-score computed separately for the UP class and the DOWN class.
Balances precision and recall for both directions. More robust than accuracy when one
class is slightly more frequent. In this project the dataset is near-balanced (49/51),
so accuracy and F1-macro track closely.

### Sharpe Proxy (Annualised)
Simulates a simple trading strategy: go long GBP/USD when the model predicts UP, stay
flat otherwise. The Sharpe proxy is the annualised return of that strategy divided by
its standard deviation (scaled by sqrt(252) for daily data).

  > 0   Strategy made money on average
  > 0.3  Decent result for a simple rule-based strategy
  < 0   Strategy lost money — accurate predictions did not translate to profit

A model can have high accuracy but negative Sharpe (it gets direction right but misses
the large moves). Sharpe is therefore a more realistic measure of practical usefulness.

### Max Drawdown
The worst peak-to-trough loss in the strategy's equity curve during the test period.
Always negative. A drawdown of −0.15 means the strategy lost 15% from its best point
before recovering. Measures downside risk, not average performance.

### Walk-Forward CV vs Standard Train/Test Split
Standard splits assign rows randomly to train and test sets. For a time series this
causes **data leakage**: the model sees future dates during training and past dates
during testing, inflating apparent performance. Walk-forward CV enforces chronological
order — the training window always ends before the test window begins.

---

## Glossary — Model Types

All model definitions live in `src/models/model_registry.py` (one `_build_X` function per model).

| Model | What it is | Strength / weakness |
|---|---|---|
| **LR** — Logistic Regression | Linear model: weighted sum of all features → sigmoid → probability | Fast, interpretable coefficients, but can only draw a *linear* decision boundary |
| **DT** — Decision Tree | A single tree of if/else splits, chosen to make each branch as "pure" as possible (Gini/entropy) | Very interpretable, but high variance — small changes in training data can produce a very different tree (prone to overfitting) |
| **RF** — Random Forest | Many DTs, each trained on a bootstrap sample **and** a random subset of features per split, majority vote | Reduces variance vs a single DT; the added feature-randomisation is what distinguishes it from Bagging_DT |
| **ET** — Extra Trees | Like RF, but split thresholds are chosen randomly instead of optimised | Even more randomness → sometimes less overfitting, faster to train |
| **Bagging_DT** | **Bagging = Bootstrap AGGregatING**: many independent DTs, each trained on a bootstrap sample (rows only, no feature randomisation) → majority vote | Conceptually the "manual" version of RF; benefits come purely from row resampling |
| **Bagging_LR** | Same bagging idea, base estimator is LR instead of DT | LR is already low-variance, so bagging improves it less than it improves DT — but still smooths out sensitivity to specific training rows |
| **KNN** — K-Nearest Neighbors | No training phase; classifies a point by majority vote of its k nearest neighbours in feature space | Sensitive to feature scaling (hence `scale=True`) and to having 110 features (curse of dimensionality) |
| **HGB / XGB / LGBM / CatBoost** — Gradient Boosting family | Trees built sequentially, each new tree corrects the errors of the previous ones | Usually the strongest performers; differ mainly in implementation speed and how they bin/handle features (CatBoost also handles categoricals natively) |
| **MLP** — Multi-Layer Perceptron | Small fully-connected neural network trained via backpropagation | Needs scaled inputs (`scale=True`); more parameters to tune, easy to overfit on ~2600 rows |
| **SVM** (linear/rbf/sigmoid/poly) | Maximum-margin classifier; the kernel shapes the decision boundary | Non-linear kernels are **slow** on this dataset size — flagged `SLOW` in the registry, do not run in Cowork |

---

## Streamlit App — User Guide (Goal 4)

**File:** `src/app/app.py` · **Purpose:** interactive demo — pick a model + fold, see how well it predicts GBP/USD direction, without retraining anything.

### How to run

```bash
# Personal machine only (needs network for first-time pip install)
pip install -r requirements.txt
streamlit run src/app/app.py
# Opens automatically at http://localhost:8501
```

### Important: the app does NOT compute anything new

`app.py` is a pure **view layer** — it only re-reads results that `train.py` and
`bayesian_search.py` already produced. This is why the demo loads instantly with no
training delay. Data sources for each part of the screen:

| What you see on screen | Where it actually comes from |
|---|---|
| Sidebar model list | Scans filenames in `models/trained/*.joblib` |
| Metric cards (accuracy/F1/AUC/Sharpe/drawdown) | One row read from `reports/tables/model_comparison.csv` (written by `train.py` after training) |
| "Predicted vs actual" chart + latest predictions table | Loads the already-fitted `Pipeline` (`.joblib`) for the chosen model+fold, rebuilds the exact same `X_test/y_test` via `get_folds()` (same walk-forward split used at training time — guarantees no leakage), then calls `pipe.predict()` / `predict_proba()` live in the browser |
| Feature importance chart | Only shown if the underlying sklearn model exposes `.feature_importances_` — true for tree-based models (DT, RF, ET, HGB, CatBoost, Bagging_DT), not for LR/KNN/MLP |
| Full comparison table + 4 PNG charts at the bottom | Static files: table from `model_comparison.csv`, PNGs pre-generated by `scripts/plot_model_comparison.py` |

### How to reuse this a year from now

1. Nothing in `app.py` needs editing to add a new model — train it with `train.py` (it
   auto-saves to `models/trained/`) and it appears in the sidebar dropdown on next refresh.
2. If you rebuild `model_comparison.csv` or the 4 PNG charts, just refresh the browser
   tab — Streamlit re-reads from disk (cached with `@st.cache_data` / `@st.cache_resource`,
   restart the app if you don't see updated numbers).
3. If a model/fold combination shows "No trained file", it simply means that
   `.joblib` was never trained — run `train.py --models <name> --fold <n>`.

---

## Reference Files

| Purpose | File |
|---|---|
| Full spec: data requirements, column list, transforms | `References/GBPUSD_ML_data_requirements_spec.md` |
| Fetch lessons learned, gotchas, Cowork workarounds | `References/CLAUDE.md` |
| Visual progress checklist | `checklist_en.html` (open in browser) |
| Data inventory dashboards | `reports/macro_data_status.html`, `reports/forex_data_status.html`, `reports/equity_data_status.html` |
| Data pipeline ERD | `eurusd_data_pipeline_erd.html` |
