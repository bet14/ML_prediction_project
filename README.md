# GBP/USD Direction Prediction Project (Machine Learning)

Full methodology: see `working_plan.html` (open in browser).
Progress and issue tracking: `checklist.html` (Vietnamese) / `checklist_en.html` (English).
Data spec: `References/GBPUSD_ML_data_requirements_spec.md`.

## Data collection window

**All raw data is collected for the period 2014-01-01 → 2024-12-31** (≈ 11 years of daily
history). This is the default `--start`/`--end` range hard-wired into the pipeline scripts
(`run_fred_pipeline.py`, `build_macro_panel.py`):

```
python run_fred_pipeline.py --start 2014-01-01 --end 2024-12-31
python build_macro_panel.py --start 2014-01-01 --end 2024-12-31
```

Notes on the window:

- The directional-prediction paper this project adapts (Guyard & Deriaz, 2024) used
  2013-04-30 → 2022-12-31. The 2014→2024 window here is wider and more recent, giving more
  training rows and covering Brexit, COVID, and the 2022–2023 rate-hike cycle.
- FRED's API returns every revision up to the call date, so some **raw** macro CSVs physically
  contain a few rows dated after 2024 (e.g. `USA_central_bank_rate.csv` runs to mid-2026,
  `UK_cpi.csv` to 2025). These tails come from re-pulling the series later; the modelling
  window is still 2014→2024 and the panel-build step trims to `--end`.
- Daily series (e.g. Fed Funds Rate) have one row per calendar day; quarterly/monthly series
  (GDP, CPI, current account) have one row per release, so their file row-counts are much
  smaller. `realtime_start` records the **actual publication date** of each value — used later
  to forward-fill without look-ahead bias.

## Directory structure & file inventory

```
ML_prediction_project/
├── data/
│   ├── raw/            # Raw data, downloaded as-is, never edited by hand
│   │   ├── forex/      # GBP/USD OHLCV + correlated FX pairs (Dukascopy) — see "forex/" below
│   │   ├── macro/      # UK/US macro indicators (FRED, ONS) — see "macro/" below
│   │   └── equity/     # Equity indices (yfinance) — see "equity/" below
│   ├── interim/        # Per-indicator macro panels, merged by date, pre-feature-engineering
│   └── processed/      # Final 3 dataset variants for training (Basic, 90-Day Lookback, Technical)
├── notebooks/          # Exploratory notebooks, EDA (number them: 01_eda.ipynb, 02_...)
├── src/                # Modular, importable code — not notebooks
│   ├── data/           # FRED fetch scripts (one per indicator) + shared helpers
│   ├── features/       # Macro-panel build + per-indicator processing/transforms
│   ├── models/         # Training, Bayesian hyperparameter search, meta-stacking (to be built)
│   ├── evaluation/     # Metrics, walk-forward CV, backtest, cumulative profit (to be built)
│   └── app/            # Streamlit interface (to be built)
├── models/
│   ├── trained/        # Trained models, saved as .joblib/.pkl
│   └── search_results/ # Bayesian search logs/results per fold
├── reports/
│   ├── figures/        # Figures (feature importance, backtest charts, ...)
│   └── tables/         # Tables (model_comparison.csv, ...)
├── configs/            # .env.example, config — no real secrets committed
├── Key/                # fred_key.txt (FRED API key, gitignored)
├── References/         # Papers (PDFs), data spec, CLAUDE.md
└── working_plan.html, checklist.html, checklist_en.html, index.html, requirements.txt
```

### `data/raw/forex/` — Forex OHLCV (Dukascopy)

Currently a placeholder (`.gitkeep` only) — populate on a personal machine. Per the data spec
(section 2.3), **13 pairs**, each as one CSV with open/close/low/high/volume columns, daily,
2014→2024:

```
AUD/USD, EUR/USD, EUR/GBP, GBP/AUD, GBP/CAD, GBP/CHF, GBP/JPY,
GBP/NZD, GBP/USD, NZD/USD, USD/CAD, USD/CHF, USD/JPY
```

GBP/USD is both a feature source and the **target** (next-day close direction). Every pair
that touches GBP or USD is included because they share macro drivers and are correlated.

### `data/raw/macro/` — Macro indicators (FRED / ONS)

Each CSV is a release history with columns `date, realtime_start, value`. Present files:

| File | Block | Indicator | Frequency | Rows | Coverage |
|---|---|---|---|---|---|
| `USA_gdp.csv` | USA | GDP | Quarterly | 459 | 2014-01-01 → 2026-01-01 |
| `USA_cpi.csv` | USA | CPI (index level) | Monthly | 1012 | 2014-01-01 → 2026-05-01 |
| `USA_central_bank_rate.csv` | USA | Fed Funds Rate | Daily | 12609 | 2014-01-01 → 2026-06-17 |
| `USA_current_account.csv` | USA | Current Account Balance | Quarterly | 409 | 2014-01-01 → 2025-10-01 |
| `UK_gdp.csv` | UK | GDP | Quarterly | 274 | 2014-01-01 → 2020-07-01 |
| `UK_cpi.csv` | UK | CPI (index level) | Monthly | 587 | 2014-04-01 → 2025-03-01 |
| `UK_central_bank_rate.csv` | UK | Bank of England Bank Rate | Monthly | 499 | 2014-08-01 → 2026-05-01 |

Per the spec there should be **6 indicators × 2 blocks**. Status vs. the target set:

- **Present (FRED-fetchable):** GDP, CPI, central bank rate, current account.
- **Missing — USA current account** has no UK counterpart file yet; **CPI YoY** is derived
  later in the panel step (not a separate raw file); **Composite PMI** is intentionally NOT
  here — it is not published on FRED and must be pulled manually from investing.com
  (see `src/data/fred_common.py`).

