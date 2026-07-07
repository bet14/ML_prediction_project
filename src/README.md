# src/

Modular, importable code (not notebooks). Not scanned by `auto_push.py`.

## `data/` — data collection (network-dependent; run outside Cowork)

Shared helpers:
- `fred_common.py` — shared fredapi logic (`load_fred`, `fetch_indicator_releases` with chunked ALFRED requests, `save_raw_csv`, `verify_series_id`) used by every per-indicator `fetch_*.py` below. Fetches full revision history (every observation × release-date pair), not just latest values — this is what lets the `process_*.py` step forward-fill by *release date* instead of *observation date* and avoid look-ahead bias.
- `pipeline_log_common.py` — shared `StepLogger` (timestamped console output) + `append_run_log()`/`run_script()`, writing one shared `reports/pipeline_run_log.jsonl` (one JSON line per script invocation, tagged `pipeline: macro|forex|equity`) so all domains share one log file instead of fragmenting.

Verified, network-required fetch scripts (FRED, one CSV per block per indicator in `data/raw/macro/{BLOCK}_{name}.csv`, columns `date, realtime_start, value`):
- `fetch_gdp.py`, `fetch_cpi.py`, `fetch_central_bank_rate.py`, `fetch_current_account.py` — combined USA+UK fetch per indicator type, built on `fred_common.py`.
- `fetch_usa_gdp.py`, `fetch_usa_cpi.py`, `fetch_usa_central_bank_rate.py`, `fetch_usa_current_account.py` — USA-only split-out versions with `StepLogger` progress output.
- `fetch_uk_gdp.py`, `fetch_uk_cpi.py`, `fetch_uk_central_bank_rate.py`, `fetch_uk_current_account.py` — UK-only split-out versions. Each logs a known data-quality caveat: UK GDP (FRED mirror discontinued mid-2020), UK CPI (~15 months stale), UK central bank rate (monthly OECD proxy, not true event-dated BoE Bank Rate). UK current account pulls from the ONS v1 beta API (series `HBOP`/dataset `pnbp`), not FRED — no confirmed UK ticker exists there.
- `fetch_fred.py` — original combined all-indicators-at-once script (USA+UK × gdp/cpi/rate/current_account in one file); superseded by the per-indicator scripts above but kept as reference/`--verify-only` sanity tool.

WIP / manual / unverified scripts (not wired into `run_fred_pipeline.py`, run manually only):
- `fetch_uk_gdp_ons.py` — no network call; parses a manually-downloaded ONS GDP CSV (`data/raw/macro/UK_gdp_ons_raw.csv`, series ABMI) to extend UK GDP past where the FRED mirror stops (2020-07-01). Overwrites `UK_gdp.csv`.
- `fetch_cpi_uk_alt_wip.py` — candidate replacement for the stale FRED UK CPI series; pulls ONS v1 beta API series `D7BT` (dataset `mm23`). Writes to a separate file (`UK_cpi_ons_alt.csv`), does not overwrite `UK_cpi.csv`, pending manual comparison (different base years make levels non-comparable).
- `fetch_current_account_uk_wip.py` — earlier draft of the ONS current-account fetch now superseded by `fetch_uk_current_account.py` (kept for reference).
- `fetch_composite_pmi_wip.py` — scrapes investing.com's economic calendar for Composite PMI (USA+UK), since ISM/Markit PMI isn't published on FRED. Real limitation: the calendar page only exposes the last ~3-4 releases, so this can only incrementally top up an existing history, never backfill 2014-2024 from scratch.
- `fetch_equity_wip.py` — fetches 9 equity indices (5 USA + 4 UK) daily OHLCV via yfinance into `data/raw/equity/`. Code complete but never run end-to-end (no network in Cowork); UK `^FTAS` (FTSE All-Share) ticker is lowest-confidence.
- `fetch_forex_wip.py` / `fetch_forex_wip - test.py` — 13-pair forex OHLC fetchers, yfinance as the operative source (dukascopy tick-level path kept only as reference since FX volume was dropped from project scope). The "test" variant adds per-day resume/atomic-write logic. Neither has been run against real data end-to-end.
- `fetch_forex_chunked.py` — resumable, chunked forex downloader (13 pairs × 11 years = 143 chunks) built to fix the single-run fragility of `fetch_forex_wip.py` under dukascopy's per-request volume. Chunk files land in `data/raw/forex_chunks/{PAIR}/` with a `manifest.jsonl`; supports `--status`, `--retry-failed`, `--merge` to produce the final `data/raw/forex/` CSVs.

## `features/` — feature engineering (pure pandas, runs in Cowork)

