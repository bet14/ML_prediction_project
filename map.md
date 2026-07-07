# map.md — File Registry by Task

> Quick lookup: "I want to do X → which file do I need"
> No need to read PROJECT_GUIDE.md unless you need to understand conventions in depth.

---

## Check project status

| What you want to do | File/Command |
|---|---|
| See status of all data (raw/interim/processed) | `python scripts\project_status.py` → prints table + saves `reports/project_status.html` |
| Open Task Runner (interactive menu) | `menu.bat` |
| See overall project progress (visual) | `reports/project_status.html` — "Status" tab (file checks) · "Checklist" tab (methodology tasks) |
| See session history | `SESSION_LOG.md` (2 most recent entries) · `SESSION_LOG_archive.md` (older) |
| See full spec: column list, data requirements | `References/GBPUSD_ML_data_requirements_spec.md` |
| Fast technical orientation for AI agents (architecture, flow, conventions, decisions, current gaps) | `agent.md` |
| See detailed Goal 3 plan (3A datasets + 3B models) | `References/GOAL3_PLAN.md` |
| See Dataset 2/3 build + train + report plan (draft, pending decisions) | `References/DATASET_2_3_PLAN.md` |
| See pipeline ERD | `eurusd_data_pipeline_erd.html` |
| Personal notes on "Framing" & "Maintain" course-schema stages (not in team deck, gitignored) | `References/personal_framing_maintain_notes.md` |

---

## Fetch raw data (needs network — run on personal machine)

| What you want to do | File/Command |
|---|---|
| Fetch macro USA (GDP/CPI/rate/current_account) | `run_fred_pipeline.py` → calls `src/data/fetch_usa_*.py` |
| Fetch macro UK (GDP/CPI/rate/current_account) | `run_fred_pipeline.py` → calls `src/data/fetch_uk_*.py` |
| Fetch UK CPI from ONS (alt source) | `src/data/fetch_cpi_uk_alt_wip.py` |
| Fetch UK current account from ONS | `src/data/fetch_uk_current_account.py` |
| Fetch 13 forex pairs (yfinance/dukascopy) | `run_forex_wip.bat` → `src/data/fetch_forex_wip.py` |
| Fetch 9 equity indices (yfinance) | `run_equity_wip.bat` → `src/data/fetch_equity_wip.py` |
| Fetch UK GDP from ONS (parse manual download) | `src/data/fetch_uk_gdp_ons.py` — parses `UK_gdp_ons_raw.csv` |
| FRED API helpers | `src/data/fred_common.py` |
| Logging/StepLogger | `src/data/pipeline_log_common.py` |

---

## Build interim panels (runs in Cowork, no network needed)

| What you want to do | File/Command |
|---|---|
| Build GDP panel → `data/interim/gdp_panel.csv` | `src/features/process_gdp.py` |
| Build CPI panel → `data/interim/cpi_panel.csv` | `src/features/process_cpi.py` |
| Build Central Bank Rate panel → `data/interim/central_bank_rate_panel.csv` | `src/features/process_central_bank_rate.py` |
| Build Current Account panel → `data/interim/current_account_panel.csv` | `src/features/process_current_account.py` |
| Build all macro panels at once | `src/features/build_macro_panel.py` |
| Build Forex panel → `data/interim/forex_panel.csv` | `src/features/process_forex.py` |
| Build Equity panel → `data/interim/equity_panel.csv` | `src/features/process_equity.py` |
| Shared panel helpers | `src/features/panel_common.py` |

---

## EDA Notebooks (Goal 2)

| What you want to do | File/Command |
|---|---|
| EDA macro indicators (GDP, CPI, rates, CA) | `notebooks/01_eda_macro.ipynb` |
| EDA forex & equity (OHLC, target balance) | `notebooks/02_eda_forex_equity.ipynb` |
| Feature analysis (importance, multicollinearity) | `notebooks/03_feature_analysis.ipynb` |
| Generate summary EDA HTML report from the 3 notebooks | `python scripts/generate_eda_report.py --open` |
| View EDA report (3 tabs: Macro · Forex/Equity · Feature Analysis) | `reports/eda_summary.html` — open in browser |

---

## Build processed datasets (Phase 3)

