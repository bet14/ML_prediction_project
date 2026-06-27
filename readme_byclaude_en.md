# GBP/USD Direction Prediction Project (Machine Learning)

A machine-learning project that predicts the next-day direction (up/down) of GBP/USD using
ensemble models (XGBoost, LightGBM, CatBoost + meta-stacking). Features include UK/US macro
indicators (GDP, CPI, interest rates, current account, PMI), 13 correlated FX pairs, and
technical indicators. Adapted from Guyard & Deriaz (2024) with a wider, more recent time window.

Full methodology: `working_plan.html` (open in browser).
Progress and issue tracking: `checklist.html` (Vietnamese) / `checklist_en.html` (English).
Data spec: `References/GBPUSD_ML_data_requirements_spec.md`.

---

## Quick Start

**Requirements:** Python ≥ 3.9 (the codebase uses `list[dict]` type hints), packages in `requirements.txt`.

```bash
# Install on a personal machine — do NOT run inside the Cowork sandbox (no internet there)
pip install -r requirements.txt

# Run the full macro pipeline (needs internet for FRED API)
python run_fred_pipeline.py --start 2014-01-01 --end 2024-12-31

# Re-run processing only (no network needed, raw CSVs already exist)
python run_fred_pipeline.py --skip-fetch --start 2014-01-01 --end 2024-12-31

# Sanity-check all series IDs without fetching or processing
python run_fred_pipeline.py --verify-only
```

Once raw CSVs exist, run the WIP scripts for forex and equity on a personal machine:
```bash
run_forex_wip.bat --pair GBPUSD --source yfinance
run_equity_wip.bat --index FTAS --append
```

---

## Data collection window

**All raw data is collected for the period 2014-01-01 → 2024-12-31** (≈ 11 years of daily history).

> **Note on `--end`:** `--start` defaults to `2014-01-01` (hard-wired). `--end` defaults to
> `None` — if not passed, the pipeline fetches up to the current date. Always pass
> `--end 2024-12-31` explicitly to pin the modelling window:

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

---

## Project Status (as of 2026-06-26)

| Layer | Status |
|---|---|
| Macro raw data (FRED) | Mostly OK — see macro table below |
| Macro panels (`data/interim/`) | 4/5 panels built (missing `composite_pmi_panel`) |
| Forex raw data | 13 header-only placeholder CSVs — not yet fetched |
| Equity raw data | 9 header-only placeholder CSVs — not yet fetched |
| Final training datasets (`data/processed/`) | Not yet built |
| Model training | Not started |
| Streamlit app | Not started |

