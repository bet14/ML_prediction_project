# Session Log — GBP/USD ML Prediction Project

> **Append-only.** Add one new entry at the top of this file each session (most recent on top).
> Goal: reading the 2–3 most recent days is enough to know what's happening, where work stopped, and what comes next.

---

## 2026-07-03 11:30 — Planned Dataset 2/3 training workflow, cleaned up duplicate global savelog command

**Branch:** branch_lee

**Done:**

### Estimated training time for Dataset 2 (90-day lookback) and Dataset 3 (technical)
- Used real `elapsed_s` data from `reports/tables/model_comparison.csv`: all 12 fast models × 6 folds on Dataset 1 (110 cols) took only ~103s total
- Dataset 3 (~120-130 cols, modest technical-indicator addition): estimated ~2-5 min for full 12-model × 6-fold run
- Dataset 2 (~9,700 cols from 90-day lag stack): estimated ~35-90 min, with `MLP`/`Bagging_LR`/`KNN` likely the slowest due to curse of dimensionality
- Noted Dataset 2/3 CSVs are not yet built — `build_dataset.py` currently only handles Dataset 1

### Verified train.py / bayesian_search.py / app.py behavior for multi-dataset support
- `train.py` and `bayesian_search.py` already support `--dataset dataset_90day_lookback` / `--dataset dataset_technical` via `DATASET_FILES` dict — no code changes needed there
- Confirmed dataset name is embedded in `.joblib` filenames (`{model}_{dataset}_fold{N}.joblib`) and in the `(dataset, model, fold)` key used to update `model_comparison.csv`, so training Dataset 2/3 will not overwrite or require retraining Dataset 1 results
- `app.py` currently hardcodes `dataset_name = "dataset_basic_daily"` (line 77) and its local `DATASET_FILES` only has one entry (line 36-38) — needs a small manual edit (add dataset selector) before it can show Dataset 2/3 results; `available_models()` already accepts `dataset_name` as a parameter so no change needed there
- Recommended skipping Bayesian search for Dataset 2 (too slow at ~9,700 cols) and training with default params instead, consistent with the "fast models already proven to work" approach

### Housekeeping: removed duplicate global `/savelog` command
- Found two `savelog.md` command files: global (`C:\Users\Hp\.claude\commands\savelog.md`) and project-local (`.claude\commands\savelog.md`)
- Global version had a hardcoded path to a *different* project's memory file (`dsp-practical-work`) — stale leftover, not matching this project's conventions
- User deleted the global version manually; project-local version (correct, scoped to this project's `SESSION_LOG.md`) kept

**Stopped at:** planning/discussion only this session — no dataset build or training run executed yet.

**Next steps:**
1. Write `build_dataset.py` support (or a new script) to actually generate `dataset_90day_lookback.csv` and `dataset_technical.csv`
2. Once built, run `python src/models/train.py --dataset dataset_technical --models <12 fast models>` (cheap, ~2-5 min)
3. Run `python src/models/train.py --dataset dataset_90day_lookback --models <12 fast models>` (expect ~35-90 min, monitor RAM)
4. Edit `app.py` to add a dataset selector before demoing Dataset 2/3 in Streamlit
5. Build the presentation deck (Google Slides/PowerPoint) — deadline **2026-07-03**

---

## 2026-07-02 (2) — Trained XGB/LGBM/MLP, refreshed comparison charts, gitignored catboost_info/

**Branch:** branch_lee

**Done:**

### Closed the trained-model gap (Goal 3)
- `python src/models/train.py --models XGB LGBM MLP --skip-existing` — all 3 models trained across 6 folds each (18 new `.joblib` files in `models/trained/`, untracked)
- `models/trained/` now has all **12 fast models × 6 folds = 72 files**, matching the 12 tuned params in `models/search_results/`
- `reports/tables/model_comparison.csv` now has 72 rows (was 54)

### Re-ran comparison charts
- `python scripts/plot_model_comparison.py` — regenerated all 4 PNGs in `reports/figures/` (`cv_vs_final_accuracy.png`, `auc_by_model.png`, `accuracy_per_fold.png`, `sharpe_by_model.png`) to include XGB/LGBM/MLP

### Decision: stop at fast models
- User decided **not** to train medium/slow models (GB, SVM_*, Bagging_KNN, Bagging_SVM_*) given time budget before the 2026-07-03 presentation deadline

### Housekeeping: catboost_info/ gitignored
- Added `catboost_info/` to `.gitignore`
- Ran `git rm -r --cached catboost_info/` to untrack it (files still exist on disk, just no longer tracked/dirtying git status on every CatBoost run)

**Stopped at:** all 3 next-steps items from the previous entry are done; nothing uncommitted needs review before `push.bat` except the usual (new joblib files, search_results JSONs, chart PNGs, CSV, .gitignore, this log).

**Next steps:**
1. Build the actual presentation deck (Google Slides/PowerPoint) — deadline **2026-07-03**
2. `push.bat` to commit + push all pending changes (new models, charts, catboost_info removal, session log)
3. `src/evaluation/backtest.py` still not built (mentioned in guide) — only if time allows after slides
4. Dataset 2 (90-day) / Dataset 3 (technical) — only if course requires beyond Dataset 1

---

## 2026-07-02 — Verified: Streamlit app running + Bayesian search complete for all fast models

**Branch:** branch_lee

**Done:**

### src/app/app.py — verified working (Goal 4)
- Confirmed file is complete (169 lines, docstring marks `STATUS: production`), not a scaffold
- Loads trained pipelines from `models/trained/`, model/fold selector in sidebar, metrics row (accuracy/F1/AUC/Sharpe/drawdown), predicted-vs-actual chart, feature importance (tree models), full comparison table + 4 PNG charts
- User confirmed running via `streamlit run src/app/app.py`

### Bayesian search — completed for all 12 FAST_MODELS
- `models/search_results/` now has 12 `*_best_params.json` files (one per fast model): LR, RF, XGB, LGBM, MLP, KNN, DT, ET, HGB, CatBoost, Bagging_DT, Bagging_LR
- 3 new this session (untracked in git): `Bagging_DT`, `Bagging_LR`, `CatBoost` — the other 9 were already committed as of the last auto-push (`847653b`, 2026-07-01 13:20)

### Gap found while verifying: trained joblib count lower than search-result count
- `models/trained/` has only **54 files = 9 models × 6 folds** (Bagging_DT, Bagging_LR, CatBoost, DT, ET, HGB, KNN, LR, RF)
- **XGB, LGBM, MLP have tuned Bayesian params but were never (re)trained** — no `.joblib` files, no rows in `reports/tables/model_comparison.csv`, so they don't appear in the Streamlit sidebar
- Confirmed `xgboost` and `lightgbm` packages import fine in this environment — not a dependency issue, just not run yet

**Stopped at:** verification pass only — no new training run triggered this session

**Next steps:**
1. Train the 3 missing fast models with tuned params: `python src/models/train.py --models XGB LGBM MLP --skip-existing`
2. Re-run `scripts/plot_model_comparison.py` after the above (4 PNG charts will include the 3 new models)
3. Decide whether to train medium/slow models (GB, SVM_*, Bagging_KNN, Bagging_SVM_*) or stop at fast models given time budget
4. Build actual slides in Google Slides/PowerPoint (deadline July 3)
5. Clean up `catboost_info/` noise in git status (modified every CatBoost run, never gitignored) — see `agent.md` known issues

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


## Template for next session

```
## YYYY-MM-DD HH:MM — [Short summary of what this session did]

**Branch:** branch_lee

**Done:**
- [ ] ...

**Stopped at:**
- ...

**Next steps:**
1. ...
```
