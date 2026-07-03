# agent.md — Technical Reference for AI Agents

> Companion to `PROJECT_GUIDE.md` (full spec) and `map.md` (file lookup). This file is a fast-orientation
> snapshot: architecture, flow, conventions, decisions, and current known state. Verify against the
> filesystem before relying on any number here — this file decays as the project moves.

**Last verified:** 2026-07-02 (file counts, git status, and registry contents checked directly, not from memory)

---

## 1. Overall architecture

One-way pipeline, no cycles, three environments with different capabilities:

```
[personal machine / Colab — network]        [Cowork sandbox — no network]
src/data/fetch_*.py                          src/features/process_*.py
  -> data/raw/{macro,forex,equity}/            -> data/interim/*_panel.csv
                                              src/features/build_dataset.py
                                                -> data/processed/dataset_basic_daily.csv
                                              src/models/train.py
                                              src/models/bayesian_search.py
                                                -> models/trained/*.joblib
                                                -> models/search_results/*.json
                                                -> reports/tables/model_comparison.csv
                                              src/app/app.py (Streamlit, view-only)
```

- **Data collection** requires network (FRED API, yfinance, ONS) → personal machine only.
- **Everything from `process_*.py` onward** is pure pandas/sklearn on already-fetched CSVs → runs fine in Cowork.
- **`src/app/app.py`** never computes anything new — it only re-reads `models/trained/*.joblib` and `reports/tables/model_comparison.csv`. This is deliberate: instant load, no training delay in the demo.

## 2. Flow (per goal)

1. **Goal 1 — Data:** `fetch_*.py` → `data/raw/` (macro has `realtime_start` column for no-look-ahead).
2. **Goal 2 — EDA:** `notebooks/01-03` read `data/interim/` panels, findings feed feature decisions in `build_dataset.py` (e.g. drop 5 collinear equity indices, use CPI YoY not level).
3. **Goal 3A — Dataset build:** `build_dataset.py` merges 6 interim panels + date encoding + `Direction` target → `data/processed/dataset_basic_daily.csv` (2868×110).
4. **Goal 3B — Model pipeline:**
   - `model_registry.py` defines every model (`_build_X` + `_suggest_X` + `REGISTRY` entry). This is the **only** file touched when adding a model.
   - `bayesian_search.py` runs Optuna on folds 1-4, validates on fold 5, writes `models/search_results/{model}_{dataset}_best_params.json`.
   - `train.py` auto-loads that JSON if present, fits the full Pipeline per fold, saves `.joblib`, upserts a row into `model_comparison.csv`.
   - `walk_forward_cv.py::get_folds(df)` is the single source of truth for the 6-fold split — used identically by `train.py`, `bayesian_search.py`, and `app.py` (so the app never leaks future data).
5. **Goal 4 — Streamlit:** `app.py` scans `models/trained/` for available model×fold combos, loads the matching `.joblib`, rebuilds `X_test/y_test` via `get_folds`, predicts live, displays metrics from `model_comparison.csv` + static PNGs from `reports/figures/`.

## 3. Conventions — implementation / test / deploy

**Implementation**
- Before editing any `.py` file: copy it to `file_name.py.bak` in the same folder first (project rule, see `CLAUDE.md`). `*.bak` is gitignored.
- Adding a model → edit only `src/models/model_registry.py`. Never touch `train.py` / `bayesian_search.py` for that.
- All code, comments, print/log output, and generated file contents must be in **English** (multi-person shared repo). Chat replies to the user stay in whichever language the user used (Vietnamese by default per global CLAUDE.md).
- New file → update `map.md` immediately, and add it to the `scripts/project_status.py` CHECKLIST if applicable.

**Test**
- No automated test suite (`pytest`, CI) exists in this repo — verification is manual:
  - `python scripts/project_status.py` — filesystem-based status check (raw/interim/processed presence, row counts, expected columns).
  - `python run_fred_pipeline.py --verify-only` — checks FRED series IDs without fetching.
  - `python src/models/train.py --models X --fold 0` — quick one-fold smoke test before a full run.
- No `tests/` directory. If adding real tests, decide with the user first (not currently part of the course scope).

**Deploy**
- No deploy target beyond local `streamlit run src/app/app.py`. There is no hosting step in the 4 course goals.
- `push.bat` / `scripts/auto_push.py` — auto add/commit/push + rebuild `index.html`, personal machine only (needs SSH key). Never run in Cowork.

## 4. Important technical decisions