---

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
│   ├── forex_data_status.html  # Same, for data/raw/forex/ (Dukascopy vs yfinance decision)
│   ├── equity_data_status.html # Same, for data/raw/equity/ (yfinance ticker confidence)
│   ├── pipeline_run_log.jsonl  # One JSON line per fetch run (macro/forex/equity)
│   ├── figures/        # Figures (feature importance, backtest charts, ...)
│   └── tables/         # Tables (model_comparison.csv, ...)
├── configs/            # .env.example, config — no real secrets committed
├── Key/                # fred_key.txt (FRED API key, gitignored)
├── References/         # Papers (PDFs), data spec, CLAUDE.md
├── run_fred_pipeline.py    # Main macro pipeline driver
├── run_fred_pipeline.bat   # Batch wrapper
├── run_equity_wip.bat      # Wrapper for fetch_equity_wip.py
├── run_forex_wip.bat       # Wrapper for fetch_forex_wip.py
├── auto_push.py            # git add/commit/push + rebuild index.html gallery
├── push.bat                # Batch wrapper for auto_push.py
├── eurusd_data_pipeline_erd.html  # ERD diagram of the data pipeline
├── working_plan.html
├── checklist.html / checklist_en.html
├── index.html          # Auto-generated deliverables gallery
└── requirements.txt
```

### `data/raw/forex/` — Forex OHLCV (Dukascopy or yfinance, see below)

**13 header-only placeholder CSVs** (`AUD_USD.csv`, `EUR_USD.csv`, `EUR_GBP.csv`,
`GBP_AUD.csv`, `GBP_CAD.csv`, `GBP_CHF.csv`, `GBP_JPY.csv`, `GBP_NZD.csv`, `GBP_USD.csv`,
`NZD_USD.csv`, `USD_CAD.csv`, `USD_CHF.csv`, `USD_JPY.csv` — columns `date, open, high, low,
close, volume`) were created 2026-06-19. No row has been fetched yet — populate on a personal
machine with `src/data/fetch_forex_wip.py`. A `.gitkeep` file remains alongside the CSVs
(keeps the directory tracked if all CSVs are later gitignored).

GBP/USD is both a feature source and the **target** (next-day close direction). Every pair
that touches GBP or USD is included because they share macro drivers and are correlated.

The spec (section 7) recommends Dukascopy, but it is tick-level data (one compressed file
per pair *per hour* — a full 13-pair/11-year backfill is on the order of 800k–900k requests)
and would need to be aggregated to daily client-side; yfinance's `=X` tickers are much
lighter but FX volume on Yahoo is widely reported unreliable/zero. `fetch_forex_wip.py`
implements **both** behind `--source dukascopy|yfinance` — see the script's docstring and
`reports/forex_data_status.html` for the full trade-off. Neither path has been run
end-to-end yet.

### `data/raw/macro/` — Macro indicators (FRED / ONS)

Each CSV is a release history with columns `date, realtime_start, value`.

| File | Block | Indicator | Frequency | Rows | Coverage | Status |
|---|---|---|---|---|---|---|
| `USA_gdp.csv` | USA | GDP | Quarterly | 459 | 2014-01-01 → 2026-01-01 | OK |
| `USA_cpi.csv` | USA | CPI (index level) | Monthly | 1012 | 2014-01-01 → 2026-05-01 | OK |
| `USA_central_bank_rate.csv` | USA | Fed Funds Rate | Daily | 12609 | 2014-01-01 → 2026-06-17 | OK |
| `USA_current_account.csv` | USA | Current Account Balance | Quarterly | 409 | 2014-01-01 → 2025-10-01 | OK |
| `UK_gdp.csv` | UK | GDP | Quarterly | 274 | 2014-01-01 → 2020-07-01 | STALE — Eurostat source discontinued |
| `UK_cpi.csv` | UK | CPI (index level) | Monthly | 587 | 2014-04-01 → 2025-03-01 | STALE — ~15 months behind USA |
| `UK_central_bank_rate.csv` | UK | BoE Bank Rate | Monthly | 499 | 2014-08-01 → 2026-05-01 | OK |
| `UK_current_account.csv` | UK | Current Account Balance | Quarterly | — | — | MISSING — ONS script verified, not yet run |
| `USA_composite_pmi.csv` | USA | Composite PMI | — | — | — | MISSING — not on FRED |
| `UK_composite_pmi.csv` | UK | Composite PMI | — | — | — | MISSING — not on FRED |

Key gaps:

- **UK GDP — stale, unfixable via re-fetch:** FRED series `CLVMNACSCAB1GQUK` stops at 2020-07-01
  because its Eurostat source was discontinued.
- **UK CPI — stale:** ~15 months behind. ONS v0 API is retired; replacement uses ONS v1 beta.
  `fetch_cpi_uk_alt_wip.py` writes to `UK_cpi_ons_alt.csv` (separate from `UK_cpi.csv`) — see
  that script's docstring before swapping it in.
- **UK current account — not on FRED:** ONS series `HBOP` (dataset `pnbp`) is the replacement;
  schema verified 2026-06-19, not yet run.
- **Composite PMI — missing for both USA and UK:** Removed from FRED in June 2016. The
  investing.com scraper in `fetch_composite_pmi_wip.py` only retains ~3–4 recent releases —
  it is an incremental updater, not a backfill tool. See that script's docstring for the
  manual-fallback workflow needed to establish 2014–2024 history.

For the live file-inventory snapshot, open `reports/macro_data_status.html` in a browser.

### `data/raw/equity/` — Equity indices (yfinance)

**9 header-only placeholder CSVs** created 2026-06-19 (columns `date, open, high, low, close, volume`).
Not yet fetched — run `src/data/fetch_equity_wip.py` on a personal machine. A `.gitkeep` remains
alongside the CSVs. Per the data spec (section 2.2):

```
US:  USA_DJI.csv (^DJI), USA_NASDAQ_COMPOSITE.csv (^IXIC), USA_NASDAQ100.csv (^NDX),
     USA_RUSSELL2000.csv (^RUT), USA_SP500.csv (^GSPC)