Row counts differ by release frequency (daily Fed rate ≈ 12.6k rows; quarterly GDP a few
hundred). UK GDP currently stops at 2020-07-01 — re-fetch to extend it.

### `data/raw/equity/` — Equity indices (yfinance)

Currently a placeholder (`.gitkeep` only). Per the data spec (section 2.2), **9 indices**,
each OHLCV daily, 2014→2024:

```
US:  DJI, NASDAQ Composite, NASDAQ100, RUSSELL2000, S&P500
UK:  FTSE100, FTSE250, FTSE350, FTSE All-Share
```

### `data/interim/` — Merged macro panels

Business-day-indexed panels (one row per calendar day, 2014→…, ~3,254 rows each), forward-filled
with a companion `days_since_update` column and the spec's transforms applied. Files:

| File | Columns include |
|---|---|
| `central_bank_rate_panel.csv` | USA/UK rate value + days_since_update + `*_value_sqrt` (sqrt transform) |
| `cpi_panel.csv` | USA/UK CPI level + days_since_update, derived `*_cpi_yoy`, `UK_cpi_yoy_log` (log transform) |
| `current_account_panel.csv` | USA current-account value + days_since_update |
| `gdp_panel.csv` | USA/UK GDP value + days_since_update |

These are intermediate (debugging the pipeline), not the final training matrix.

### `data/processed/` — Final training datasets

Placeholder (`.gitkeep`). Three variants to be built (spec section 3):

- **Dataset 1 — Basic Daily:** macro panel + index/forex OHLCV, date encoding.
- **Dataset 2 — 90-Day Lookback:** Dataset 1 + each feature lagged over the previous 90 days.
- **Dataset 3 — Technical Indicators:** Dataset 1 + the 16 indicator families (SMA, WMA, RSI,
  MACD, Stochastic K/D, Momentum, CCI, ROC, Williams %R, A/D, Disparity, OSCP) computed per
  instrument — ~2,000 columns, trimmed via Bayesian feature selection.

### `src/data/` — FRED fetch scripts (need network; run outside Cowork)

| File | Role |
|---|---|
| `fred_common.py` | Shared FRED client + paths; the only `fredapi`-touching logic |
| `fetch_fred.py` | Generic single-series fetcher |
| `fetch_gdp.py` | Fetch USA/UK GDP release history |
| `fetch_cpi.py` | Fetch USA/UK CPI release history |
| `fetch_central_bank_rate.py` | Fetch Fed Funds Rate / BoE Bank Rate |
| `fetch_current_account.py` | Fetch current-account balance |
| `__init__.py` | Package marker |

### `src/features/` — Panel build & transforms (pure pandas; runs in Cowork)

| File | Role |
|---|---|
| `build_macro_panel.py` | Turn raw release histories into the forward-filled, transform-applied macro panel (no look-ahead: uses `realtime_start`) |
| `panel_common.py` | Shared panel helpers |
| `process_gdp.py` | Per-indicator processing → `data/interim/gdp_panel.csv` |
| `process_cpi.py` | → `cpi_panel.csv` (adds CPI YoY, log transform) |
| `process_central_bank_rate.py` | → `central_bank_rate_panel.csv` (sqrt transform) |
| `process_current_account.py` | → `current_account_panel.csv` |
| `__init__.py` | Package marker |

`src/models/`, `src/evaluation/`, `src/app/` are scaffolded (empty `__init__.py`/`.gitkeep`) and
to be built.

### Project root scripts & files

| File | Role |
|---|---|
| `run_fred_pipeline.py` / `run_fred_pipeline.bat` | Run all `fetch_*` then `process_*` in order (`--verify-only`, `--skip-fetch` flags) |
| `auto_push.py` / `push.bat` | git add/commit/push + rebuild `index.html` gallery (personal machine; needs SSH key) |
| `index.html` | Auto-generated deliverables gallery |
| `eurusd_data_pipeline_erd.html` | ERD of the data pipeline |
| `requirements.txt` | Python deps for `src/` |

### `References/`

Eleven research PDFs (`01_…`–`11_…`, FX/AML/ML topics), `GBPUSD_ML_data_requirements_spec.md`
(the full data spec), `eurusd-forex-prediction.html`, and `CLAUDE.md`.

### `configs/` & `Key/`

`configs/.env.example` (copy to `.env`; holds `FRED_API_KEY`, optional `ONS_API_KEY`),
`configs/README.md`. `Key/fred_key.txt` holds the FRED API key (gitignored).

## Important note (execution environment)

The Cowork sandbox has no outbound network access — it cannot call Dukascopy/FRED/ONS/yfinance,
and cannot `pip install` new packages (verified; see the issue log in the checklist). As a result:

- Data collection (`src/data/`) must run outside Cowork: a personal machine, Google Colab, or
  Kaggle. Save the results as CSV and copy them into `data/raw/`.
- Cowork can read/process/train on data already present in `data/` using pandas/sklearn — no
  network needed. In particular `build_macro_panel.py` and the `process_*` scripts run fine in
  Cowork once the raw CSVs exist.
- `auto_push.py`/`push.bat` (git add/commit/push) also run on a personal machine since they
  require a personal SSH key, not available in the sandbox.

## Note on `auto_push.py`

The script only scans files directly inside `References/`, `data/`, `notebooks/`, `models/`,
`reports/` (non-recursive) to build `index.html`. Files inside `data/raw/forex/`,
`models/trained/`, etc. will not automatically appear on the gallery page — this is a known
limitation, not a bug. `src/` and `configs/` are not scanned since they hold code/configuration,
not deliverables.

## requirements.txt

Lists the packages needed for `src/`. Install and run on a personal machine/Colab, not inside the
Cowork sandbox (network is blocked there).
