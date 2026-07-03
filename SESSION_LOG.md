# Session Log — GBP/USD ML Prediction Project

> **Append-only.** Add one new entry at the top of this file each session (most recent on top).
> Goal: reading the 2–3 most recent days is enough to know what's happening, where work stopped, and what comes next.

---

## 2026-07-03 20:15 — New "Model Training & Fine-Tuning" slide, corrected app.py status, verified regularization/tuning by reading code

**Branch:** branch_lee

**Done:**

### Fact-check: src/app/app.py — confirmed already built, not "not yet built"
- Read the file directly: 169 lines, `STATUS: production`, model/fold selector, metrics, predicted-vs-actual chart, feature importance, comparison table/charts — fully working, previously verified running via `streamlit run` (2026-07-02 session)
- Slide 10 (Streamlit App)'s "Status" table incorrectly said `src/app/app.py` = "Not yet built" (leftover from an earlier draft stage) — corrected to "Built — 169 lines, verified running via streamlit run"
- Removed "12/22 ready" framing throughout (Slide 9 status table, Slide 10 status table, Slide 9's issues/next-steps list) — reworded to state the 12 trained models by name and describe the rest as "planned next, time allowing" instead of a fraction

### Verified fine-tuning/regularization by reading the actual code and JSON files (not assumed)
- Read `models/search_results/*.json` for all 12 trained models directly — confirmed every one has a saved Optuna best-params file (all fine-tuned, none left on library defaults)
- Confirmed only **LR** (`penalty` ∈ {l1, l2} + C) and **HGB** (`l2_regularization`) carry an explicit classic regularization term; LR's actual tuned result is **L1, C=0.68**. MLP uses `alpha` (L2 weight decay, tuned to 0.0025). Bagging_LR's base LogisticRegression keeps sklearn's default L2 (only C + n_estimators were searched, not penalty). Tree ensembles (RF/ET/DT/Bagging_DT/XGB/LGBM/CatBoost) regularize structurally via depth/leaf/sampling limits, no L1/L2 term.
- Confirmed no classic train/val "learning curve" exists in the codebase (`scripts/plot_model_comparison.py` has only 4 chart functions: CV-vs-Final accuracy, AUC-by-model, accuracy-per-fold, Sharpe-by-model) — these substitute for a learning curve since a random train/val split would leak future information in a time series
- Computed real CV-vs-Final accuracy gaps directly from `model_comparison.csv` to ground the bias-variance claims (LR +8.2pp gap, Bagging_LR +6.3pp gap = overfit; XGB +1.0pp, CatBoost −4.5pp = well-generalized; DT capped at max_depth=3 by the search itself = underfit)

### reports/draft_final_presentation.html — new Slide 8 "Model Training & Fine-Tuning"
- Inserted between Walk-Forward CV and Models & Results (now slide 8 of 12; sidebar renumbered, `slides.length` auto-drives the counter)
- Training workflow diagram (Bayesian search → inner validation on fold 5 → best_params.json → refit on all 6 folds)
- Full 12-model table: family, how each model works, which regularization/complexity knob was tuned, and the actual best value found (real numbers from search_results/*.json, not placeholders)
- Table of the 4 evaluation charts and what each one reads as
- 3-card bias-variance breakdown (high variance/overfit: LR, Bagging_LR · low variance/well-generalized: XGB, CatBoost · high bias/underfit: DT), all numbers pulled from model_comparison.csv this session

### Verified in-browser
- Served over temporary local `python -m http.server` (stopped afterward): checked new slide 8 in full, Slide 9 status table wording, Slide 10 status table — all render correctly, no leftover "12/22" phrasing found in a follow-up grep of Slide 9's issues/next-steps list (fixed 2 more instances there too).

**Stopped at:** all requested changes applied and visually verified; not committed/pushed yet.

**Next steps:**
1. User to do a final visual pass in their own browser, especially the new Slide 8 model table on narrow widths
2. `push.bat` once approved
3. Resume Dataset 2/3 (90-day lookback / technical indicators) work — still not started
4. Decide what to do with `References/06_Admin_Affiliation_Document.pdf` (flagged earlier as likely misplaced personal data, still unresolved)

---

## 2026-07-03 19:30 — Converted 3 more tables to card/diagram style, fixed encoding

**Branch:** branch_lee

**Done:**

### reports/draft_final_presentation.html — more table→card conversions (continuing from previous session's diagram restyle)
- Slide 3 (Data Limitations): "Two features investigated and excluded" table → 2-card `.pipe-detail-grid` (Composite PMI, FX trading volume), each card keeping the issue text and a `num-bad` "Decision: Excluded" line
- Slide 4 (Target Variable Definition): "Task: GBP/USD next-day direction prediction" table → 4-card `.pipe-detail-grid` (What is predicted / Input / Target / Problem type), matching the same blue→purple→orange→green accent cycle used elsewhere in the deck
- Slide 6 (Feature Engineering): "Dropped (EDA-justified)" and "Added / encoded" tables → put side by side in a `.cols` (2-column) layout, each column itself a 2-col `.pipe-detail-grid` of cards (6 dropped-feature cards, 4 added-feature cards) — matches the "Three data categories" card pattern from Slide 2

### Fixed missing charset declaration
- File had no `<meta charset="utf-8">` — caused mojibake ("Â·", "â‰ˆ") when served over plain HTTP (e.g. `python -m http.server` without a charset header, browser guessed wrong encoding). Added `<meta charset="utf-8">` right before `<title>`. Affects the whole deck, not just today's edits — a real bug now fixed, not just a test artifact.

### Verified in-browser
- Served over temporary local `python -m http.server` (stopped afterward), checked slides 1, 3, 4, 6 — all render correctly, correct colors, correct UTF-8 characters (·, ≈, →) after the charset fix.

**Stopped at:** all requested changes applied and visually verified; not committed/pushed yet.

**Next steps:**
1. User to do a final visual pass in their own browser
2. `push.bat` once approved
3. Resume Dataset 2/3 (90-day lookback / technical indicators) work and `src/app/app.py` build — still not started, carried over from earlier sessions
4. Decide what to do with `References/06_Admin_Affiliation_Document.pdf` (flagged earlier as likely misplaced personal data, still unresolved)

---

## 2026-07-03 18:45 — Split Streamlit slide out, restyled pipeline diagrams to match reference deck

**Branch:** branch_lee

**Done:**

### reports/draft_final_presentation.html — Streamlit App promoted to its own slide (Goal 4)
- Slide 8 was previously "Models, Results & Streamlit Interface" combined in one slide — split into Slide 8 "Models & Results" and a new Slide 9 "Streamlit App"
- New Streamlit slide adds an "App data flow" diagram (User input → Model selector → Pipeline.predict() → Direction+confidence) plus the 3 feature cards (input form, prediction output, feature importance) and a build-status table (`src/app/app.py` still not built; 12/22 trained models ready to load)
- Sidebar/nav renumbered: 9 Streamlit App → 10 Conclusion → 11 References (11 slides total, `slides.length` auto-drives the count so no other JS changes needed)

### Pipeline diagram restyle — matched to user-supplied reference (`5-layer-detection-with-demo-2.html`)
- Rewrote `.flow-step`/`.flow-arrow` CSS: each step in a `.flow` now gets a distinct accent color + soft glow via `nth-child` (blue→purple→orange→green→cyan→red, cycling through existing CSS vars), applied automatically to **every** pipeline diagram in the deck (Goal-overview flow, data-collection flow, model pipeline flow, time-alignment flow) — no per-slide markup changes needed beyond content
- Added new `.pipe-detail-grid` / `.pipe-card` classes (colored top border matching the flow step above it) — used to replace the Model Pipeline's plain Step/Role/Key-tasks table with 4 colored cards, and reused for the "Three data categories" section (3 cards: Macro / Forex / Equity) and the Streamlit feature list

### Slide 2 (Data Sources & Pipeline) — table transposed to match horizontal flow
- "Three data categories" table → converted to a 3-card diagram (category, source, contents)
- The 6-step pipeline flow's Step/Role/Key-tasks table was **transposed**: step names now sit as column headers (color-matched to the flow diagram above), with two rows underneath ("Role", "Key tasks"); task descriptions shortened to fit horizontally, wrapped in `overflow-x:auto` for narrow viewports

### Slide 3 (Data Limitations & Time Alignment) — vertical flow converted to horizontal
- "Time-alignment without look-ahead bias" diagram changed from `.flow-vert` (4 stacked boxes with ↓ arrows) to `.flow` (horizontal, → arrows), text shortened to fit, colors applied automatically via the new nth-child CSS

### Slide 4 (Target Variable Definition) — added explicit task framing
- Added a "Task: GBP/USD next-day direction prediction" box above the formula, spelling out What is predicted / Input / Target / Problem type in plain terms before the `Direction(t) = 1 if close(t+1) > close(t)` formula

### Slide 1 (Introduction) — title made prominent
- `<h1>` title font size increased (1.6rem → 2.6rem), centered, bold, gradient-colored (accent→accent2) via `background-clip:text`; subtitle centered to match

### Verified in-browser
- Served the file over a temporary local `python -m http.server` (Claude-in-Chrome blocks `file://` URLs) and visually checked: title slide, Data Sources & Pipeline (category cards + transposed table), Time-alignment (horizontal flow), Target Variable (task box), Models & Results (colored pipe-cards), new Streamlit App slide — all render correctly with matching colors

**Stopped at:** all requested changes applied and visually verified; not yet reviewed by the user in their own browser, not committed/pushed.

**Next steps:**
1. User to do a final visual pass in their own browser (esp. the transposed table on narrow/projector widths — it has `min-width:820px` inside a scroll container)
2. `push.bat` once approved, to commit the updated `draft_final_presentation.html`
3. Resume Dataset 2/3 (90-day lookback / technical indicators) work and `src/app/app.py` build — still not started, carried over from earlier sessions
4. Decide what to do with `References/06_Admin_Affiliation_Document.pdf` (flagged last session as likely misplaced personal data, still unresolved)

---

## 2026-07-03 16:00 — Rebuilt draft_final_presentation.html end-to-end with data-verified content

**Branch:** branch_lee

**Done:**

### reports/draft_final_presentation.html — resumed, then fully redesigned across several iterations
- Initial resume: fixed missing `CV_B64`/`ACC_B64`/`SHARPE_B64` JS consts (the file had been interrupted mid-build, leaving Slide 8 charts blank) — embedded the 3 PNGs from `reports/figures/` as base64
- Full redesign per user request: removed all speaker names/time badges/speaker notes from every slide; converted bullet lists to tables/grids/diagrams throughout; added a left sidebar outline (click to jump slides) and menu hide/show toggle
- Added an Entity-Relationship Diagram for the data pipeline on Slide 2 — first attempt used mermaid.js via CDN but text contrast was unreadable (white-on-light rows); **rebuilt as static HTML/CSS cards** instead (no CDN dependency, guaranteed contrast using the deck's own color variables)
- Added a light/dark theme toggle button (persisted via localStorage), a click-to-zoom lightbox for all chart/EDA images, tag-pill styling for EDA findings, and a real visual walk-forward CV diagram (color-coded grid: train/test/unused years per fold) generated by JS
- Pulled 3 real images from `reports/eda_summary.html` (macro correlation heatmap, forex returns distribution, equity price series) into Slide 5 instead of describing them in bullets

### Data-verification pass — corrected several inaccurate claims in the deck
- Analyzed `data/processed/dataset_basic_daily.csv` directly (pandas): actual shape is 2,868 × **111** columns (not 110 as CLAUDE.md states) — added a real column-breakdown table to Slide 6 (Forex 52, Equity 28, Macro 20, Date/Calendar 10, Target 1) with dtype and per-category NaN ratio (macro worst at 3.53% avg, USA CPI YoY worst single column at 10.46%)
- Analyzed `reports/tables/model_comparison.csv` directly: confirmed only **12 of 22** registry models were actually trained (the other 10 — SVM kernels, Bagging_KNN, GB — are defined but never run, too slow at this scale); corrected Slide 8's wrong claim that CatBoost was "most reliable" — real 2024 held-out data shows Bagging_LR/LGBM lead on accuracy but XGB/HGB have the best Sharpe proxy, while Bagging_LR (accuracy leader) has the worst Sharpe — added this as an explicit "depends on the metric" table plus an Issues/Next-steps box
- Rewrote the Bayesian search section to describe only what the team actually did (Optuna/TPE, 50 trials/model, F1-macro objective on an inner split) instead of a "paper vs ours" comparison, using the real search log (`reports/bayesian_search_fast_models.log`) — including the finding that Bagging_LR had the highest inner-validation F1 (0.756) but the worst real Sharpe, i.e. inner search score did not predict generalization
- Added detailed Role/Key-tasks tables for both pipeline diagrams (data collection: fetch→raw→process→interim→build_dataset→final CSV; model pipeline: InfinityToNaNTransformer→SimpleImputer→RobustScaler→Model), each step's purpose grounded in actual source code (`src/models/preprocessing.py`, `src/models/model_registry.py`)

### Slide 10 References — replaced placeholder text with real APA-7 citations
- Extracted first-page text from all PDFs in `References/` via `pdftotext` to get real titles/authors/venues; wrote 9 full APA citations (previously the slide just said "FX direction prediction, LSTM volatility forecasting..." with no real citations)
- Fixed a wrong author initial: primary reference is "Guyard, K. C." not "Guyard, T." (confirmed from the PDF itself)
- **Found `References/06_Admin_Affiliation_Document.pdf` is not a research paper** — it's a French personal payroll/affiliation letter containing what looks like a personal address and client ID. Excluded it from citations and flagged it to the user as likely misplaced (not moved/deleted — user's call)
- Rewrote AI Disclosure to reflect actual working relationship (team decided code/outline/plan; Claude Code executed under that direction, wrote testing code, explained concepts) instead of the earlier vaguer wording
- Changed layout from 2-column grid to single vertical column (Primary reference → Data sources → Papers → AI Disclosure)

### Slide 1 — added course/class/team info
- Added Course = "Statistical Analysis & Machine Learning", Class = "DSA Spring 2026", and full team names (Manimegalai Kumar-Periyasamy, Somitha Gudivada, Linh Hoang-Thuy) per user-supplied emails

### Sidebar outline reorganized
- Changed from "Part 1/Part 2" grouping to "Overview → Goal 1 (Data Collection) → Goal 2 (EDA & Target Definition) → Goal 3 (Model Pipeline & Metrics) → Goal 4 (Streamlit UI) → Wrap-up", matching the course's 4 official goals, each with sub-items

**Stopped at:** presentation content and structure complete; not yet verified visually in a real browser this session (Claude-in-Chrome extension blocks `file://` URLs, so verification was via `Start-Process` opening the user's default browser — user has not yet confirmed final visual review).

**Next steps:**
1. User to visually review the rebuilt deck end-to-end (colors, ERD contrast, lightbox, walk-forward diagram, all data tables) in an actual browser
2. Decide what to do with `References/06_Admin_Affiliation_Document.pdf` (likely move out of the project, contains personal data)
3. Resume the Dataset 2/3 (90-day lookback / technical indicators) work planned in the previous session — not touched this session
4. `push.bat` once the deck is approved, to commit the new `draft_final_presentation.html`

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