Macro panel builders (no-look-ahead-bias forward-fill using `realtime_start`, not the observation date — logic shared via `panel_common.py`):
- `panel_common.py` — shared helpers: `load_raw_csv`, `business_calendar`, `build_known_as_of` (the core forward-fill), `save_panel`. Also strips timezone info from ONS timestamps so `merge_asof` works.
- `process_gdp.py`, `process_current_account.py` — forward-fill only, no transform. UK current-account column stays absent until `UK_current_account.csv` exists (auto-picks it up once present).
- `process_cpi.py` — forward-fills CPI levels, derives CPI YoY, applies a log transform to UK CPI YoY only.
- `process_central_bank_rate.py` — forward-fills, applies a sqrt transform.
- `process_composite_pmi.py` — placeholder/no-op: no raw PMI CSV exists yet for either block, so it skips both and writes nothing until `fetch_composite_pmi_wip.py` produces data.
- `build_macro_panel.py` — legacy single-script orchestrator combining all 4 macro indicator types × USA/UK into one `data/interim/macro_panel.csv`; superseded by the per-indicator `process_*.py` scripts above (not called by `build_dataset.py`, which reads the separate per-indicator panels instead).

Market panel builders (no look-ahead-bias concern — public prices, not revised):
- `process_forex.py` — reads 13 raw OHLC CSVs from `data/raw/forex/`, reindexes to the business-day calendar with ffill (volume excluded — yfinance FX volume is always 0). Writes `data/interim/forex_panel.csv` (52 cols).
- `process_equity.py` — reads 9 raw OHLCV CSVs from `data/raw/equity/`, reindexes with ffill, sqrt-transforms volume. Writes `data/interim/equity_panel.csv` (54 cols). Skips gracefully if a raw file is missing.
- `technical_indicators.py` — pure function module (no `main`), used by `build_dataset_technical.py`. Computes 12 of 16 planned indicator families per instrument via the `ta` library (SMA/WMA close & volume, Stochastic %K/%D, RSI, Williams %R, CCI, ROC, MACD, MACD signal); 4 families (Momentum N-day, A/D Oscillator, Disparity N-day, OSCP N/M-day) are skipped by design — no `ta` equivalent.

Dataset builders (top-level entry points, run in this order):
- `build_dataset.py` — the main orchestrator. Merges the 6 interim panels (gdp/cpi/rate/current-account/forex/equity) on the business-day calendar, forward-fills macro columns, drops non-stationary CPI level columns and 5 redundant/multicollinear equity indices (`REDUNDANT_INDICES`), adds `rate_differential`, date encodings (int + sin/cos), and the `Direction` target (next-day GBP/USD up/not-up). Writes **Dataset 1**: `data/processed/dataset_basic_daily.csv` (2868 rows × 110 cols).
- `build_dataset_90day.py` — standalone downstream step; loads Dataset 1, adds 90 lagged copies (`_lag1`..`_lag90`) of every lag-eligible column, drops the first 90 warm-up rows. Writes **Dataset 2**: `data/processed/dataset_90day_lookback.csv` (~9,110 cols). Not built yet per project status — script exists but hasn't been run to produce the CSV.
- `build_dataset_technical.py` — standalone downstream step; loads Dataset 1 plus the interim forex/equity panels, computes technical indicators per instrument via `technical_indicators.py`, merges in, drops the first 90 warm-up rows. Writes **Dataset 3**: `data/processed/dataset_technical.csv` (~1,178 cols). Not built yet per project status.

## `models/` — model zoo, training, hyperparameter search

- `preprocessing.py` — `InfinityToNaNTransformer`, a sklearn-compatible transformer converting `+inf`/`-inf` to `NaN` (e.g. `UK_cpi_yoy_log` can be `-inf` during deflation) so `SimpleImputer` can fill them. Kept in its own module, separate from `train.py`, so joblib-pickled `Pipeline` objects can be unpickled from any script — joblib pickles reference a class's module path, and `__main__`-defined classes break when loaded elsewhere.
- `model_registry.py` — single source of truth for all ~21 models (LR, RF, XGB, LGBM, MLP, KNN, DT, ET, HGB, CatBoost, GB, SVM_linear/rbf/sigmoid/poly, Bagging_DT/LR/KNN/SVM_linear/rbf/sigmoid/poly). Each model contributes one `_build_X(params)` (bare unfitted estimator, `random_state=42`) and one `_suggest_X(trial)` (Optuna search space) function, registered in `REGISTRY` with a `scale` flag (adds `RobustScaler` for distance/gradient-sensitive models) and a `speed` tag (`F`/`M`/`S`, exposed as `FAST_MODELS`/`MEDIUM_MODELS`/`SLOW_MODELS` — SVM_rbf/sigmoid/poly and Bagging_SVM_* flagged "do not run at Cowork"). `train.py` and `bayesian_search.py` never change when adding a model — only this file does. XGB/LGBM/CatBoost use lazy imports so the registry still loads without those libs installed.
- `train.py` — trains models across walk-forward CV folds. CLI: `--dataset` (`dataset_basic_daily` default / `dataset_90day_lookback` / `dataset_technical`), `--models` (REGISTRY keys), `--fold` (single 0-based index, default = all folds), `--skip-existing` (resume mode). `build_pipeline()` assembles `InfinityToNaNTransformer → SimpleImputer(median) → [RobustScaler if scale=True] → model`; auto-loads best hyperparameters from `models/search_results/{model}_{dataset}_best_params.json` if present. Gets folds from `walk_forward_cv.get_folds()`; the last fold is labeled `"final"` (held-out 2024). Saves each fitted pipeline to `models/trained/{model}_{dataset}_fold{label}.joblib` and upserts a row into `reports/tables/model_comparison.csv` after every fold, so an interrupted run keeps completed results.
- `bayesian_search.py` — 3-stage Optuna hyperparameter search per model per dataset: (1) inner CV over fold indices `[0,1,2,3]`, maximizing mean F1-macro; (2) `study.best_params` found via `optimize(n_trials=...)`; (3) validated on held-out fold index `4`. CLI: `--dataset`, `--models` (default `["RF"]`), `--trials` (default 50). Writes `models/search_results/{model}_{dataset}_best_params.json`, which `train.py` then auto-loads.

