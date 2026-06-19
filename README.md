# GBP/USD Direction Prediction Project (Machine Learning)

Full methodology: see `working_plan.html` (open in browser).
Progress and issue tracking: `checklist.html` (Vietnamese) / `checklist_en.html` (English).
Data spec: `References/GBPUSD_ML_data_requirements_spec.md`.

## Data collection window

**All raw data is collected for the period 2014-01-01 → 2024-12-31** (≈ 11 years of daily
history). This is the default `--start`/`--end` range hard-wired into the pipeline driver
(`run_fred_pipeline.py`, which calls every `fetch_*.py` then every `process_*.py` in turn):

```
python run_fred_pipeline.py --start 2014-01-01 --end 2024-12-31
```

(`src/features/build_macro_panel.py` is an older, unused consolidator — not called by
`run_fred_pipeline.py` or anything else; see the `src/features/` table below.)

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
│   ├── macro_data_status.html  # Live dashboard: raw/interim inventory, errors, alt-API research
│   ├── pipeline_run_log.jsonl  # One JSON line per run_fred_pipeline.py invocation
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

Each CSV is a release history with columns `date, realtime_start, value`.

| File | Block | Indicator | Frequency | Rows | Coverage | Status |
|---|---|---|---|---|---|---|
| `USA_gdp.csv` | USA | GDP | Quarterly | 459 | 2014-01-01 → 2026-01-01 | OK |
| `USA_cpi.csv` | USA | CPI (index level) | Monthly | 1012 | 2014-01-01 → 2026-05-01 | OK |
| `USA_central_bank_rate.csv` | USA | Fed Funds Rate | Daily | 12609 | 2014-01-01 → 2026-06-17 | OK |
| `USA_current_account.csv` | USA | Current Account Balance | Quarterly | 409 | 2014-01-01 → 2025-10-01 | OK |
| `UK_gdp.csv` | UK | GDP | Quarterly | 274 | 2014-01-01 → 2020-07-01 | STALE — underlying Eurostat source discontinued, not a re-fetch fix |
| `UK_cpi.csv` | UK | CPI (index level) | Monthly | 587 | 2014-04-01 → 2025-03-01 | STALE — ~15 months behind `USA_cpi.csv` |
| `UK_central_bank_rate.csv` | UK | Bank of England Bank Rate | Monthly | 499 | 2014-08-01 → 2026-05-01 | OK |
| `UK_current_account.csv` | UK | Current Account Balance | Quarterly | — | — | MISSING — no FRED ticker found |
| `USA_composite_pmi.csv` | USA | Composite PMI | — | — | — | MISSING — not on FRED |
| `UK_composite_pmi.csv` | UK | Composite PMI | — | — | — | MISSING — not on FRED |

Per the spec there should be **6 indicators × 2 blocks**. This is *not* a clean
USA-OK/UK-not-OK split — three of the four FRED-backed indicators work on both blocks:

- **Fully OK on both blocks:** GDP (USA), CPI (USA), central bank rate (USA *and* UK).
- **UK GDP — stale, not a re-fetch fix:** the FRED series (`CLVMNACSCAB1GQUK`) stops at
  2020-07-01 because its underlying Eurostat source was discontinued, not because the local
  copy is simply out of date.
- **UK CPI — stale:** about 15 months behind the USA file. ONS series `D7BT` (dataset
  `mm23`) is an unverified candidate replacement — see Section 5 of
  `reports/macro_data_status.html`.
- **UK current account — missing entirely:** no FRED ticker has been found. ONS series
  `HBOP` (dataset `pnbp`) is an unverified candidate; a WIP fetch script targeting it is at
  `src/data/fetch_current_account_uk_wip.py`.
- **Composite PMI — missing for BOTH USA and UK**, not a UK-only gap: not published on FRED
  for either block (the related ISM Manufacturing PMI series family was removed from FRED in
  June 2016 at ISM's own request). No free full-history API has been found for either
  country; a documentation stub is at `src/data/fetch_composite_pmi_wip.py`.
- CPI YoY is not in the table above because it is derived in the panel step, not stored as a
  separate raw file.

Row counts differ by release frequency (daily Fed rate ≈ 12.6k rows; quarterly GDP a few
hundred). For the live, auto-checked snapshot (file presence/size/row-count) open
`reports/macro_data_status.html` in a browser.

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
| `fetch_fred.py` | Generic single-series fetcher — **not called by `run_fred_pipeline.py`**; standalone manual-lookup tool |
| `fetch_gdp.py` | Fetch USA/UK GDP release history |
| `fetch_cpi.py` | Fetch USA/UK CPI release history |
| `fetch_central_bank_rate.py` | Fetch Fed Funds Rate / BoE Bank Rate |
| `fetch_current_account.py` | Fetch USA current-account balance (UK intentionally skipped — see docstring) |
| `fetch_current_account_uk_wip.py` | **WIP, unverified** — UK current account from the ONS API (series `HBOP`, dataset `pnbp`); run `--raw-dump` first |
| `fetch_composite_pmi_wip.py` | **WIP stub** — documents why Composite PMI has no free API for USA or UK; scaffolds a manual investing.com-export fallback |
| `__init__.py` | Package marker |

The two `*_wip.py` scripts are deliberately separate from the four working `fetch_*.py`
above: they are not wired into `run_fred_pipeline.py` and must be run by hand once their
source is confirmed working.

### `src/features/` — Panel build & transforms (pure pandas; runs in Cowork)

| File | Role |
|---|---|
| `build_macro_panel.py` | Older consolidator script — **not called by `run_fred_pipeline.py` or anything else**; the per-indicator `process_*.py` scripts below are what actually runs |
| `panel_common.py` | Shared panel helpers |
| `process_gdp.py` | Per-indicator processing → `data/interim/gdp_panel.csv` |
| `process_cpi.py` | → `cpi_panel.csv` (adds CPI YoY, log transform) |
| `process_central_bank_rate.py` | → `central_bank_rate_panel.csv` (sqrt transform) |
| `process_current_account.py` | → `current_account_panel.csv` (USA only for now — picks up a UK CSV automatically, no code change needed, once one exists) |
| `process_composite_pmi.py` | **WIP** — → `composite_pmi_panel.csv`; prints a message and exits without writing anything until a raw CSV exists for at least one block |
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

### `reports/`

| File | Role |
|---|---|
| `macro_data_status.html` | Live dashboard (open in browser) — raw/interim file inventory, current errors/warnings, and the alternative-API research notes (ONS candidates, Composite PMI investigation) |
| `pipeline_run_log.jsonl` | One JSON line appended per `run_fred_pipeline.py` invocation (timestamp, mode, per-script returncode/duration, overall success); created on first run, accumulates from then on |
| `figures/`, `tables/` | Generated charts and result tables (empty until model training runs) |

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
