# Session Log — Archive

> Entries older than the 2 most recent sessions are moved here.
> Read this file when looking up history; no need to read regularly.

---

## 2026-07-01 (2) — Cleanup checklist + gitignore update

**Branch:** branch_lee

**Done:**

### CLEANUP_BEFORE_SHARE.md — new file (local only, gitignore'd)
- 7-step checklist to run before making repo public / sharing with employers
- Step 1: delete personal workflow files (CLAUDE.md, SESSION_LOG, map.md, task_division.md)
- Step 2: delete personal automation (push.bat, auto_push.py)
- Step 3: delete *.bak files
- Step 4: decide what to do with models/trained/ (72 joblib, potentially large)
- Step 5: list of what to keep visible (src/, notebooks/, reports/, presentation_outline.md...)
- Step 6: README.md update checklist (best result 63.2%, reproduce steps, API keys note)
- Step 7: git hygiene (check commit history, no API keys)

### .gitignore — updated
- Added `CLEANUP_BEFORE_SHARE.md` (never push)
- Added `*.bak` (never push backup files created by Claude Code)

**Stopped at:** cleanup file created; no code changes this sub-session.

**Next steps:** (same as before)
1. Write src/app/app.py — Streamlit UI (Goal 4)
2. Run Bayesian search for fast models if time allows
3. Build actual slides in Google Slides / PowerPoint by July 3

---

## 2026-07-01 — Presentation outline finalized + task division locked

**Branch:** branch_lee

**Done:**

### presentation_outline.md — rewritten (full 10-slide script)
- Slide 1: Title + Project Overview (Lee, ~75 sec)
- Slide 2: Data Sources & Pipeline (Manim, ~70 sec)
- Slide 3: Limitations & Panel Harmonization (Manim, ~70 sec)
- Slide 4: Target Variable Definition (Somitha, ~40 sec)
- Slide 5: EDA — Macro, Forex, Equity (Somitha, ~60 sec)
- Slide 6: Feature Engineering & Build Dataset (Somitha, ~55 sec)
- Slide 7: Walk-Forward CV (Lee, ~60 sec)
- Slide 8: Models + Results + Streamlit with 3 charts (Lee, ~90 sec)
- Slide 9: Conclusion (Lee, ~30 sec)
- Slide 10: References & AI Disclosure (display only)
- Full speaker notes written for every slide in first-person English
- Time budget: 10 min exactly including buffer

### task_division.md — fully updated
- Manim: slides 2-3 only (was 2-3-4 in previous draft)
- Somitha: slides 4-5-6 (Target → EDA → Feature Engineering — logical order)
- Lee: slides 1, 7-9
- Files to read + visuals listed per person
- Time summary table updated

### scripts/plot_model_comparison.py — new file (created earlier this session)
- Generates 4 PNG charts from reports/tables/model_comparison.csv:
  1. cv_vs_final_accuracy.png — CV vs Final 2024 per model, yellow = flagged LR anomaly
  2. auc_by_model.png — AUC-ROC per model with literature reference lines
  3. accuracy_per_fold.png — accuracy per test year 2019-2023 (consistency check)
  4. sharpe_by_model.png — financial usefulness (Sharpe proxy, green/red bars)
- All 4 charts saved to reports/figures/

### PROJECT_GUIDE.md — Glossary section added
- CV Accuracy, Final 2024 Accuracy, AUC-ROC (with thresholds), F1-Macro,
  Sharpe Proxy, Max Drawdown, Walk-Forward CV vs Standard Split — all defined in English

### src/models/train.py — --skip-existing flag added
- `train_all(skip_existing=True)` checks if joblib file exists before training that fold
- CLI: `python src/models/train.py --models RF XGB --skip-existing`
- Enables resuming interrupted training runs without re-training completed folds
- Backup: train.py.bak

**Stopped at:** Presentation outline + task division complete. Slides not yet built in any tool (Google Slides / PowerPoint).

**Next steps:**
1. Build actual slides in Google Slides or PowerPoint — one deck, one file per person by July 3
2. Run Bayesian search for fast models if not yet done: `python src/models/bayesian_search.py --models KNN DT ET HGB CatBoost Bagging_DT Bagging_LR --trials 50`
3. Write `src/app/app.py` — Streamlit UI (Goal 4), needed for screenshot in slide 8
4. Rehearsal July 5-6: time each section, cut detail if any section runs over

---

## 2026-06-30 10:30 — Goal 3B: full model pipeline + 12 fast models trained

**Branch:** branch_lee

**Done:**

### src/evaluation/walk_forward_cv.py — new file
- Expanding-window CV: 6 folds (train 2014→N, test year N+1; final test 2024)
- `get_folds(df)` returns list of `(X_train, y_train, X_test, y_test)` tuples
- `describe_folds()` prints date ranges and sizes
- Verified: Fold 1 train=1303 rows / test=261; Final train=2607 / test=261