| Decision | Why |
|---|---|
| Forward-fill macro data using `realtime_start`, not the period date | Prevents look-ahead bias — a GDP figure for Q1 isn't known until its actual publish date |
| Expanding-window walk-forward CV (not sliding, not random split) | Macro indicators carry long-term structure; random split would leak future into training. Follows Guyard & Deriaz (2024) |
| `InfinityToNaNTransformer` in its own file (`src/models/preprocessing.py`), not `train.py` | Avoids joblib pickling failure when a `Pipeline` containing a class defined in `__main__` is loaded from a different script (`app.py`) |
| CPI used as YoY, not level | Level series fail ADF (I(1), non-stationary) → risk of spurious correlation with target. YoY is stationary |
| Dropped FTSE250/FTSE350/FTSE_ALL_SHARE/DJI/NASDAQ_COMPOSITE | \|r\| ≥ 0.85 with a kept index (FTSE100/SP500/NASDAQ100) — multicollinearity, not information loss |
| Forex volume excluded entirely | yfinance FX volume is always 0 (no consolidated spot-FX tape); Dukascopy tick data would need ~800k requests for 13 pairs × 11 years — not worth it for this scope |
| Composite PMI dropped from scope | No free historical source found for USA+UK 2014–2024 (FRED discontinued ISM PMI in 2016, S&P/CIPS PMI is proprietary) |
| `app.py` is read-only (no live training) | Keeps the demo fast and reproducible; also guarantees the UI never trains on data it then evaluates on |

## 5. Current status (verified 2026-07-02, not from memory)

| Component | Status |
|---|---|
| Macro panels (USA) | Built — 4 indicators |
| Macro panels (UK) | Built, with caveats — GDP/CPI swapped to ONS sources, Composite PMI dropped |
| Forex / Equity panels | Built (`forex_panel.csv`, `equity_panel.csv`) |
| `dataset_basic_daily.csv` | Built — 2868 rows × 110 cols |
| Dataset 2 (90-day) / Dataset 3 (Technical) | **Not built** |
| Model registry | 22 models defined (`src/models/model_registry.py`), grouped `FAST_MODELS` (12) / `MEDIUM_MODELS` (3) / `SLOW_MODELS` (7) |
| Bayesian search | **Complete for all 12 FAST_MODELS** — `models/search_results/` has 12 `*_best_params.json` |
| Trained `.joblib` | **Only 9 of the 12 fast models actually trained** (54 files = 9×6 folds): LR, RF, DT, ET, HGB, CatBoost, Bagging_DT, Bagging_LR, KNN. **XGB, LGBM, MLP have tuned params but no trained pipeline yet** — gap, see TODO |
| `model_comparison.csv` | Matches the 9 trained models only |
| Medium/slow models (GB, SVM_*, Bagging_KNN, Bagging_SVM_*) | Not trained |
| `src/app/app.py` | Written and verified running (`streamlit run src/app/app.py`), docstring marks `STATUS: production` |
| `src/evaluation/backtest.py` | Not built (mentioned in guide, not yet started) |
| Presentation | Outline + task division locked; slides not yet built (deadline: 2026-07-03) |

## 6. Known dirty / untracked files

As of 2026-07-02 `git status`:
- **Modified (tracked, noisy):** `catboost_info/catboost_training.json`, `catboost_info/learn/events.out.tfevents`, `catboost_info/learn_error.tsv`, `catboost_info/time_left.tsv` — CatBoost writes these on every run; the folder is **not gitignored**, so every CatBoost training run dirties git status. Consider adding `catboost_info/` to `.gitignore` (ask the user first — not done yet).
- **Deleted (tracked):** `catboost_info/tmp/cat_feature_index.*.tmp` — transient CatBoost temp file, safe to let go, same root cause as above.
- **Untracked:** `models/search_results/Bagging_DT_dataset_basic_daily_best_params.json`, `Bagging_LR_dataset_basic_daily_best_params.json`, `CatBoost_dataset_basic_daily_best_params.json` — real output from this session's Bayesian search runs (the other 9 search-result JSONs are already committed). These should be committed on the next `push.bat`, not discarded.
- Two stray `.bak` files at repo root (`PROJECT_GUIDE.md.bak`, `project_status.py.bak`) exist on disk but are gitignored (`*.bak` rule) — harmless, not part of git state.

## 7. TODO / next steps

1. Train the 3 missing fast models to close the registry/trained gap: `python src/models/train.py --models XGB LGBM MLP --skip-existing`
2. Re-run `scripts/plot_model_comparison.py` afterward so the 4 comparison PNGs include XGB/LGBM/MLP.
3. Decide whether to train medium/slow models (`GB`, `SVM_*`, `Bagging_KNN`, `Bagging_SVM_*`) given the time budget before the presentation, or stop at fast models.
4. Write `src/evaluation/backtest.py` (long-strategy simulation) — mentioned in `PROJECT_GUIDE.md` as not yet built.
5. Build Dataset 2 (90-day lookback) and Dataset 3 (Technical indicators) — only if the course requires more than Dataset 1 for the final grade; not currently in the immediate next-steps list from `SESSION_LOG.md`.
6. Build the actual presentation deck (Google Slides/PowerPoint) — deadline 2026-07-03, per `presentation_outline.md` / `task_division.md`.
7. Housekeeping: consider gitignoring `catboost_info/` (confirm with user before editing `.gitignore`).

---

## Where to look next

- `PROJECT_GUIDE.md` — full spec, folder structure, CV strategy, glossary, Streamlit user guide.
- `map.md` — "I want to do X → which file" lookup table.
- `SESSION_LOG.md` — last 2 days of session history (older entries in `SESSION_LOG_archive.md`).
- `References/GBPUSD_ML_data_requirements_spec.md` — full data/column spec.
- `References/GOAL3_PLAN.md` — detailed Goal 3A/3B implementation plan.