## `evaluation/` — walk-forward CV, metrics, backtesting

- `walk_forward_cv.py` — `get_folds(df, target_col="Direction", first_test_year=2019, n_test_years=1)` builds 6 expanding-window folds: train 2014–2018/test 2019, train 2014–2019/test 2020, … train 2014–2022/test 2023, plus a final train 2014–2023/test 2024 (true held-out set). Self-terminates based on the last year actually present in the data. `describe_folds()` prints date ranges/row counts per fold.
- `metrics.py` — `compute_metrics(y_true, y_pred, y_proba=None, returns=None)` computes accuracy and F1-macro always; AUC-ROC only if `y_proba` is passed; Sharpe proxy (`_annualised_sharpe`) and max drawdown (`_max_drawdown`, peak-to-trough on cumulative log returns) only if `returns` is passed (long-when-predicted-up, else flat strategy).
- `backtest.py` — **implemented and functional** (self-labeled "production" — supersedes the "not yet built" note elsewhere). Stitches per-fold out-of-sample predictions from pre-trained `.joblib` pipelines (no retraining) across folds 1–5 + final into one continuous 2019–2024 daily equity curve, comparing a model-driven long/flat strategy against GBP/USD buy-and-hold. `stitch_oos_predictions()` loads/predicts per fold; `simulate_strategy(spread_pips=0.0)` applies a configurable spread cost on position changes and computes gross/net equity curves; `summarize()` reports accuracy, F1-macro, AUC-ROC, gross/net Sharpe, max drawdown, total returns, trade count. CLI: `--dataset`, `--models` (default `XGB HGB`), `--spread-pips` (0/1/2 sensitivity test), `--open`. Writes per-day CSVs and an equity+drawdown PNG to `reports/tables/` and `reports/figures/`; skips gracefully with a `[WARN]`/`[SKIP]` if a fold's model file is missing.

## `app/` — Streamlit interface (`app.py`, status: production)

Loads trained pipelines from `models/trained/`, the 3 processed datasets, `reports/tables/model_comparison.csv`, and PNGs from `reports/figures/` — reads existing artifacts only, does not train anything.

Run with: `streamlit run src/app/app.py` (from project root), or double-click `auto_open_streamlit.bat` in the project root.

**Code walkthrough (`app.py`):**
- **Paths/constants** — `PROCESSED_DIR`, `TRAINED_DIR`, `COMPARISON_CSV`, `FIGURES_DIR` all resolved relative to project root; `DATASET_FILES`/`DATASET_LABELS` map the 3 dataset keys to files/labels; `FOLD_LABELS` = the 6 walk-forward folds (`1`-`5` + `final`, where `final` is the held-out 2024 set).
- **Cached loaders** — `load_dataset()` and `load_comparison()` use `@st.cache_data`; `load_pipeline()` uses `@st.cache_resource` to keep loaded models in memory across reruns. `available_models()` scans `models/trained/` and filters to models present in `REGISTRY` for the chosen dataset.
- **Sidebar** — 3 dropdowns (Dataset, Model, Fold) drive the whole page; stops with an error if no trained model exists for the selection.
- **Fold data** — re-derives the exact train/test split via `get_folds()` (`src/evaluation/walk_forward_cv.py`) so displayed test data matches what the model was evaluated on.
- **Metrics row** — looks up the matching row in `model_comparison.csv` and renders Accuracy / F1-macro / AUC-ROC / Sharpe proxy / Max drawdown as `st.metric` tiles.
- **Predictions** — runs `pipe.predict()`/`predict_proba()` on the fold's test set; shows a line chart of actual vs. predicted direction and a table of the 20 most recent predictions.
- **Feature importance** — bar chart of top 15 features, shown only for tree-based models (those exposing `feature_importances_`).
- **Comparison tables/charts** — full `model_comparison.csv` rows for the dataset, pre-rendered PNGs from `reports/figures/` (per-model comparison charts + dataset 1 vs 2 vs 3 comparison charts).

Requirements before running: `streamlit` installed, trained `.joblib` files in `models/trained/`, `model_comparison.csv` generated, and the relevant dataset CSV in `data/processed/`.
