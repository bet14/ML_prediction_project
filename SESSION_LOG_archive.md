# Session Log — Archive

> Entries older than the 2 most recent sessions are moved here.
> Read this file when looking up history; no need to read regularly.

---

## 2026-07-05 23:22 — Built `src/evaluation/backtest.py` — the last missing item in `project_status.py`, now 100% (52/52)

**Branch:** branch_lee

**Done:**

### Built `src/evaluation/backtest.py` (new file)
- Stitches OOS predictions from the 6 walk-forward fold `.joblib` pipelines (already trained by `train.py`, no retraining here) into one continuous 2019–2024 equity curve — folds 1-5 (test years 2019-2023) + `final` (2024) are calendar-contiguous and non-overlapping, so concatenating by date gives a true continuous out-of-sample series instead of 6 disconnected snippets
- `log_return` is computed on the *stitched* close series itself (not per-fold like `train.py`'s `_compute_log_returns`), so the daily move across a fold boundary (e.g. Dec-31-2019 → Jan-01-2020) is captured instead of being zeroed out at every fold start — a small but real improvement over the per-fold sharpe already logged in `model_comparison.csv`
- Strategy: long GBP/USD (position=1) when the model predicts `Direction=1`, flat otherwise
- `--spread-pips` CLI flag charges a spread cost (in pips, converted to log-return scale via `pip_size / close`) on every position change — satisfies the spec's still-open checklist item ("Sensitivity analysis: 1–2 pip GBP/USD spread applied to cumulative P(t)")
- Reused `_annualised_sharpe` / `_max_drawdown` from `metrics.py` directly (not `compute_metrics`'s `y_pred`-masking path, which would incorrectly zero out the cost incurred on an exit day since `y_pred==0` on that day)
- Outputs: `reports/figures/equity_curve_<model>_<dataset>.png` (equity curve + drawdown, 2 stacked single-axis panels, no dual-axis), `reports/tables/backtest_<model>_<dataset>.csv` (per-day detail), `reports/tables/backtest_summary.csv` (upserted by `(dataset, model, spread_pips)` key, so different spread runs accumulate instead of overwriting)

### Verified end-to-end (not just code review)
- Ran `python src/evaluation/backtest.py --dataset dataset_basic_daily --models XGB HGB` (spread=0): XGB total return +3.6% vs buy&hold -1.3%, Sharpe 0.08; HGB +1.6% vs -1.3%, Sharpe 0.04
- Ran again with `--spread-pips 1.5` on XGB (669 trades over 6 years): total return flipped to **-4.1%** — confirms transaction costs erase XGB's edge at a realistic spread, exactly the kind of result this checklist item was meant to surface
- Opened `reports/figures/equity_curve_XGB_dataset_basic_daily.png` and visually confirmed correct rendering (equity panel + drawdown panel, legend, no axis issues)
- Re-ran `python scripts/project_status.py` → **52/52 (100%)**, up from 51/52 — `backtest.py` was the only remaining gap

### Updated `map.md` with the new `backtest.py` entry under "Model & Evaluation" (per project convention)

**Stopped at:** `backtest.py` built, tested, and producing correct output for Dataset 1 (XGB/HGB). Have not yet run it against Dataset 2/3 or other models (RF, LGBM, CatBoost, etc.) — only the 2 strongest Dataset-1 models from `model_comparison.csv`'s final-fold Sharpe ranking were backtested this session. `CLAUDE.md`'s "Not yet built" list still says `backtest.py` is missing — left untouched since it's a project-instructions file the user may want to review/edit themselves (also noticed that section is stale in other ways, e.g. Dataset 2/3 already built — out of scope for this session to fix).

**Next steps:**
1. Decide which additional (model, dataset) combos are worth backtesting — e.g. best Dataset 3 tree/boosting models, even though their final-fold Sharpe was negative per last session's analysis (worth seeing the actual equity curve, not just the summary metric)
2. Consider updating `CLAUDE.md`'s stale "Not yet built" list (backtest.py now done; Dataset 2/3 already built) — flagged, not yet done
3. `push.bat` once user wants to commit — new `backtest.py`, `reports/figures/equity_curve_*.png`, `reports/tables/backtest_*.csv`, `reports/tables/backtest_summary.csv`, plus the `map.md` update
4. Presentation deck review (`presentation_outline_NEW.md` / `draft_final_presentation_NEW.html`) still pending user approval, carried over from 2026-07-04 — could now cite the spread-sensitivity finding (XGB profitable gross, unprofitable net of realistic spread) as a methodology/limitations point

---

## 2026-07-05 (2) — Analyzed full 12-model Dataset 1/2/3 results; built `scripts/plot_dataset_comparison.py` + `scripts/generate_dataset_comparison_report.py` → `reports/dataset_comparison.html`

**Branch:** branch_lee

**Done:**

### Analyzed `reports/tables/model_comparison.csv` (216 rows, full 12-model x 6-fold x 3-dataset grid) to resolve last session's open question
- Pivoted CV-mean (folds 1-5) accuracy/AUC per model x dataset — confirms **Dataset 2's near-random pattern (flagged for LR/LGBM two sessions ago) holds for all 12 models**, including every tree/boosting model (RF/XGB/CatBoost/HGB/ET/Bagging_DT all in the 0.50-0.56 accuracy range, no better than LR/LGBM). Tree models do not handle Dataset 2's p>>n (9,110 cols vs ~2,700 rows) any better than linear ones here — decision: **accept as a negative result**, no mitigation attempted this session (matches `References/DATASET_2_3_PLAN.md`'s own suggested path when full-fold evidence confirms the pattern).
- **Dataset 3 confirmed strong and consistent** for every tree/boosting model (0.80-0.85 CV accuracy, 0.87-0.92 AUC — Bagging_DT, CatBoost, ET, HGB, LGBM, RF, XGB all in this band), matching the paper's (Guyard & Deriaz 2024) finding that technical indicators help gradient-boosting specifically.
- **New nuance not previously documented:** linear models (LR, Bagging_LR) actually score *lower* on Dataset 3 (~0.64 CV accuracy) than on Dataset 1 (~0.74) — likely because the 12 indicator families repeat the same window sizes (3/7/14/30/60/90), producing heavy collinearity that hurts an unregularised linear decision boundary. DT and KNN stay the weakest models on all 3 datasets.

### Built `scripts/plot_dataset_comparison.py` (new file, follows `plot_model_comparison.py` conventions)
- 4 grouped-bar charts (3 datasets x 12 models each) → `reports/figures/dataset_comparison_{accuracy,auc,sharpe,overfit_gap}.png`
- Verified visually — accuracy chart clearly shows Dataset 2 flat-lining near the 50% reference line across every model while Dataset 3 towers over Dataset 1 for tree/boosting models.

### Built `scripts/generate_dataset_comparison_report.py` (new file, follows `generate_eda_report.py`'s self-contained-HTML pattern)
- Embeds the 4 charts as base64 + one per-model metrics table per dataset (Acc/AUC/F1/Sharpe/MaxDD, CV vs Final, overfit gap column flagged red if >5pp) + a "Key Findings" narrative section
- Output: `reports/dataset_comparison.html` (407 KB, self-contained) — opened in browser to confirm rendering

### Updated `map.md` (English, per project convention) with the 2 new script entries under "Model & Evaluation"

### Explained the two statistical concepts behind the report's Key Findings, in Vietnamese, to the user (Q&A, no code changed)
- **p >> n** (Dataset 2's problem): p = feature count, n = row count; at p/n ≈ 3.4x, the design matrix is rank-deficient for LR (infinitely many solutions fit the training rows, including ones that fit noise), which is why `sag`/`lbfgs` throws `ConvergenceWarning` and accuracy stays ~50% even on the fold with the most training rows. Tree/ensemble models tolerate high p better in theory (pick one best feature per split, no matrix inversion) but still landed at 0.50-0.56 accuracy here — confirms the signal itself is too diluted across 9,110 lag columns, not just an algorithm limitation.
- **Multicollinearity** (Dataset 3's problem for linear models): the 12 indicator families all reuse the same window set N ∈ {3,7,14,30,60,90} per instrument (e.g. `SMA_7` and `SMA_14` over the same price series are highly correlated), so many columns carry near-duplicate information. This destabilizes LR's per-column coefficients (variance inflation) but barely affects trees, since a tree just picks whichever near-duplicate column split is best and ignores the rest — matches the observed LR/Bagging_LR regression on Dataset 3 (~0.64 acc) vs their Dataset 1 result (~0.74 acc).
- Worth reusing this explanation verbatim if the presentation deck needs a methodology slide justifying why Dataset 2 was accepted as a negative result and why Dataset 3 helps trees but not linear models.

**Stopped at:** Dataset 2 vs 3 comparison report is done and reviewed. `project_status.py` still shows 51/52 (98%) — `reports/figures` check is a generic dir-nonempty check so the 4 new PNGs didn't need a new checklist item.

**Next steps:**
1. `push.bat` once user wants to commit — 120+ new `.joblib` files from last session, updated `model_comparison.csv`, the 2 new report scripts + their outputs, plus the `train.py`/`model_registry.py` bug fixes from last session (`.bak` files can be removed once confirmed good, or kept until after push)
2. Presentation deck review (`presentation_outline_NEW.md` / `draft_final_presentation_NEW.html`) still pending user approval, carried over from 2026-07-04 — worth folding in the Dataset 2/3 findings above if the deck covers Goal 3 results
3. `src/evaluation/backtest.py` remains the only missing item in `project_status.py` (49/52 -> 51/52 after this session's additions were auto-counted under existing dir checks)
4. No further work planned on Dataset 2 unless user wants to revisit the plan's mitigation options (shorter lookback / Bayesian feature selection) — currently treated as a settled negative result

---

## 2026-07-05 21:28 — Extended Dataset 2 and Dataset 3 to the full 12-model registry (10 remaining models each, all 6 folds); fixed two training-pipeline bugs found along the way

**Branch:** branch_lee

**Done:**

### Ran `src/models/train.py --skip-existing` for the 10 fast models not yet covered on each new dataset
- Dataset 2 (`dataset_90day_lookback`): `RF XGB MLP KNN DT ET HGB CatBoost Bagging_DT Bagging_LR` (LR/LGBM already done last session)
- Dataset 3 (`dataset_technical`): `LR RF MLP KNN DT ET HGB CatBoost Bagging_DT Bagging_LR` (XGB/LGBM already done last session)
- Both runs launched in background (`run_in_background`); the Dataset 2 run got killed partway twice — investigated rather than just retried blindly (see bugs below)

### Bug 1 — `train.py` only wrote `model_comparison.csv` once, at the very end of the whole batch
- Consequence: when the Dataset 2 background run was killed (environment appears to cap background bash tasks around ~10 min), 9 of the 10 models had already finished training (`.joblib` files existed) but **none of their metrics were logged** — only 1 row (`RF` fold 1, from an earlier manual timing test) had survived
- Fix: added `_upsert_record()` to `src/models/train.py` — writes/updates one CSV row immediately after each fold finishes, instead of batching until the end. Backed up first (`train.py.bak`, per CLAUDE.md rule)
- Recovered the lost metrics without retraining: wrote a one-off backfill script (scratchpad, not committed) that loads each existing `.joblib`, re-predicts on its fold's test set, computes metrics, and upserts — recovered 53 rows across 9 models with zero retraining cost

### Bug 2 — `Bagging_LR`'s base `LogisticRegression` used `solver="saga"`, ~20x slower than needed on wide feature sets
- Dataset 2 has 9,109 feature columns; a single `saga` fit took 170-300s (matches last session's plain `LR` timing), and `Bagging_LR` fits 20 of these per fold → 500-900s/fold, exceeding the environment's background-task time cap
- Verified before changing anything: timed a single `LogisticRegression(solver="lbfgs")` fit on the same fold-5 data — **12.9s vs. ~250s** for `saga`, same L2-penalty optimum (this function never uses the L1 option, so `lbfgs` is a safe drop-in)
- Fix: `src/models/model_registry.py` `_build_bagging_lr` now uses `solver="lbfgs"`. Backed up first (`model_registry.py.bak`). Retrained all 6 `Bagging_LR` folds on Dataset 2 for consistency (not just the missing ones) — each fold now finishes in 40-185s instead of 500s+

### Final state — verified via `scripts/project_status.py`
- **216 trained models** (12 models × 6 folds × 3 datasets) and **216 rows** in `reports/tables/model_comparison.csv` — full parity across Dataset 1, 2, and 3
- Project status: 51/52 items `[OK]` (98%) — only remaining gap is `src/evaluation/backtest.py`, unrelated to this session's scope

**Stopped at:** all 3 datasets now have the full 12-model × 6-fold registry trained and logged. No analysis done yet on the new models' results for Dataset 2/3 (e.g., does Dataset 2's near-random pattern from LR/LGBM last session hold for tree-based models too, or was it specific to those 2 models).

**Next steps:**
1. Analyze the newly-completed Dataset 2/3 results in `model_comparison.csv` — does the p≫n weak-signal problem flagged for Dataset 2 (LR/LGBM) also affect RF/XGB/CatBoost/etc., or do tree-based models handle 9,109 columns better?
2. Decide Dataset 2's fate (mitigate vs. accept as negative result) now that full evidence exists across all 12 models, not just 2
3. Build `scripts/plot_dataset_comparison.py` + `scripts/generate_dataset_comparison_report.py` → `reports/dataset_comparison.html` (Dataset 1 vs 2 vs 3), per `References/DATASET_2_3_PLAN.md` section 4 — still not started
4. `push.bat` once user wants to commit — 120 new `.joblib` files, updated `model_comparison.csv`, plus the `train.py`/`model_registry.py` bug fixes (`.bak` files can be removed once changes are confirmed good, or kept until after push)
5. Presentation deck review (`presentation_outline_NEW.md` / `draft_final_presentation_NEW.html`) still pending user approval, carried over from 2026-07-04

---

## 2026-07-05 00:20 — Full 6-fold training completed for Dataset 2 and Dataset 3 (remaining folds), confirming Dataset 2's weak-signal pattern holds project-wide

**Branch:** branch_lee

**Done:**

### Ran `src/models/train.py --skip-existing` (no `--fold` filter) for both new datasets, same 2 models per dataset as last session's fold-1 smoke test
- Dataset 2 (`dataset_90day_lookback`): `--models LR LGBM` — ran in background (task `bh3burvov`), fold 1 skipped (already existed), folds 2/3/4/5/final trained
- Dataset 3 (`dataset_technical`): `--models XGB LGBM` — ran in background in parallel (task `bgy22rlnh`), fold 1 skipped, folds 2/3/4/5/final trained
- `--skip-existing` flag did exactly what was needed here — no custom fold-list scripting required, `train.py` already supported resuming a partial dataset×model run
- Results merged cleanly into `reports/tables/model_comparison.csv`: 24 new rows, verified no duplicate `(dataset, model, fold)` keys after merge

### Results — full 6-fold picture (fold 1 from last session + folds 2-final from this session)
| Dataset | Model | Accuracy range | AUC-ROC range | Notes |
|---|---|---:|---:|---|
| Dataset 3 (technical) | XGB | 0.61–0.84 | 0.64–0.90 | Fold 1 weakest (smallest train set), folds 2-final all 0.79-0.84 acc |
| Dataset 3 (technical) | LGBM | 0.51–0.83 | 0.51–0.90 | Same pattern as XGB |
| Dataset 2 (90-day) | LR | 0.48–0.57 | 0.51–0.60 | Near-random on **every** fold, not just fold 1; `sag` solver hit `ConvergenceWarning` on all 5 remaining folds; 170-300s/fold (slowest model by far) |
| Dataset 2 (90-day) | LGBM | 0.48–0.61 | 0.49–0.64 | Also near-random on every fold, no improvement trend as training window grows |

- **Resolves last session's open question:** the "Next steps" list asked whether fold 1's weak Dataset 2 signal was just the worst-case p≫n scenario (smallest training window) or a persistent problem. Now answered — **it's persistent across all 6 folds**, including the final fold with the largest training window (~2,600 rows vs. 9,110 cols). This confirms the plan doc's flagged p≫n risk (`References/DATASET_2_3_PLAN.md`, "Rủi ro" section) is real, not a fold-1 artifact.
- **Dataset 3 confirmed strong and consistent** across all folds for both gradient-boosting models — matches the paper's finding (Guyard & Deriaz 2024) that technical indicators help boosting models specifically. Only XGB/LGBM tested so far, not the full 12-model registry.

**Stopped at:** both datasets now have full 6-fold results for their 2 smoke-test models each. No decision made yet on Dataset 2's fate (mitigate vs. abandon), and Dataset 3 has not yet been extended to the full 12-model registry.

**Next steps:**
1. Decide Dataset 2's path: try a mitigation from the plan's already-documented options (Bayesian feature selection, or shorter lookback like 30/60 days instead of 90) vs. accepting it as a negative result and moving on — full 6-fold evidence is now in hand to make this call, unlike last session
2. Dataset 3 is safe to extend to the full 12-model registry (`References/DATASET_2_3_PLAN.md` section 3 has the exact command) whenever wanted
3. Build `scripts/plot_dataset_comparison.py` + `scripts/generate_dataset_comparison_report.py` → `reports/dataset_comparison.html` (Dataset 1 vs 2 vs 3), per plan section 4 — not started yet
4. `push.bat` once user wants to commit — new `.joblib` files (20 new files across both datasets) + updated `model_comparison.csv`; large dataset CSVs remain gitignored
5. Presentation deck review (`presentation_outline_NEW.md` / `draft_final_presentation_NEW.html`) still pending user approval, carried over from 2026-07-04

---

## 2026-07-04 (4) — Smoke-tested fold 0 on Dataset 2 and Dataset 3 with the plan's recommended models

**Branch:** branch_lee

**Done:**

### Ran `src/models/train.py --fold 0` for the 2 models the plan recommended per dataset (`References/DATASET_2_3_PLAN.md`, "Nếu chỉ train thử 2 model/dataset trước")
- Dataset 3 (`dataset_technical`, 1,538 cols): `--models XGB LGBM` — ran in foreground, both finished in 7.9s/9.0s
- Dataset 2 (`dataset_90day_lookback`, 9,110 cols): `--models LR LGBM` — ran in background (`run_in_background`, task id `b42zubnai`) since LR on 9,110 cols was expected to be slow; polled via `TaskOutput` until completion
- Results auto-merged into `reports/tables/model_comparison.csv` by `train.py`'s existing key-based upsert (dataset+model+fold) — no code changes needed

### Results — fold 1 (train 2014-2018, test 2019), compared against existing Dataset 1 baseline pulled from `model_comparison.csv`
| Dataset | Model | Accuracy | AUC-ROC | Sharpe proxy | Time |
|---|---|---:|---:|---:|---:|
| Dataset 1 (baseline) | XGB | 0.605 | 0.638 | 0.739 | -- |
| Dataset 1 (baseline) | LGBM | 0.598 | 0.649 | 0.543 | -- |
| Dataset 1 (baseline) | LR | 0.701 | 0.807 | 0.300 | -- |
| **Dataset 3** | XGB | **0.762** | **0.840** | -0.176 | 7.9s |
| **Dataset 3** | LGBM | **0.766** | **0.837** | 0.129 | 9.0s |
| **Dataset 2** | LR | 0.513 | 0.528 | -0.189 | 170.6s |
| **Dataset 2** | LGBM | 0.510 | 0.510 | 1.041 | 38.9s |

- **Dataset 3 (technical indicators): clear improvement** for both XGB and LGBM over Dataset 1 (+0.16/+0.17 accuracy, +0.20/+0.19 AUC) — matches the paper's finding that gradient-boosting benefits most from domain-knowledge technical features (`References/DATASET_2_3_PLAN.md` Q&A section on this). Fast to train, no concerns raised for a full 6-fold run.
- **Dataset 2 (90-day lookback): near-random accuracy (~0.51) for both models**, actually *worse* than the Dataset 1 baseline. LR threw a `ConvergenceWarning` (`sag` solver hit `max_iter` without converging) and took 170.6s vs LGBM's 38.9s for the same fold. This matches the p≫n risk the plan doc already flagged (fold 1 has the smallest training set, ~1,000 rows, against 9,110 columns) -- not treated as a bug, but as the predicted risk materializing.
- Explicitly noted to the user: fold 1 is the *most extreme* p≫n case among the 6 folds (smallest training window); this single result doesn't prove Dataset 2 is unusable overall since later folds have more training rows -- flagged as inconclusive on 1 fold, not a final verdict.

**Stopped at:** fold-0 smoke test done for both new datasets; no full 6-fold run yet, no decision made yet on whether/how to address Dataset 2's fold-1 weak signal.

**Next steps:**
1. Decide whether to run Dataset 2's remaining folds (2-final) before judging it further, since fold 1 is the worst-case p≫n scenario -- later folds (more training rows) may behave differently
2. If Dataset 2 stays weak across all folds after a full run, consider the plan's already-documented mitigation options (no date-encoding lag already applied; next options would be shorter lookback like 30/60 days, or feature selection via Bayesian search) -- not to be done pre-emptively without full-fold evidence first
3. Dataset 3 looks safe to proceed to a full 6-fold x 12-model run (per plan section 3's commands) whenever user wants
4. Resolve Q3 (first full training run's hyperparameters -- defaults vs. Bayesian search) before the full run, per plan section 3
5. `push.bat` once user wants to commit -- remember `dataset_90day_lookback.csv`/`dataset_technical.csv` are now gitignored (too large for GitHub), only code + `model_comparison.csv` need pushing

---

## 2026-07-04 (3) — Built Dataset 2 (90-Day Lookback) and Dataset 3 (Technical Indicators), per the plan's already-resolved decisions

**Branch:** branch_lee

**Done:**

### Read `References/DATASET_2_3_PLAN.md` + `SESSION_LOG.md` to resume — all Q1/Q2/Q4 decisions were already resolved last session, went straight to coding per its "Next steps" list
- Verified against real files before coding (not from memory): `dataset_basic_daily.csv` has 111 cols (110 + `date` index), 9 date-encoding cols confirmed by name, `forex_panel.csv`/`equity_panel.csv` column layout confirmed, `ta` function signatures re-verified (`stoch`/`stoch_signal`/`williams_r`/`macd`/`macd_signal` params), and pulled the exact per-family N-value lists from `References/GBPUSD_ML_data_requirements_spec.md` section 2.4 (the plan doc only had family *counts*, not the literal N lists)

### Created `src/features/technical_indicators.py` (new file)
- `compute_technical_indicators(df, has_volume)` — 12 of 16 spec families via the `ta` library (families #5 Momentum, #10 A/D Oscillator, #13 Disparity, #14 OSCP dropped entirely, per last session's Q4 decision)
- Verified output column count with a synthetic OHLCV DataFrame before wiring into the build script: 60 cols (forex, no volume), 72 cols (equity, with volume) — exact match to the plan's revised estimate
- Noted a spec-literal choice for Stochastic %D: spec says "%D(N) = N-day mean of %K(N)", so `stoch_signal(..., window=n, smooth_window=n)` uses the same N for both, not `ta`'s default `smooth_window=3`

### Created `src/features/build_dataset_technical.py` (new file) → ran it successfully
- Loads `dataset_basic_daily.csv` + both interim panels, computes indicators per instrument (13 forex + 9 equity = 22), prefixes columns, merges, drops first 90 rows (Q2)
- Output: `data/processed/dataset_technical.csv` — **2,778 rows × 1,538 cols** (2014-05-08 → 2024-12-30), exact match to plan estimate, 0.08% NaN overall

### Created `src/features/build_dataset_90day.py` (new file) → ran it successfully
- Loads `dataset_basic_daily.csv`, lags all 100 lag-eligible cols (excludes `Direction` + 9 date-encoding cols per Q1) from lag1..lag90, drops first 90 rows (Q2)
- Output: `data/processed/dataset_90day_lookback.csv` — **2,778 rows × 9,110 cols** (2014-05-08 → 2024-12-30), exact match to plan estimate, 0.53% NaN overall
- Investigated the NaN before accepting it: traced to `USA_cpi_yoy` having 300 pre-existing NaN rows in Dataset 1 itself (YoY needs 12 months of prior data) — inherited via lagging, not a bug introduced by this script

### Verified both new datasets are drop-in compatible with the existing training pipeline (no train.py/bayesian_search.py changes needed, as the plan predicted)
- `get_folds()` from `walk_forward_cv.py` runs cleanly on both — 6 folds each, final fold test = 2024-01-01 → 2024-12-30, same as Dataset 1
- Did **not** run `train.py` — user said "tạo dataset trước, train sau" (dataset-build only this round; Q3 hyperparameter choice still deferred to the train session)

### Updated `map.md` (English) — replaced both "NOT BUILT YET" lines with the real commands/output paths
### Updated `scripts/project_status.py` (backed up first → `project_status.py.bak`, per CLAUDE.md rule)
- `cl3_10` checklist label was stale ("All 16 technical indicator families...") — corrected to state 12/16 + which 4 were dropped and why, so the checklist stays truthful
- Re-ran `project_status.py` after editing to confirm it still works: **98% (51/52)**, Dataset 2 and Dataset 3 both now show `[OK]`

**Stopped at:** both datasets built and verified compatible with the training pipeline; **no training run yet** (by design, per user's request this round).

**Next steps:**
1. Resolve Q3 (first training run's hyperparameters) when starting the train session — plan's own recommendation: use `model_registry.py` defaults first for a fast baseline, save Bayesian search for after a first look at results
2. Run `python src/models/train.py --dataset dataset_technical --fold 0 --models LGBM` (or similar single-model/single-fold smoke test) before committing to full 6-fold × 12-model runs — Dataset 2 (9,110 cols) will be markedly slower than Dataset 1 (110 cols)
3. Full training commands are already written out in `References/DATASET_2_3_PLAN.md` section "3. Train 12 model trên 2 dataset mới"
4. After training: build `scripts/plot_dataset_comparison.py` + `scripts/generate_dataset_comparison_report.py` → `reports/dataset_comparison.html` (Dataset 1 vs 2 vs 3 comparison), per the plan's section 4
5. `push.bat` once user wants to commit this session's new files (2 new datasets are large CSVs — confirm before adding to git if size is a concern)

---

## 2026-07-04 (2) — Resolved Dataset 2/3 plan's 4 open questions with user, verified `ta` library coverage, updated plan doc; no code written yet

**Branch:** branch_lee

**Done:**

### Read `References/DATASET_2_3_PLAN.md` end to end with user (4 open questions Q1-Q4 at bottom)
- User's opening request already answered part of Q4 implicitly by restating the plan's own default column-count scenario for Dataset 3 (equity keeps volume, forex naturally has none, ≈1.978 cols)

### Asked user to resolve Q1/Q2/Q4 via AskUserQuestion (Q3 deferred — user said "tạo dataset trước, train sau")
- **Q1 (lag date-encoding in Dataset 2):** user picked the plan's recommended option — do NOT lag the 9 date-encoding columns. Dataset 2 ≈ 9,110 cols.
- **Q2 (first 90 rows missing lookback):** user picked the plan's recommended option — drop the first 90 rows for both Dataset 2 and 3 (~2,778 rows remain).
- **Q4 (how to implement the 16 technical-indicator families):** user picked the opposite of the plan's recommendation — use the `ta` library instead of hand-writing every formula from the spec.

### Verified `ta` library's actual API before accepting Q4's answer (did not assume from memory)
- Ran `python -c "import ta.trend, ta.momentum, ta.volume; ..."` in the project venv to list real available functions/signatures
- Found: 12/16 spec families have a direct `ta` function with a tunable `window=` param (SMA/WMA close+volume, Stochastic %K/%D, RSI, Williams %R, CCI, ROC, MACD, MACD signal) — these are safe to use as-is
- Found: 4/16 families have **no equivalent in `ta`** — Momentum N-day (#5), A/D Oscillator (#10), Disparity N-day (#13), OSCP N/M (#14). `ta.volume.acc_dist_index` looks like a name match for #10 but is actually Chaikin's A/D Line (cumulative money flow), a different formula from the paper's Williams A/D Oscillator — flagged this distinction explicitly to the user before they decided
- Asked a follow-up clarifying question (interrupted once by user for a plain clarification, then re-asked): user confirmed **drop all 4 missing families entirely, do not hand-write substitutes** — accepts the resulting column-count drop from ~1,978 to ~1,538 for Dataset 3 (Equity 9×72=648, Forex 13×60=780, +110 Dataset 1 cols)

### Updated `References/DATASET_2_3_PLAN.md` with all resolved decisions (no code changes yet)
- Added a "QUYẾT ĐỊNH ĐÃ CHỐT — 2026-07-04" section right after the header recording Q1/Q2/Q4 answers, the verified `ta` function table for the 12 usable families, and the revised Dataset 3 column-count table (old 16-family/1,978-col plan vs new 12-family/1,538-col plan)
- Rewrote the file's final "Next steps" section into a concrete 6-step build order reflecting the decisions (build `technical_indicators.py` → `build_dataset_technical.py` → `build_dataset_90day.py` → update `map.md` → stop, no training this round → Q3 deferred to the train session)

**Stopped at:** all 3 blocking questions (Q1/Q2/Q4) resolved and written into the plan doc; **no code written yet** — user needs to shut down the machine. Next session should start coding directly per the plan's updated "Next steps", no need to re-ask Q1/Q2/Q4.

**Next steps:**
1. `src/features/technical_indicators.py` — write functions using `ta` for the 12 available families (see function table in the plan doc), skip families #5/#10/#13/#14 entirely
2. `src/features/build_dataset_technical.py` — load `forex_panel.csv` + `equity_panel.csv`, apply step 1 per instrument, merge with `dataset_basic_daily.csv`, drop first 90 rows, output `data/processed/dataset_technical.csv` (~1,538 cols)
3. `src/features/build_dataset_90day.py` — lag every Dataset 1 feature except the 9 date-encoding cols and `Direction`, lag1-lag90, drop first 90 rows, output `data/processed/dataset_90day_lookback.csv` (~9,110 cols)
4. Update `map.md` (English) — replace the 2 "NOT BUILT YET" lines with the real file names
5. Do NOT train yet — user explicitly wants datasets built first, training later (Q3 still open, resolve when that session starts)

---

## 2026-07-04 — Reviewed training/metrics/model section for clarity; drafted restructured slides 7-9 as _NEW files for review

**Branch:** branch_lee

**Done:**

### Read PROJECT_GUIDE.md + code + training results, cross-checked against presentation_outline.md / draft_final_presentation.html
- Re-verified slide 8's numbers by hand against `reports/tables/model_comparison.csv` (LR CV 73.69%→final 65.52%, gap −8.2pp; Bagging_LR 73.70%→67.43%, gap −6.3pp; CatBoost 58.74%→63.22%; XGB 62.34%→61.30%) — all match, no fabricated numbers
- Read `bayesian_search.py`, `train.py`, `walk_forward_cv.py`, `metrics.py`, `plot_roc_pr_curves.py`, `app.py` directly to check the *mechanics* behind the training/metrics narrative, not just what the outline claims

### Found 6 clarity/logic gaps in the training-metrics-model section (old slides 7-9)
1. No slide anywhere defines Accuracy/F1-macro/AUC-ROC/Sharpe proxy/Max drawdown or gives good/bad thresholds — `PROJECT_GUIDE.md` (lines 237-294) has this glossary but it never made it into the deck
2. `PROJECT_GUIDE.md`'s own caveat that CV accuracy is optimistic (folds 1-4 double as both search-tuning data and CV-mean data) was never stated in the deck — only "overfitting" was said, not the mechanism
3. **New finding:** Bagging_LR's final AUC-ROC (0.869) crosses the project's own ">0.80 = investigate for leakage" threshold — deck only said "consistent with overfitting flag", never acknowledged the threshold crossing explicitly (plausible explanation: its search found `C=5.50`, very weak regularization)
4. Bayesian-search deep-dive ("why Bayesian over Grid/Random", "what results showed") sat in slide 9's collapsed extra material, disconnected from slide 8 where Bayesian search is introduced
5. "Pipeline architecture" (preprocessing steps) was explained at the top of slide 9 (Results) — *after* slides 7-8 had already used the word "fit" repeatedly
6. Slide 8's flow diagram said "Refit on all 6 folds", reads like one combined model; `train.py` actually fits 6 independent pipelines sharing one fixed `best_params`

### Created `presentation_outline_NEW.md` and `reports/draft_final_presentation_NEW.html` (proposed fix, not applied to the main files)
- Backed up originals first: `presentation_outline.md.bak`, `reports/draft_final_presentation.html.bak`
- Slide 7 renamed "Model Pipeline, Metrics & Walk-Forward CV" — pipeline architecture moved here from slide 9, new "metrics we'll cite" decoder table added, CV diagram unchanged
- Slide 8: fixed the "refit" wording, added CV-optimism + C=5.50 explanation to the bias-variance box, consolidated Bayesian-search deep-dive here (moved from slide 9)
- Slide 9: pipeline architecture and Bayesian-search extra material removed (relocated, not duplicated); "Model status" is now its own box; fixed a pre-existing wording bug ("see the next slide" → "see the previous slide", since training already comes *before* results); added the AUC-threshold acknowledgment to chart 4's caption
- Verified all 3 changed slides render correctly via a temporary local `python -m http.server` + Claude-in-Chrome screenshots (stopped afterward)
- Raw time estimate for the new slides 7-9 comes to ~10:15 (+15s over the 10:00 target) — outline's Time Budget section documents the trim options (shorten slide 8's 12-model narration, or cut 1 bullet from slide 9's open-issues lists)

**Stopped at:** `_NEW` files created and visually verified, **not yet applied** to `presentation_outline.md` / `reports/draft_final_presentation.html` — waiting on user review.

**Next steps:**
1. User reviews `presentation_outline_NEW.md` and `reports/draft_final_presentation_NEW.html` (open directly in a browser or via local server)
2. If approved: replace the main files with the `_NEW` versions (and remove the `.bak`/`_NEW` files, or keep `.bak` until after `push.bat`)
3. If changes needed: iterate on the `_NEW` files directly, no need to re-read all the training code again — this entry + the `_NEW` files carry full context
4. Once finalized, `push.bat` to commit
5. Resume Dataset 2/3 (90-day lookback / technical indicators) work — still not started, carried over from earlier sessions

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