UK:  UK_FTSE100.csv (^FTSE), UK_FTSE250.csv (^FTMC), UK_FTSE350.csv (^FTLC),
     UK_FTSE_ALL_SHARE.csv (^FTAS)
```

`^FTAS` (FTSE All-Share) has the lowest confidence — spot-check it first. See
`reports/equity_data_status.html` for the full per-ticker confidence table.

### `data/interim/` — Merged macro panels

Business-day-indexed panels (one row per calendar day, 2014→…, ~3,254 rows each):

| File | Columns include |
|---|---|
| `central_bank_rate_panel.csv` | USA/UK rate + days_since_update + `*_value_sqrt` |
| `cpi_panel.csv` | USA/UK CPI level + days_since_update + `*_cpi_yoy` + `UK_cpi_yoy_log` |
| `current_account_panel.csv` | USA current-account value + days_since_update |
| `gdp_panel.csv` | USA/UK GDP value + days_since_update |

`composite_pmi_panel.csv` will be added once a raw CSV exists for at least one block.
These are intermediate debugging outputs, not the final training matrix.

### `data/processed/` — Final training datasets

Placeholder (`.gitkeep`). Three variants to be built (spec section 3):

- **Dataset 1 — Basic Daily:** macro panel + index/forex OHLCV, date encoding.
- **Dataset 2 — 90-Day Lookback:** Dataset 1 + each feature lagged over the previous 90 days.
- **Dataset 3 — Technical Indicators:** Dataset 1 + 16 indicator families (~2,000 columns,
  trimmed via Bayesian feature selection).

### `src/data/` — Fetch scripts (need network; run outside Cowork)

| File | Role |
|---|---|
| `fred_common.py` | Shared FRED client + paths |
| `fetch_fred.py` | Generic single-series fetcher — standalone tool, not called by the pipeline |
| `fetch_gdp.py` | Fetch USA/UK GDP release history |
| `fetch_cpi.py` | Fetch USA/UK CPI release history |
| `fetch_central_bank_rate.py` | Fetch Fed Funds Rate / BoE Bank Rate |
| `fetch_current_account.py` | Fetch USA current-account (UK intentionally skipped — see docstring) |
| `fetch_current_account_uk_wip.py` | **WIP** — UK current account via ONS v1 beta API; schema verified 2026-06-19 |
| `fetch_cpi_uk_alt_wip.py` | **WIP** — alternative UK CPI via ONS v1 beta API; writes `UK_cpi_ons_alt.csv` |
| `fetch_composite_pmi_wip.py` | **WIP** — investing.com scraper; incremental updater only, cannot backfill |
| `fetch_forex_wip.py` | **WIP** — 13 forex pairs, `--source dukascopy|yfinance`; not yet run |
| `fetch_equity_wip.py` | **WIP** — 9 equity indices via yfinance; not yet run |
| `pipeline_log_common.py` | Shared logging helpers (`append_run_log`, `run_script`) used by all three pipeline scripts |
| `__init__.py` | Package marker |

### `src/features/` — Panel build & transforms (pure pandas; runs in Cowork)

| File | Role |
|---|---|
| `build_macro_panel.py` | **Unused** — older consolidator, not called by any pipeline |
| `panel_common.py` | Shared panel helpers |
| `process_gdp.py` | → `data/interim/gdp_panel.csv` |
| `process_cpi.py` | → `cpi_panel.csv` (adds CPI YoY, log transform) |
| `process_central_bank_rate.py` | → `central_bank_rate_panel.csv` (sqrt transform) |
| `process_current_account.py` | → `current_account_panel.csv` (USA only until UK CSV exists) |
| `process_composite_pmi.py` | **WIP** — exits without writing until a raw CSV exists |
| `__init__.py` | Package marker |

`src/models/` and `src/evaluation/` are scaffolded (empty `__init__.py`) and to be built.
`src/app/` has a `.gitkeep` only (no `__init__.py` yet).

### Project root scripts & files

| File | Role |
|---|---|
| `run_fred_pipeline.py` / `run_fred_pipeline.bat` | Macro pipeline driver. `--start` defaults to `2014-01-01`; `--end` defaults to `None` (fetches to today) — always pass `--end` explicitly |
| `auto_push.py` / `push.bat` | git add/commit/push + rebuild `index.html` (personal machine only) |
| `index.html` | Auto-generated deliverables gallery |
| `eurusd_data_pipeline_erd.html` | ERD diagram of the data pipeline |
| `requirements.txt` | Python deps (Python ≥ 3.9 required) |
| `run_equity_wip.bat` | Wrapper for `fetch_equity_wip.py`; passes all args through |
| `run_forex_wip.bat` | Wrapper for `fetch_forex_wip.py`; passes all args through |

### `reports/`

| File | Role |
|---|---|
| `macro_data_status.html` | Live dashboard — raw/interim inventory, errors, ONS/PMI research notes |
| `forex_data_status.html` | 13-pair placeholder inventory + Dukascopy-vs-yfinance trade-off |
| `equity_data_status.html` | 9-index placeholder inventory + per-ticker confidence |
| `pipeline_run_log.jsonl` | Append-only run log; created on first pipeline run |
| `README.md` | Short description of the reports folder |
| `figures/`, `tables/` | Empty until model training runs |

### `References/`

Eleven research PDFs (`01_…`–`11_…`), `GBPUSD_ML_data_requirements_spec.md`, `eurusd-forex-prediction.html`, and `CLAUDE.md`.

### `configs/` & `Key/`

`configs/.env.example` (copy to `.env`; holds `FRED_API_KEY`, optional `ONS_API_KEY`).
`Key/fred_key.txt` holds the FRED API key (gitignored).

---

## Important note (execution environment)

The Cowork sandbox has no outbound network — it cannot call FRED/ONS/Dukascopy/yfinance and
cannot `pip install` new packages. As a result:

- **Data collection** (`src/data/`) must run on a personal machine, Colab, or Kaggle. Copy
  results as CSVs into `data/raw/`.
- **Processing and training** (`src/features/`, `src/models/`) run fine in Cowork once raw
  CSVs exist — no network needed.
- **`auto_push.py`/`push.bat`** require a personal SSH key; run on a personal machine only.

---

## Note on `auto_push.py`

Scans files directly inside `References/`, `data/`, `notebooks/`, `models/`, `reports/`
(non-recursive) to build `index.html`. Files inside subdirectories like `data/raw/forex/` or
`models/trained/` will not appear in the gallery — known limitation, not a bug.

---

## requirements.txt

**Python ≥ 3.9 required.** Install on a personal machine/Colab only.

> The `yfinance` comment in `requirements.txt` mentions "DAX, VIX" — these are **not** in
> the current data plan. Only the 9 indices listed in `data/raw/equity/` are in scope.
> That comment is outdated.

---

## Corrections vs. original README

| # | Original README | Correction |
|---|---|---|
| 1 | Directory tree missing `run_fred_pipeline.py/.bat`, `auto_push.py`, `push.bat`, `eurusd_data_pipeline_erd.html` | All added to tree |
| 2 | Forex/equity CSVs described as "replacing" the `.gitkeep` | `.gitkeep` still present alongside CSVs — intentional |
| 3 | `src/app/` described as having `__init__.py` + `.gitkeep` | `src/app/` has `.gitkeep` only; no `__init__.py` yet |
| 4 | `--end` described as "hard-wired" | Only `--start` is hard-wired; `--end` defaults to `None` |
| 5 | `reports/README.md` not listed in reports table | Added |
| 6 | No project description, no Quick Start, no status summary | All three added |
| 7 | Python version not mentioned | Added: requires Python ≥ 3.9 |
| 8 | `requirements.txt` comment mentions DAX/VIX (not in data plan) | Flagged as outdated |