### src/evaluation/metrics.py — new file
- Pure function `compute_metrics(y_true, y_pred, y_proba, returns)` → dict
- Metrics: accuracy, f1_macro, auc_roc, sharpe_proxy (annualised, 252-day), max_drawdown
- Missing inputs → None (not NaN) for auc_roc / sharpe / drawdown

### src/models/preprocessing.py — new file
- `InfinityToNaNTransformer` (sklearn BaseEstimator + TransformerMixin)
- Replaces +/-inf with NaN before SimpleImputer step
- Root cause: `UK_cpi_yoy_log` becomes -inf during UK deflation (2015) — log of negative CPI YoY
- Defined in separate file so joblib can deserialise Pipeline from any script (avoids `__main__` pickling issue)

### src/models/model_registry.py — new file (central registry, 22 models)
- Pattern: to add a new model, write `_build_X(params)` + `_suggest_X(trial)` + 1 entry in `REGISTRY`
- `train.py` and `bayesian_search.py` need no changes when adding models
- `scale` flag per entry: True → RobustScaler added in pipeline (LR, KNN, SVM, MLP, Bagging_LR, Bagging_KNN, Bagging_SVM_*)
- Speed tags exported: `FAST_MODELS` (12), `MEDIUM_MODELS` (3), `SLOW_MODELS` (7)
- All 22 models: LR, RF, XGB, LGBM, MLP, KNN, DT, ET, HGB, CatBoost, Bagging_DT, Bagging_LR, GB, SVM_linear, Bagging_KNN, SVM_rbf, SVM_sigmoid, SVM_poly, Bagging_SVM_{linear/rbf/sigmoid/poly}

### src/models/train.py — new file
- Trains any model from REGISTRY across walk-forward folds for a given dataset
- Pipeline order: InfinityToNaNTransformer → SimpleImputer(median) → [RobustScaler] → model
- Auto-loads best_params from `models/search_results/` if JSON exists
- Saves fitted Pipeline to `models/trained/{model}_{dataset}_fold{n}.joblib`
- Upserts results into `reports/tables/model_comparison.csv` (key: dataset+model+fold)
- CLI: `python src/models/train.py --models LR RF --fold 0`

### src/models/bayesian_search.py — new file
- Optuna search; search spaces defined per model in model_registry.py (no logic here)
- Inner CV on folds 1-4 (optimise mean F1-macro), validates result on fold 5
- Saves `models/search_results/{model}_{dataset}_best_params.json`
- CLI: `python src/models/bayesian_search.py --models RF --trials 50`

### Training runs completed
- 12 fast models × 6 folds = 72 Pipeline objects in `models/trained/`
- `reports/tables/model_comparison.csv`: 72 rows with full metrics
- Accuracy highlights (default params, dataset_basic_daily):
  - LR / Bagging_LR: 65–79% (unusually high — to investigate)
  - HGB / CatBoost / Bagging_DT: 55–65% (reasonable)
  - RF / KNN / DT / ET: 48–61% (consistent with paper expectation 53–56%)

### Packages installed
- `optuna 4.9.0`, `catboost`

### map.md — updated
- Model & Evaluation section rewritten with full commands + registry pattern note

**Stopped at:** /savelog — 12 fast models trained; medium/slow and backtest.py pending

**Next steps:**
1. Run bayesian search for fast models: `python src/models/bayesian_search.py --models KNN DT ET HGB CatBoost Bagging_DT Bagging_LR --trials 50`
2. Train medium models (1-5 min/fold): `python src/models/train.py --models GB SVM_linear Bagging_KNN`
3. Train slow models overnight: `python src/models/train.py --models SVM_rbf SVM_sigmoid SVM_poly Bagging_SVM_linear Bagging_SVM_rbf Bagging_SVM_sigmoid Bagging_SVM_poly`
4. Write `src/evaluation/backtest.py` — long strategy simulation, equity curve, Sharpe/drawdown per model
5. Write `src/app/app.py` — Streamlit UI (Goal 4)

---

## 2026-06-30 08:30 — build_dataset.py: Dataset 1 Basic Daily built

**Branch:** branch_lee

**Done:**

