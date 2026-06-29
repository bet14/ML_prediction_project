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

## Reference Files

| Purpose | File |
|---|---|
| Full spec: data requirements, column list, transforms | `References/GBPUSD_ML_data_requirements_spec.md` |
| Fetch lessons learned, gotchas, Cowork workarounds | `References/CLAUDE.md` |
| Visual progress checklist | `checklist_en.html` (open in browser) |
| Data inventory dashboards | `reports/macro_data_status.html`, `reports/forex_data_status.html`, `reports/equity_data_status.html` |
| Data pipeline ERD | `eurusd_data_pipeline_erd.html` |