| What you want to do | File/Command |
|---|---|
| Build Dataset 1 — Basic Daily (~110 cols) | `python src/features/build_dataset.py` → `data/processed/dataset_basic_daily.csv` |
| Build Dataset 2 — 90-Day Lookback (~9,110 cols) | `python src/features/build_dataset_90day.py` → `data/processed/dataset_90day_lookback.csv` |
| Build Dataset 3 — Technical Indicators (~1,178 cols) | `python src/features/build_dataset_technical.py` → `data/processed/dataset_technical.csv` (uses `src/features/technical_indicators.py`, 12/16 indicator families via `ta` library; equity limited to 4 non-redundant indices, same `REDUNDANT_INDICES` as Dataset 1) |

---

## Model & Evaluation (Phase 5)

| What you want to do | File/Command |
|---|---|
| **Add a new model** | Only edit `src/models/model_registry.py` — add `_build_X` + `_suggest_X` + one entry in REGISTRY |
| Train models (LR/RF/XGB/LGBM/MLP) | `python src/models/train.py --models LR RF --fold 0` |
| Bayesian hyperparameter search | `python src/models/bayesian_search.py --models RF --trials 50` |
| Walk-forward CV splits | `src/evaluation/walk_forward_cv.py` — `get_folds(df)` |
| Compute metrics (acc/f1/auc/sharpe/drawdown) | `src/evaluation/metrics.py` — `compute_metrics(y_true, y_pred, ...)` |
| View trained models | `models/trained/*.joblib` |
| View hyperparameter search results | `models/search_results/*_best_params.json` |
| View model comparison table | `reports/tables/model_comparison.csv` |
| Generate model comparison charts (CV vs final acc, AUC, per-fold acc, Sharpe) | `python scripts/plot_model_comparison.py --open` → `reports/figures/*.png` |
| Generate ROC + Precision-Recall curves on the 2024 held-out fold | `python scripts/plot_roc_pr_curves.py --open` (default: XGB/HGB/Bagging_LR/LGBM; `--models all` for all 12 trained models) → `reports/figures/roc_pr_curves.png` |
| Generate Dataset 1 vs 2 vs 3 comparison charts (accuracy/AUC/Sharpe/overfit gap, all 12 models) | `python scripts/plot_dataset_comparison.py --open` → `reports/figures/dataset_comparison_*.png` |
| Generate bias-variance trade-off scatter (one per dataset; x=fold-to-fold accuracy std-dev, y=final accuracy; only 3-4 extreme models labeled) — draft support for Slide 8b | `python scripts/plot_variance_tradeoff.py --open` → `reports/figures/variance_tradeoff_dataset{1,2,3}_*.png` |
| View Dataset 1 vs 2 vs 3 comparison report (key findings + charts + per-model tables) | `python scripts/generate_dataset_comparison_report.py --open` → `reports/dataset_comparison.html` |
| Walk-forward backtest — stitch OOS fold predictions into one 2019-2024 equity curve, long/flat strategy vs buy-and-hold, spread-cost sensitivity | `python src/evaluation/backtest.py --dataset dataset_basic_daily --models XGB HGB --spread-pips 1.5 --open` → `reports/figures/equity_curve_<model>_<dataset>.png` + `reports/tables/backtest_<model>_<dataset>.csv` + `reports/tables/backtest_summary.csv` |
| View final course presentation (slide deck, single HTML file) | `reports/final_presentation.html` — open in browser (working copy: `reports/draft_final_presentation.html`) |

---

## Streamlit UI (Goal 4)

| What you want to do | File/Command |
|---|---|
| Run the GBP/USD prediction interface | `streamlit run src/app/app.py` (requires `streamlit` installed — run on personal machine) |
| One-click launch (no typing) | `auto_open_streamlit.bat` (project root) |
| What the app does | Select model + fold → view metrics, predicted vs actual, feature importance, model comparison table, 4 charts from `reports/figures/` |
| Code walkthrough + Streamlit usage guide | `src/README.md` — `app/` section |

---

## Git & Maintenance

| What you want to do | File/Command |
|---|---|
| Push to git | `push.bat` or `python scripts\auto_push.py` |
| Update session log | `SESSION_LOG.md` — prepend a new entry, keep max 2 entries; archive older ones → `SESSION_LOG_archive.md` |
| API keys | `Key/fred_key.txt` (gitignored) · `configs/.env.example` |
| Fetch gotchas (ONS/FRED/yfinance) | `References/CLAUDE.md` |