### src/features/build_dataset.py — new file
- Builds `data/processed/dataset_basic_daily.csv` in 12 steps (see docstring)
- Loads 6 interim panels (gdp/cpi/rate/ca/forex/equity), merges on bdate_range
- Drops 2014-01-01 (New Year's Day — no forex trading)
- Forward-fills macro cols (_value, _yoy, _yoy_log, _sqrt, _days_since_update)
- Drops level CPI cols (I(1) non-stationary) — keeps YoY only
- Computes equity log returns: `{INDEX}_ret = log(close_t / close_{t-1})`
- Drops all cols for 5 redundant equity indices (DJI/NASDAQ_COMPOSITE/FTSE250/FTSE350/FTSE_ALL_SHARE)
- Adds `rate_differential = USA_central_bank_rate_value − UK_central_bank_rate_value`
- Adds date encodings: day/month/weekday (int) + sin/cos cyclical variants
- Adds `Direction` target: shift(-1) on GBP_USD_close, drops last row

### Output: data/processed/dataset_basic_daily.csv
- **Shape: 2868 rows × 110 cols** (2014-01-02 → 2024-12-30)
- Direction balance: UP=49.1% / DOWN=50.9% — nearly perfectly balanced
- NaN overall: 0.64% (legitimate initial NaN before first macro releases — handled in train.py)
- Main NaN: USA_cpi_yoy 10.5%, UK/USA central_bank_rate 7.6%, USA_current_account 4.1%

### map.md — updated
- Build processed datasets section: replaced CHƯA CÓ with `python src/features/build_dataset.py`

### project_status.py — now shows [OK] for Dataset 1 Basic Daily
- Overall progress: **77% (40/52 items)**

**Stopped at:** Dataset 1 complete — model scripts not yet started

**Next steps:**
1. Write `src/evaluation/walk_forward_cv.py` — expanding window, 6 folds (train 2014→N, test year N+1, final test 2024)
2. Write `src/evaluation/metrics.py` — pure function: accuracy, F1-macro, AUC-ROC, Sharpe proxy, max drawdown
3. Write `src/models/train.py` — LR + RF first to validate end-to-end pipeline
4. Write `src/models/bayesian_search.py` — Optuna hyperparameter search

---

## 2026-06-30 00:05 — Goal 3 plan, GOAL3_PLAN.md, detailed checklist in project_status.py

**Branch:** branch_lee

**Done:**

### References/GOAL3_PLAN.md — new file (English)
- Comprehensive implementation plan for Goal 3 (3A + 3B), written to serve as reference during coding
- **3A section:** pipeline diagram (6 interim panels → build_dataset.py → 3 CSVs), step-by-step table for build_dataset.py (13 steps: load/merge/ffill/drop-redundant-cols/verify-transforms/add-rate_differential/date-encoding/add-target/save), expected output schema for all 3 datasets
- **3B section:** walk-forward fold scheme (expanding: train 2014→N, test year N+1, final test 2024), 5-file code plan (walk_forward_cv.py / metrics.py / train.py / bayesian_search.py / backtest.py), scaling strategy (RobustScaler for LR+MLP only), hyperparameter search space per model, expected accuracy 54–57% based on Guyard & Deriaz 2024
- Includes EDA evidence table (r values) justifying redundant col drops and CPI YoY decision
- Open decisions section (outlier clipping, RobustScaler leak guard, Dataset 3 feature selection method)
- Implementation order with dependency graph (3 weeks)

### scripts/project_status.py — DETAILED_CHECKLIST expanded + 2 new auto-check types
- Backup: `scripts/project_status.py.bak`
- `DETAILED_CHECKLIST` restructured: 6 stages / 19 items → **7 stages / 35 items**
  - cl1 (Setup) + cl2 (EDA): unchanged
  - cl3 **Goal 3A — Build Processed Datasets**: 10 items, 7 auto-check
    - Auto: build_dataset.py exists, dataset1 ≥2000 rows, Direction col, rate_differential col, weekday col, day_sin col, dataset2/3 path
    - Manual: redundant cols dropped (confirmed by user), 16 tech indicator families computed
  - cl4 **Goal 3B — Model & Evaluation Scripts**: 5 items, all auto (path checks for 5 .py files)
  - cl5 **Goal 3B — Training Results**: 7 items, 3 auto (models/trained/ nonempty, search_results/ nonempty, model_comparison.csv exists)
  - cl6 **Goal 3B — Evaluation Quality**: 6 items, 1 auto (reports/figures/ nonempty)
  - cl7 **Goal 4 & Wrap-up**: 4 items, 1 auto (src/app/app.py exists)
- Added 2 helper functions: `_csv_min_rows(path, min_rows)` and `_dir_nonempty(path)`
- Added 2 new check types in `run_checklist_auto()`: `csv_minrows` and `dir_nonempty`
- Verified: `python scripts/project_status.py --no-html` runs clean; overall 75% (39/52); all Goal 3 items correctly show MISSING/uncheck

### map.md — updated
- Added entry: `References/GOAL3_PLAN.md` under "Xem trạng thái project" section

**Stopped at:** /savelog — all planning work captured; no model code written yet

**Next steps:**
1. Write `src/features/build_dataset.py` — Dataset 1 Basic Daily (~130 cols); see GOAL3_PLAN.md step table
   - Load 6 interim panels, merge, ffill, drop redundant equity cols, add rate_differential, date encoding (int + sin/cos), target Direction via shift(-1), drop 2014-01-01, save to `data/processed/dataset_basic_daily.csv`
2. Write `src/evaluation/walk_forward_cv.py` — expanding window, 6 folds (2014→2018/test2019 … final test 2024)
3. Write `src/evaluation/metrics.py` — pure function: accuracy, F1-macro, AUC-ROC, Sharpe proxy, max drawdown
4. Write `src/models/train.py` — LR + RF first to validate end-to-end pipeline

---

## 2026-06-29 23:55 — Q&A: feature selection rationale (EDA findings review)

**Branch:** branch_lee

**Done:**

### Session overview — no files modified, pure analysis Q&A
- Ran `/about`: read PROJECT_GUIDE.md, map.md, SESSION_LOG.md — reported full project status table and next steps to user.
- Answered user question: *"Why drop FTSE350/ALL_SHARE/FTSE250/DJI/NASDAQ_COMPOSITE? Why use CPI YoY instead of level?"*

### Explanation synthesised from notebooks 02 & 03 (evidence cited):
- **Redundant equity drop — multicollinearity:** Notebook 03 Section 6 showed 19 pairs with |r| ≥ 0.85.
  - UK FTSE cluster: FTSE100↔FTSE_ALL_SHARE r=0.993, FTSE100↔FTSE350 r=0.974 → keep FTSE100, drop the 3 broader indices
  - US large-cap: SP500↔DJI r=0.954 → keep SP500 (broader coverage), drop DJI
  - US tech: NASDAQ_COMPOSITE↔NASDAQ100 r=0.992 → keep NASDAQ100 (pure tech signal), drop COMPOSITE
  - Rationale: collinear cols destabilise LR coefficients; split RF importance across near-identical features → noise
- **CPI YoY vs level — non-stationarity:** Notebook 01 Section 4 (ADF test)
  - `USA_cpi_value` and `UK_cpi_value` both fail ADF → I(1) unit root — monotone upward trend 100→130 over 11 years
  - `USA_cpi_yoy` and `UK_cpi_yoy` pass ADF → stationary, mean-reverting around inflation cycle
  - Additional: CPI level USA↔UK r=0.982 (near-duplicate after removing trend); YoY breaks this spurious correlation
  - Rationale: feeding I(1) series into ML risks spurious correlation with target (both trend over time)

**Stopped at:** Q&A complete — no pending code work started

**Next steps:**
1. Begin **Goal 3** — write `src/features/build_dataset.py` to build Dataset 1 Basic Daily (~130 cols)
   - Forward-fill macro NaN, drop redundant equity cols (FTSE350/ALL_SHARE/FTSE250/DJI/NASDAQ_COMPOSITE), use CPI YoY not level, add rate_differential = Fed − BoE, drop 2014-01-01
2. Run notebook 03 to verify RF importance and VIF numbers before finalising feature list
3. Decide on RobustScaler vs StandardScaler strategy for different feature groups

---

## 2026-06-29 23:00 — Key Takeaways, EDA HTML report, menu option 8

**Branch:** branch_lee

**Done:**

### notebooks — Key Takeaways filled in all 3 notebooks
- **01_eda_macro.ipynb — Section 7:** Missing values (forward-fill strategy), Stationarity (GDP/CPI levels are I₁ → use YoY/diff), Correlations (Fed↔BoE r=0.94, USA CPI↔UK CPI r=0.98), Release lags (GDP/CA quarterly max 90d; CPI monthly max 45d), Implications (days_since_update as explicit feature; rate differential as synthetic feature).
- **02_eda_forex_equity.ipynb — Section 11:** Target balance (49.1/50.9% — no SMOTE needed), Returns profile (skew=-0.91, kurtosis=14.44 → RobustScaler), EUR/GBP kurtosis=109 + GBP/CHF kurtosis=173 (clip ±5σ), UK FTSE positively correlated with GBP/USD, Rolling volatility as engineered feature candidate.
- **03_feature_analysis.ipynb — Section 10:** 19 high-corr pairs documented with drop decisions (keep FTSE100/SP500/NASDAQ100, drop DJI/FTSE350/FTSE_ALL_SHARE/NASDAQ_COMPOSITE), RF importance notes, 4 feature clusters labeled, Dataset 1/2/3 implications written.

### scripts/generate_eda_report.py — new script
- Reads 3 executed EDA notebooks (JSON), extracts all cell outputs (text + matplotlib images as base64)
- Renders markdown cells (including Key Takeaways with bold/code/list formatting)
- Generates `reports/eda_summary.html` — standalone, 3-tab HTML (Macro · Forex & Equity · Feature Analysis)
- Flags: `--run-notebooks` (execute via nbconvert first), `--open` (open browser after)
- Output size: ~1592 KB (charts embedded as base64)

### menu.bat — option 8 added
- New option `8 — Generate EDA summary report (HTML)` between options 7 and A
- Runs `python scripts/generate_eda_report.py --open` with optional extra args

### map.md — updated
- Added 2 entries under EDA Notebooks section: `scripts/generate_eda_report.py` and `reports/eda_summary.html`

**Stopped at:** Session closed — /savelog confirmed, all work captured

**Next steps:**
1. Begin **Goal 3** — write `src/features/build_dataset.py` to build Dataset 1 Basic Daily (~130 cols)
   - Forward-fill macro NaN, drop redundant equity cols (FTSE350/ALL_SHARE/FTSE250/DJI/NASDAQ_COMPOSITE), use CPI YoY not level, add rate_differential = Fed − BoE, drop 2014-01-01
2. Run notebook 03 to verify RF importance and VIF numbers before finalising feature list
3. Decide on RobustScaler vs StandardScaler strategy for different feature groups

---

## 2026-06-29 21:00 — Fix notebook 01 errors, create notebook 03

**Branch:** branch_lee

**Done:**

### notebooks/01_eda_macro.ipynb — 3 bugs fixed
- **Bug 1 — statsmodels cascade failure:** `from statsmodels.tsa.stattools import adfuller` was in the shared imports cell; when it raised `ModuleNotFoundError`, `DATA = '../data/interim/'` was never assigned → all downstream cells failed with NameError. Fix: moved statsmodels import into the ADF section cell only, wrapped in `try/except ImportError` with `_statsmodels_ok` flag for graceful degradation.
- **Bug 2 — column filter over-match:** `'value' in c` matched `_value_sqrt` cols; `'yoy' in c` matched `_yoy_days_since_update` and `_yoy_log` cols. Fix: replaced with `c.endswith('_value')` and `c.endswith('_yoy')` throughout the missingness heatmap cell.
- **Bug 3 — pandas 2.x resample API:** `mask.resample('ME').any()` raised `AttributeError: 'DatetimeIndexResampler' object has no attribute 'any'` (removed in pandas 2.x). Fix: replaced with `resample('ME').max()` — equivalent for boolean masks since `max(True, False) = True`.
- Installed `statsmodels 0.14.6` via pip (now available for ADF tests).

### notebooks/02_eda_forex_equity.ipynb — verified clean
- No statsmodels import, no substring column filters, no resample issues. All cells have outputs. No changes needed.

### notebooks/03_feature_analysis.ipynb — created (10 sections)
- Section 1: Load & merge all 6 interim panels into one feature matrix (~130 cols)
- Section 2: Define target (GBP/USD direction, `shift(-1)`)
- Section 3: NaN summary by feature group
- Section 4: Correlation heatmap — macro value/YoY features
- Section 5: Correlation heatmap — forex close returns
- Section 6: Highly correlated pairs (`|r| ≥ 0.85`)
- Section 7: VIF — Variance Inflation Factor (statsmodels, `try/except`)
- Section 8: Random Forest feature importance (sklearn, `try/except`)
- Section 9: Feature clustering dendrogram (scipy, `try/except`)
- Section 10: Key takeaways & selection decisions template
- Applied all 3 notebook rules: optional imports in own cells, `endswith()` for column filters, `.max()` not `.any()` on resampler
- `map.md` updated: removed "CHƯA CÓ" tag for notebook 03

### Memory saved
- `feedback_notebook_import_patterns.md` — 3 rules: (1) optional imports in own `try/except` cell, (2) `endswith()` not `'str' in col`, (3) `resample().max()` not `resample().any()` on pandas 2.x

**Stopped at:** SESSION_LOG update

**Next steps:**
1. Run notebook 03 in JupyterLab, fill in Key Takeaways (sections 01, 02, 03)
2. Begin Goal 3 — build `data/processed/`: start with Dataset 1 Basic Daily (~130 cols)
3. Write `src/features/build_dataset.py` — merge all interim panels, encode date features, add target

---

## 2026-06-29 19:00 — Fix checklist tab % logic

**Branch:** branch_lee

**Done:**

### scripts/project_status.py — checklist tab overall %
- Vấn đề: tab Checklist hiển thị ~21% (đếm checkbox được tick / 19 methodology items) trong khi tab Status hiển thị 73% (file checks) — hai con số đo khác nhau, gây nhầm lẫn
- Đã bỏ thanh Overall dựa trên checkbox count
- Đưa lại thanh Overall nhưng đổi logic: dùng `total_ok / total_countable` từ file checks (cùng nguồn với Status tab)
- `_checklist_tab_html()` nhận thêm 2 param: `total_ok`, `total_countable`
- `generate_html()` truyền 2 param đó vào
- Thanh màu theo ngưỡng: xanh ≥70%, vàng ≥40%, đỏ <40%
- Label đổi thành "Files done: X% (N/M)" để rõ ý nghĩa
- Backup: `scripts/project_status.py.bak`

**Stopped at:** SESSION_LOG update

**Next steps:**
1. Mở JupyterLab (menu option 6), chạy notebook 01 & 02, điền Key Takeaways
2. Tạo `notebooks/03_feature_analysis.ipynb`
3. Goal 3A: build `data/processed/` — Dataset 1 Basic Daily trước

---

## 2026-06-29 17:00 — EDA notebooks, menu.bat Jupyter, scripts/ refactor, checklist tab

**Branch:** branch_lee

**Done:**

### EDA Notebooks (Goal 2)
- Created `notebooks/01_eda_macro.ipynb` — 7 sections: load/overview, missing values heatmap, time series plots (GDP/CPI/rates/current account), ADF stationarity tests, Pearson correlation matrix, release lag distribution, key takeaways template
- Created `notebooks/02_eda_forex_equity.ipynb` — 11 sections: target class balance (~49% UP / ~51% DOWN → no SMOTE), GBP/USD price & returns, OHLC spread ranking, return distribution grid, forex correlation matrix, equity normalised performance, sqrt-volume transform, equity–forex cross-correlation, rolling volatility (Brexit spike annotated)
- `map.md` updated with EDA section

### menu.bat — Jupyter integration
- Added option **6**: `python -m jupyter lab --notebook-dir=notebooks` → opens JupyterLab in browser
- Added option **7**: `python -m jupyter nbconvert --execute --inplace` → runs chosen notebook headless (choice 1/2/3)
- Menu header restructured into DATA / EDA sections

### scripts/ refactor
- Created `scripts/` folder; moved `project_status.py`, `build_index.py`, `run_fred_pipeline.py`, `auto_push.py` from root
- Created `scripts_backup/` with originals (user to delete when ready)
- Fixed `Path(__file__).parent` → `Path(__file__).resolve().parent.parent` in all 4 files (5 occurrences)
- Updated all callers: `menu.bat` (8 refs), `push.bat` (1 ref), `CLAUDE.md` (2 refs), `map.md` (paths + added `menu.bat` entry)

### Checklist tab in project_status.html
- Read `1st_draft_checklist_en.html`, filtered out items already tracked by Phase Details, removed outdated items (Dukascopy, forex volume, PMI, DAX/VIX)
- Added to `scripts/project_status.py`:
  - `_csv_has_column()` helper
  - `DETAILED_CHECKLIST` — 6 stages × 19 items (methodology & procedural)
  - `run_checklist_auto()` — 6 auto-checks from filesystem
  - `_checklist_tab_html()` — generates Checklist tab HTML
  - Tab nav (📊 Status / ✅ Checklist) with localStorage persistence
  - CSS: tab nav, cl-stage, cl-item, auto badge (green)
  - JS: `switchTab()`, `clApplyState()`, localStorage for manual items
- Auto-ticked on run (6/19): FRED key, forex volume exclusion, look-ahead bias guard, class balance (EDA done), equity sqrt, CPI log
- Manual (13/19): bank holidays, stationarity decision, date encoding, PCA, stacking, CV folds, sensitivity analysis, high-vol flagging, rolling re-fit, slides, demo, APA refs
- `map.md`: removed reference to `checklist_en.html`, now points to `reports/project_status.html`
- `1st_draft_checklist_en.html` can be deleted by user

**Stopped at:** SESSION_LOG update

**Next steps:**
1. Run notebooks 01 & 02 in JupyterLab (menu option 6), fill in Key Takeaways sections
2. Create `notebooks/03_feature_analysis.ipynb`
3. Begin Goal 3: build `data/processed/` datasets (start with Dataset 1 — Basic Daily)

---

## 2026-06-29 13:00 — Build forex_panel and equity_panel → Phase 2 complete

**Branch:** branch_lee

**Done:**
- Created `src/features/process_forex.py` → `data/interim/forex_panel.csv`
  - 13 pairs × 4 OHLC cols = 52 columns, 2870 rows, 0 NaN
  - Volume excluded per spec (yfinance FX volume = 0)
  - Aligned to bdate_range via reindex + ffill
- Created `src/features/process_equity.py` → `data/interim/equity_panel.csv`
  - 9 indices × 5 OHLCV cols + 9 sqrt(volume) cols = 54 columns, 2870 rows
  - 1 NaN row on 2014-01-01 (New Year's Day, no trading data — expected, will be dropped during final dataset build)
  - sqrt transform applied to volume columns per spec section 3
- Updated `map.md`: replaced "CHƯA CÓ" placeholders for both scripts
- Phase 2 now 6/6 panels complete
- Overall progress: 65% → 69% (36/52 items OK)

**Stopped at:** SESSION_LOG update

**Next steps:**
1. Begin **Goal 2 — EDA notebooks** (`notebooks/`)
   - `01_eda_macro.ipynb` — macro panel: missing values, stationarity, correlation matrix
   - `02_eda_forex_equity.ipynb` — OHLC distributions, GBP/USD target balance (class imbalance check)
   - `03_feature_analysis.ipynb` — feature importance, multicollinearity

---

## 2026-06-29 12:10 — Remove forex volume from project scope

**Branch:** branch_lee

**Done:**
- **Decision:** forex volume dropped from project scope — yfinance FX volume = 0 (spot FX has no consolidated tape); Dukascopy would provide real tick volume but ~800k requests for 13 pairs × 11 years; OHLC alone is sufficient for the model.
- Updated `References/GBPUSD_ML_data_requirements_spec.md`: forex OHLCV→OHLC, 65→52 cols; indicator rows 3–4 (volume MAs) marked "equity only"; sqrt transform note fixed; worked example forex table and transform examples updated
- Updated `PROJECT_GUIDE.md`: folder comment OHLCV→OHLC; removed dukascopy line from forex pipeline
- Updated `References/CLAUDE.md` item 7: replaced volume trade-off discussion with "decision made, yfinance OHLC is the operative choice"
- Updated `src/data/fetch_forex_wip.py` docstring: removed volume-reliability justification, clarified dukascopy path is kept as WIP reference only

**Stopped at:** session log update

**Next steps (unchanged):**
1. Create `src/features/process_forex.py` → `data/interim/forex_panel.csv` (OHLC only, no volume)
2. Create `src/features/process_equity.py` → `data/interim/equity_panel.csv`
3. Once both panels complete → Phase 2 fully done → begin Goal 2 (EDA notebooks)

---

## 2026-06-29 11:50 — Fill UK macro data gaps, drop Composite PMI

**Branch:** branch_lee

**Done:**

### UK GDP — replaced FRED discontinued series with ONS manual download
- Copied `D:\series-170626.csv` → `data/raw/macro/UK_gdp_ons_raw.csv` (ONS series ABMI, real GDP chained vol. £m, release 2026-05-14)
- Wrote `src/data/fetch_uk_gdp_ons.py` — parses ONS quarterly format, sets `realtime_start = end_of_quarter + 60 days` per row to approximate release lag
- Generated new `UK_gdp.csv`: 48 rows, 2013-01-01 → 2024-10-01 (old FRED version backed up as `UK_gdp.csv.bak`)
- Re-ran `process_gdp.py` → `gdp_panel.csv` rebuilt: UK_gdp_value 2870/2870 rows OK

### UK CPI — swapped in ONS source (replaces FRED series that was 15 months behind)
- `UK_cpi_ons_alt.csv` already fetched via `fetch_cpi_uk_alt_wip.py` (ONS series D7BT, 161 rows through 2026-05)
- Fixed `realtime_start`: was single snapshot 2026-06-16 → recomputed per row as `end_of_month + 42 days`
- Copied processed alt file → `UK_cpi.csv` (old FRED version backed up as `UK_cpi.csv.bak`)
- Re-ran `process_cpi.py` → `cpi_panel.csv` rebuilt: UK columns 2870/2870 rows OK

### UK Current Account — integrated into panel
- `UK_current_account.csv` already fetched via `fetch_uk_current_account.py` (ONS series HBOP, 52 rows)
- Fixed `realtime_start`: was single snapshot 2026-03-30 → recomputed per row as `end_of_quarter + 60 days`
- Re-ran `process_current_account.py` → `current_account_panel.csv` rebuilt: UK columns 2870/2870 rows OK
- Updated `build_macro_panel.py`: added `"current_account"` to UK INDICATORS

### Composite PMI — dropped permanently
- Investigated: S&P Global / CIPS Composite PMI is proprietary — not on FRED
- ISM Manufacturing PMI was removed from FRED by ISM in 2016
- investing.com only shows ~3-4 most recent releases, no historical data
- Scraper confirmed working (`fetch_composite_pmi_wip.py`) but cannot backfill 2014–2024
- **Decision: PMI dropped from project scope.** WIP scripts kept as documentation.
- Removed PMI entries from `project_status.py`, `map.md`, `build_macro_panel.py`

**Goal 1A result:** all 8 items now OK (no WARN, no BLOCKED)

**Stopped at:** SESSION_LOG update

**Next steps:**
1. Create `src/features/process_forex.py` → build `data/interim/forex_panel.csv` from 13 forex CSVs
2. Create `src/features/process_equity.py` → build `data/interim/equity_panel.csv` from 9 equity CSVs
3. Once both panels complete → Phase 2 fully done → begin Goal 2 (EDA notebooks)

---

## 2026-06-29 11:08 — Fix stale memory, remove status tracking, translate docs to English

**Branch:** branch_lee

**Done:**
- Diagnosed why memory was outdated: SESSION_LOG.md was updated each session but `data_status.md` memory and `PROJECT_GUIDE.md` were never synced → caused drift
- Updated memory file `data_status.md` to reflect 2026-06-29 reality (forex/equity have real data, not header-only)
- Removed status percentages/emojis from `CLAUDE.md` (4 goals line) and `PROJECT_GUIDE.md` (goals table + entire "Data Status" section) — SESSION_LOG.md is now the single source of truth for data status
- Translated `PROJECT_GUIDE.md` and `SESSION_LOG.md` fully to English (project is shared with multiple readers)

**Stopped at:** documentation cleanup before closing

**Next steps (unchanged from previous session — high → low priority):**
1. Create `src/features/process_forex.py` → build `data/interim/forex_panel.csv` from 13 forex CSVs
2. Create `src/features/process_equity.py` → build `data/interim/equity_panel.csv` from 9 equity CSVs
3. Decide on UK CPI: swap `UK_cpi_ons_alt.csv` into `process_cpi.py` → rebuild `cpi_panel.csv`
4. Integrate `UK_current_account.csv` into `process_current_account.py` → rebuild `current_account_panel.csv`
5. Find UK GDP alternative source (ONS direct)
6. Once interim is complete → build `data/processed/` (3 dataset variants)
7. Build `src/models/` and `src/evaluation/`

---

## 2026-06-29 10:11 — Status review, update SESSION_LOG, create CLAUDE.md

**Branch:** branch_lee

**project_status.py result (run at 10:11):** Overall 74% — 32/43 items OK

**Changes that happened since the previous log (2026-06-27) but were not recorded:**

### Phase 1B — Forex (complete)
All 13 FX pairs fetched for real via yfinance (`run_forex_wip.bat --source yfinance`):
| Pair | Rows | Coverage |
|---|---|---|
| GBP/USD (target) | 2,866 | 2014-01-01 → 2024-12-30 |
| EUR/USD, AUD/USD, NZD/USD, USD/CAD, USD/CHF, USD/JPY | 2,866 | 2014-01-01 → 2024-12-30 |
| EUR/GBP, GBP/AUD, GBP/CAD, GBP/CHF, GBP/NZD | 2,867 | 2014-01-01 → 2024-12-30 |
| GBP/JPY | 2,867 | 2014-01-01 → 2024-12-30 |

> Note: volume = 0 for all FX pairs on yfinance — known limitation (documented in spec). OHLC is reliable; volume is not usable.

### Phase 1C — Equity (complete)
All 9 equity indices fetched for real via yfinance (`run_equity_wip.bat`):
| Index | Rows | Coverage |
|---|---|---|
| S&P 500, Nasdaq Composite, Nasdaq 100, DJI, Russell 2000 | 2,767 | 2014-01-02 → 2024-12-30 |
| FTSE 100, FTSE 250, FTSE All-Share | 2,777–2,778 | 2014-01-02 → 2024-12-30 |
| FTSE 350 | 2,697 | 2014-01-02 → 2024-12-30 |

### Phase 1A — Macro (unchanged)
- USA: 4 indicators OK
- UK central bank rate: OK
- UK GDP: **WARN** — FRED discontinued Jul-2020, need alternative source
- UK CPI: **WARN** — stale ~15 months; `UK_cpi_ons_alt.csv` (161 rows, ONS) available but not yet swapped into pipeline
- UK Current Account: `UK_current_account.csv` (52 rows, ONS) available but not yet integrated into interim panel
- Composite PMI (USA + UK): **BLOCKED** — no historical source found

### Phase 2 — Interim (partial)
4 macro panels OK (`gdp`, `cpi`, `central_bank_rate`, `current_account` — 2,870 rows each).
Forex panel and Equity panel **not yet built** — highest priority next step.

**Stopped at:** status review + SESSION_LOG update + CLAUDE.md root creation

---

## 2026-06-27 — Split macro fetch scripts per block, add StepLogger

**What was done:**
- Split 4 combined scripts (fetch_gdp/cpi/central_bank_rate/current_account) into 8 separate scripts for USA and UK
- Created `StepLogger` class in `pipeline_log_common.py` — console print + JSON log per script
- Updated `fred_common.py`: added `log_fn` callback so chunk-level messages route through the logger
- Updated `run_fred_pipeline.py`: calls the 8 new scripts, added `--block USA|UK` filter flag
- Promoted `fetch_current_account_uk_wip.py` → `fetch_uk_current_account.py` (removed _wip suffix)
- Saved logging convention to global memory + project memory

**New files created (8 scripts):**
- `src/data/fetch_usa_gdp.py`
- `src/data/fetch_uk_gdp.py`
- `src/data/fetch_usa_cpi.py`
- `src/data/fetch_uk_cpi.py`
- `src/data/fetch_usa_central_bank_rate.py`
- `src/data/fetch_uk_central_bank_rate.py`
- `src/data/fetch_usa_current_account.py`
- `src/data/fetch_uk_current_account.py`

**Files modified:**
- `src/data/pipeline_log_common.py` — added `StepLogger` class
- `src/data/fred_common.py` — added `log_fn` param
- `run_fred_pipeline.py` — refactored to use 8 new scripts, added `--block` flag

**Old scripts (fetch_gdp.py, fetch_cpi.py, fetch_central_bank_rate.py, fetch_current_account.py):**
Still in repo, not deleted, but no longer called by the pipeline.
