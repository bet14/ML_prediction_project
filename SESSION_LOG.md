# Session Log — GBP/USD ML Prediction Project

> **Append-only.** Add one new entry at the top of this file each session (most recent on top).
> Goal: reading the 2–3 most recent days is enough to know what's happening, where work stopped, and what comes next.

---

## 2026-07-07 14:30 — Replaced the accuracy-vs-Sharpe scatter with a real bias-variance trade-off chart in `scripts/plot_variance_tradeoff.py`; updated `presentation_outline.md` and `map.md` to match

**Branch:** branch_lee

**Done:**

### User feedback: the "VARIANCE & TRADE-OFF" charts (Slide 8b) weren't actually a bias-variance chart
- The existing `scripts/plot_variance_tradeoff.py` plotted accuracy (x) vs. Sharpe proxy (y) with all 12 models individually labeled per dataset — a profit-vs-accuracy trade-off, not a bias-variance one, despite the filename/slide title. User asked for the real bias-variance trade-off, clarified per dataset, and to drop the "spot every model by name" clutter.

### Rewrote `scripts/plot_variance_tradeoff.py` to build a genuine bias-variance scatter from the real walk-forward CV fold numbers in `reports/tables/model_comparison.csv`
- x-axis = fold-to-fold accuracy std-dev across inner CV folds 1-5 (variance — how much a model's accuracy swings year to year during tuning)
- y-axis = final (2024 held-out) accuracy (bias proxy — low accuracy = underfit regardless of stability)
- Reference lines: 50% coin-flip (high-bias threshold) and each dataset's own median fold-to-fold σ (typical variance for that dataset) — ideal quadrant = top-left
- Only 4 points per dataset are labeled (auto-picked, not hardcoded): highest final accuracy, lowest final accuracy, highest variance, and a "best trade-off" point (highest accuracy among below-median-variance models) — the other ~8 models are plain dots colored by family (Linear / Tree-Bagging / Boosting / Other) via a legend, replacing the old 12-name clutter
- Same 3 output filenames as before (`variance_tradeoff_dataset{1,2,3}_*.png`), so no other doc/script needed a filename update

### Ran the script and visually verified all 3 regenerated PNGs
- Dataset 1 (Basic Daily): CatBoost auto-labeled "best trade-off" (63.2% acc, σ=0.033) vs. Bagging_LR (highest acc 67.4% but σ=0.047) and DT (lowest acc 47.5%, below coin flip)
- Dataset 2 (90-Day Lookback): whole cloud sits in a tight 48-62% band regardless of variance — visual confirmation of the already-documented p≫n negative-result finding; CatBoost still tops accuracy (62.1%)
- Dataset 3 (Technical Indicators): boosting/tree cluster (LGBM, HGB, CatBoost, ET, XGB, Bagging_DT) packs into the top-left ideal quadrant at 82-83% accuracy, low variance; HGB auto-labeled "best trade-off"; DT is a dramatic outlier — highest variance in the whole project (σ=0.096, 3-4x every other model) and the only sub-50% accuracy on this dataset

### Updated `presentation_outline.md` (Slide 8b section + Goal 3 summary + speaker notes) to describe the new chart correctly
- Replaced all "accuracy on x-axis, Sharpe proxy on y-axis" / "all 12 models spotted" language with the new axis definitions, reference lines, and per-dataset labeled-point description
- Rewrote the per-chart bullet points and speaker notes paragraph with real numbers pulled from the regenerated charts; removed a leftover duplicate sentence fragment from the old draft that had survived an earlier edit

### Updated `map.md` entry for `plot_variance_tradeoff.py` to describe the new axes/behavior instead of the old accuracy-vs-Sharpe wording

**Stopped at:** script rewritten, run, and verified visually against all 3 datasets; `presentation_outline.md` and `map.md` both updated to match. `reports/draft_final_presentation.html` does not reference these charts directly (no changes needed there for this task) — its other unrelated pending diff from before this session was left untouched.

**Next steps:**
1. If `draft_final_presentation.html`'s Slide 8b is ever built out with embedded images (currently only in the text outline draft), embed the 3 regenerated PNGs there too, using the new bias-variance description
2. `push.bat` once user wants to commit — updated `scripts/plot_variance_tradeoff.py`, regenerated `reports/figures/variance_tradeoff_dataset{1,2,3}_*.png`, `presentation_outline.md`, `map.md`
3. Everything else still uncommitted from prior sessions (trained `.joblib` files, `model_comparison.csv`, dataset comparison report/scripts, the pre-existing `draft_final_presentation.html`/`map.md` diff from session start) remains pending, carried over unchanged

---

## 2026-07-06 19:15 — Fixed Dataset 3 (Technical Indicators) still using all 9 equity indices instead of the 4 non-redundant ones; rebuilt dataset, retrained all 12 models, updated reports/docs

**Branch:** branch_lee

**Done:**

### Found and fixed an inconsistency: `build_dataset_technical.py` never applied the equity redundant-index filter
- User asked why Dataset 3 computes technical indicators for all 9 equity indices when Dataset 1 (`build_dataset.py`'s `REDUNDANT_INDICES`) already found 5 of them multicollinear (`USA_DJI`, `USA_NASDAQ_COMPOSITE`, `UK_FTSE250`, `UK_FTSE350`, `UK_FTSE_ALL_SHARE`, per `notebooks/03_feature_analysis.ipynb` correlation analysis) and dropped them
- Confirmed via `References/DATASET_2_3_PLAN.md` line 102 that the *plan* for Dataset 2 (90-day lookback) explicitly intended "4 index còn lại" after dropping the 5 redundant ones, but the Dataset 3 plan/implementation was never updated to match — an oversight, not an intentional design choice (no Q1-Q4 decision in the plan doc ever addressed this for Dataset 3 specifically)
- Backed up `src/features/build_dataset_technical.py` -> `.py.bak`, then imported `REDUNDANT_INDICES` from `build_dataset.py` and filtered `equity_indices` before the technical-indicator loop; remaining 4 equity indices: `UK_FTSE100`, `USA_NASDAQ100`, `USA_RUSSELL2000`, `USA_SP500`

### Rebuilt Dataset 3 and retrained everything downstream
- `python src/features/build_dataset_technical.py` -> `data/processed/dataset_technical.csv` shrank from ~1,538 to **1,178 cols** (2,778 rows, unchanged), NaN 0.09%
- Retrained all 12 fast models x 6 folds on the new `dataset_technical` (`python src/models/train.py --dataset dataset_technical --models LR RF DT KNN HGB XGB LGBM CatBoost ET MLP Bagging_LR Bagging_DT`) — `reports/tables/model_comparison.csv` upserted cleanly (72 rows for dataset_technical, no duplicates, verified via key `dataset+model+fold`)
- Regenerated `reports/figures/dataset_comparison_{accuracy,auc,sharpe,overfit_gap}.png` (`scripts/plot_dataset_comparison.py`) and `reports/dataset_comparison.html` (`scripts/generate_dataset_comparison_report.py`)

### Updated docs to match the new column counts
- `References/DATASET_2_3_PLAN.md`: added a dated correction row/note to the "ĐÃ CHỐT" column-count table and to the Next Steps section (both previously said 9 index / ~1,538 cols)
- `map.md`: Dataset 3 row now says "~1,178 cols" and notes the 4-index filter

**Stopped at:** fix verified end-to-end (rebuild -> retrain -> reports regenerated -> docs updated). No backtest existed for `dataset_technical` before this session, so none was generated now (out of scope of this fix — `backtest.py` only covers `dataset_basic_daily` models so far, a pre-existing gap).

**Next steps:**
1. If backtesting Dataset 3 models is wanted later, extend `src/evaluation/backtest.py` to accept `--dataset dataset_technical`
2. Presentation deck (`reports/draft_final_presentation.html`, Slide 9) cites the old Dataset 2/3 comparison numbers/charts — will need re-embedding the regenerated PNGs and re-checking the accuracy/Sharpe figures next time that deck is touched
3. Consider a quick correlation check on the new 4 equity indices + their technical indicators to confirm no further redundancy remains before relying on Dataset 3 results

---

## 2026-07-06 17:30 — Clarified pipeline-vs-feature-engineering placement in the deck; compared deck's intro workflow against the course's official ML-workflow schema; drafted then split out personal "Framing/Maintain" notes

**Branch:** branch_lee

**Done:**

### Clarified why `InfinityToNaNTransformer -> SimpleImputer(median) -> RobustScaler` lives on Slide 7 (Model Pipeline) and not Slide 6 (Feature Engineering) in `reports/draft_final_presentation.html`
- User's question was legitimate: these look like feature-engineering steps. Reason they're intentionally separate: Slide 6's drops/additions (CPI YoY, log returns, rate_differential, date encoding) are static, dataset-level transforms computed once before any CV split; imputation/scaling must be refit per training fold (median/IQR fit only on train, never test) to avoid leakage — that's why they're bundled inside the sklearn Pipeline object on Slide 7 instead
- Added one short italic note on each slide (Slide 6: "imputation/scaling aren't shown here... run per training fold inside the model Pipeline (Slide 7) to avoid leakage"; Slide 7: "Refit per training fold here, not once in Feature Engineering (Slide 6) — intentional, to avoid leakage")
- Added the full explanation to `presentation_outline.md`'s Slide 6 speaker notes and Slide 7 content (the short HTML notes point here for detail, per user's explicit request to keep slides terse and put detail only in the outline)

### Compared the deck's Slide 1 intro workflow (`Data Collection -> EDA -> Model Pipeline -> Streamlit UI`) against the course's own "oversimplified schema machine learning workflow" (DSA course slides PDF, page 14: `data analysis -> framing -> training (loop: improve preprocessing, add data sources) -> move to PROD -> maintain`)
- Rendered page 14 as an image via PyMuPDF (`fitz`) since `pdftoppm`/poppler isn't installed on this machine and `pdftotext` alone only returned the slide title, not the diagram
- Found 3/5 stages map cleanly (data analysis=EDA, training=Model Pipeline, move to PROD=Streamlit UI) but 2 are implicit/missing in the deck's simplified diagram: **framing** (target/metric/feasibility/labelling decisions folded silently into the Target Variable slide) and **maintain** (out of scope — deliverable stops at the Streamlit demo); also noted the deck's linear flow arrow doesn't show the course schema's training-stage feedback loop (iterate on preprocessing / add data sources), even though the project did do this in practice (e.g., added Dataset 2/3 later, fixed `InfinityToNaNTransformer` after finding UK CPI deflation produced -inf)

### Drafted 2 new slides ("Framing the Problem", "Maintain") directly in `draft_final_presentation.html` first, then reverted per user's follow-up request to keep them out of the shared deck entirely
- Initially inserted both as real slides (12 -> 14, renumbered nav) to make the deck fully mirror the course's 5-stage schema
- User then asked to split them into a personal-only file instead — removed both slide blocks and reverted the side-nav back to the original 12 entries; confirmed slide count is back to 12 via `slides.push(` grep count

### Created `References/personal_framing_maintain_notes.md` (new file, gitignored)
- Content/Speaker-notes format matching `presentation_outline.md`'s style, covering the same Framing (define target / business metric / POC feasibility-ROI / gather labelling) and Maintain (performance monitoring, data drift, concept drift, retraining cadence, label lag, versioning/rollback) material that was drafted for the deck, kept here instead as personal reference only
- Added `References/personal_framing_maintain_notes.md` to `.gitignore` under the existing "Local-only files (never publish)" section
- Added a `map.md` entry pointing to the new file (per project convention: update `map.md` immediately when creating a new file)

**Stopped at:** `draft_final_presentation.html` is back to its original 12-slide structure (only the 2 short italic cross-reference notes on slides 6/7 are new); `presentation_outline.md` has the fuller Slide 6/7 explanation; the Framing/Maintain material lives only in the new gitignored personal file, not in the graded deck.

**Next steps:**
1. `push.bat` once user wants to commit — the 2 short HTML notes + outline explanation are fine to share with the team; `References/personal_framing_maintain_notes.md` will NOT be pushed (gitignored), which is intentional
2. Everything else still uncommitted from prior sessions (trained `.joblib` files, `model_comparison.csv`, `backtest.py`, dataset comparison report/scripts) remains pending, carried over unchanged
3. Consider updating `CLAUDE.md`'s stale "Not yet built" list (still flagged across several sessions, still not done — project-instructions file the user may want to edit themselves)

---

## 2026-07-06 15:45 — Updated presentation deck (`draft_final_presentation.html` + `presentation_outline.md`) with Dataset 2/3 results and the new multi-dataset Streamlit app

**Branch:** branch_lee

**Done:**

### Updated `reports/draft_final_presentation.html` (source of truth) to reflect that Dataset 2/3 are now trained and Streamlit supports all 3 datasets — both were still described as pending/Dataset-1-only in the deck
- Embedded the 4 existing `dataset_comparison_{accuracy,auc,sharpe,overfit_gap}.png` charts as new base64 JS consts (`DSCOMP_ACC_B64`, `DSCOMP_AUC_B64`, `DSCOMP_SHARPE_B64`, `DSCOMP_GAP_B64`), wired through the same `__PLACEHOLDER__` → `.replace()` mechanism the deck already uses for its other charts
- **Slide 9 (Models & Results):** added a new "Dataset 1 vs 2 vs 3 — does more data help?" box + the 4 new charts, with the key findings: Dataset 2 (90-day lookback, 9,110 cols) is a documented negative result — near coin-flip for all 12 models (p≫n); Dataset 3 (technical indicators) is a strong, consistent win for every tree/boosting model (80-85% acc., CV→Final gap <4pp) but linear models score *lower* than on Dataset 1, and — the counter-intuitive part — the much higher accuracy does not translate into a better Sharpe proxy. Also fixed the "Which model is most effective" and "Open issues & next steps" sections, which still said Dataset 2/3 and `backtest.py` were not yet built (both were completed in prior sessions)
- **Slide 10 (Streamlit App):** flow diagram now shows a "Dataset selector" step before the model selector; feature cards and status table rewritten to describe 3-dataset support, correctly attributing the app changes already made in the prior 2026-07-06 session
- **Slide 11 (Conclusion):** Goal 3/Goal 4 cards updated to mention the 216 model×fold×dataset pipeline count; "What's next" list dropped the stale "build Dataset 2/3" and "build backtest.py" bullets, replaced with real remaining work (extend `backtest.py` to Dataset 3's models, mitigate Dataset 2's p≫n problem)
- Updated Time Budget (Slide 9 grows to ~1:25, new total ~11:25, trim suggestions added) and Speaker Notes for slides 9-11 to match

### Verified end-to-end in a real browser (not just code review)
- Served the file via a temporary local `python -m http.server 8899` (stopped afterward) since the Chrome extension can't navigate to `file://` URLs directly
- Confirmed no console errors on load, and visually checked slides 9, 10, and 11 render correctly — all 4 new charts display, the `p≫n` HTML entity renders correctly, and the new Dataset selector flow diagram shows on slide 10

### Updated `presentation_outline.md` to mirror the HTML exactly (per the file's own "source of truth" convention)
- Added a new "What changed — 2026-07-06" changelog section (in addition to the existing slides 7-9 restructure changelog) documenting all 4 changes above
- Mirrored the Slide 9/10/11 content blocks, speaker notes, Time Budget, Key Numbers, and Charts Available sections to match the HTML

**Stopped at:** both `draft_final_presentation.html` and `presentation_outline.md` now correctly reflect Dataset 2/3 training + the multi-dataset Streamlit app; verified visually with no rendering issues. Deck total runtime is now ~11:25 (was ~10:50), with trim suggestions already written into the outline's Time Budget note.

**Next steps:**
1. Rehearse the deck at least once with the new Slide 9 content to confirm the ~1:25-over estimate is realistic and decide which trims (if any) from the Time Budget note to actually apply
2. `push.bat` once user wants to commit — updated `draft_final_presentation.html` / `presentation_outline.md`, plus everything else still sitting uncommitted from prior sessions (trained `.joblib` files, `model_comparison.csv`, `backtest.py`, dataset comparison report/scripts)
3. Consider updating `CLAUDE.md`'s stale "Not yet built" list (Dataset 2/3, `backtest.py`, multi-dataset Streamlit app are all done) — flagged across several sessions now, still not done since it's a project-instructions file the user may want to edit themselves

---

## 2026-07-06 — Updated Streamlit app to support Dataset 2 and Dataset 3 (previously hardcoded to Dataset 1 only)

**Branch:** branch_lee

**Done:**

### Found `src/app/app.py` was hardcoded to `dataset_basic_daily` even though Dataset 2 (90-day lookback) and Dataset 3 (technical indicators) were fully trained (12 models x 6 folds each, confirmed via `model_comparison.csv`'s `dataset` column and `models/trained/` filenames)
- `DATASET_FILES` dict only had one entry; `dataset_name` was a hardcoded string; the model-comparison table and metric lookup never filtered by dataset — selecting a different dataset was not possible in the UI at all

### Edited `src/app/app.py` (backed up to `.bak` first per project convention, removed after verifying the change works)
- Added `DATASET_FILES` entries for `dataset_90day_lookback` and `dataset_technical`, plus a `DATASET_LABELS` dict for display names ("Dataset 1 -- Basic Daily" / "Dataset 2 -- 90-Day Lookback" / "Dataset 3 -- Technical Indicators")
- Added a "Dataset" selectbox in the sidebar (above the existing Model/Fold selectors) — `load_dataset()`, `available_models()`, and `load_pipeline()` were already parameterized by `dataset_name`, so this was mostly wiring, not new logic
- Fixed the metrics lookup and the "All models -- comparison" table to filter `comparison` by `dataset == dataset_name` (previously showed the whole 216-row table across all 3 datasets undifferentiated, and the metric cards could silently pick up a fold-label collision from another dataset)
- Added a new "Dataset 1 vs 2 vs 3 -- comparison" section at the bottom rendering the 4 pre-built `dataset_comparison_*.png` charts from `scripts/generate_dataset_comparison_report.py` (accuracy/AUC/Sharpe/overfit-gap by dataset), with a caption pointing to the full `reports/dataset_comparison.html` narrative report

### Verified end-to-end in a real browser (not just code review)
- Launched `streamlit run src/app/app.py --server.headless true --server.port 8511`, confirmed HTTP 200 and no console errors
- Used Chrome automation to select each dataset from the new dropdown: Dataset 1 loaded correctly (Bagging_DT fold final: 58.2% acc), switching to Dataset 3 correctly reloaded the model list and metrics (Bagging_DT fold final: 82.0% acc, 0.897 AUC — matches `model_comparison.csv`), confirming the dataset switch actually re-triggers `load_dataset`/`available_models`/`load_pipeline` instead of silently reusing cached Dataset-1 state
- Scrolled to confirm the new dataset-comparison charts render without errors
- Stopped the test server afterward (killed the streamlit/python processes and confirmed the port's listener PID was already gone — stale TCP entry, not a leaked process)

**Stopped at:** Streamlit app now fully supports all 3 datasets. No other app features changed (feature importance, prediction chart, per-fold chart_files section all still work as before, just correctly scoped to whichever dataset is selected).

**Next steps:**
1. `push.bat` once user wants to commit — updated `src/app/app.py`, plus all the untracked `.joblib` files / `model_comparison.csv` updates / report files already sitting in git status from prior sessions (backtest.py, dataset_comparison report, etc. — still uncommitted per repo state at session start)
2. Presentation deck review (`presentation_outline_NEW.md` / `draft_final_presentation_NEW.html`) still pending user approval, carried over from 2026-07-04/05
3. Consider updating `CLAUDE.md`'s stale "Not yet built" list (Dataset 2/3, backtest.py, and now the multi-dataset Streamlit app are all done) — flagged in a prior session, still not done since it's a project-instructions file the user may want to edit themselves

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
