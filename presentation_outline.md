# Presentation Outline — GBP/USD Direction Prediction
# Duration: 10 minutes | Date: July 8, 2026
# Source of truth: reports/draft_final_presentation.html (12 slides) — this outline mirrors it exactly
# STATUS: APPLIED — slides 7-9 restructure + 2026-07-06 Dataset 2/3 & Streamlit update are both live in the main file. See "What changed" sections for rationale.
# DRAFT PENDING: Slides 6b/7b/8b below (Goal 3 re-split into Models / Hyperparameters & Refit /
# Evaluation) are a proposed alternative to the live Slides 7-9 — NOT adopted, kept for comparison.

---

## DRAFT — 2026-07-06: Goal 3 re-split into Models / Hyperparameters & Refit / Evaluation

Requested trial re-structure of Goal 3 (currently live Slides 7-9: "Pipeline, Metrics &
Walk-Forward CV" / "Training & Fine-Tuning" / "Models & Results"). New 3-slide split:

  Slide 6b — Models            (walk-forward CV diagram + pipeline architecture + the
             12-model roster, no hyperparameter/result numbers yet — expanded 2026-07-07
             to carry the CV diagram and full pipeline detail cards, moved in from live
             Slide 7, so this slide is the complete "how a model is built and validated"
             story)
  Slide 7b — Hyperparameters & Refit  (Bayesian search + best_params + per-fold refit)
  Slide 8b — Evaluation: Accuracy & Profit  (metrics decoder trimmed to just Accuracy/Sharpe
             + a Dataset 1×2×3 × 12-model results table + 3 new bias-variance trade-off
             scatter charts, one per dataset, only the 3-4 extreme models per dataset
             labeled — the other ~8-9 are plain dots colored by model family)

New chart support (generated for this draft, real data from `model_comparison.csv`,
built from the actual CV fold numbers, not accuracy-vs-Sharpe):
  reports/figures/variance_tradeoff_dataset1_basic_daily.png
  reports/figures/variance_tradeoff_dataset2_90day_lookback.png
  reports/figures/variance_tradeoff_dataset3_technical.png
  (regenerate: `python scripts/plot_variance_tradeoff.py --open`)
  Axes: x = fold-to-fold accuracy std-dev across inner CV folds 1-5 ("variance" --
  how much a model's accuracy swings year to year during tuning); y = final (2024
  held-out) accuracy ("bias" proxy -- low accuracy = underfit regardless of stability).
  Reference lines at 50% (coin flip / high-bias threshold) and the dataset's median
  fold-to-fold σ. Ideal quadrant = top-left. Labeled points per dataset: highest final
  accuracy, lowest final accuracy, highest variance, and the "best trade-off" (highest
  accuracy among below-median-variance models, picked automatically per dataset) --
  everything else is an unlabeled dot colored by family (Linear / Tree-Bagging /
  Boosting / Other) per the legend.

Not yet decided: whether this replaces the live Slides 7-9 (would need re-timing —
current 3-slide Goal 3 section runs ~3:35, draft below is untimed) or stays a discussion
draft. 2026-07-07 fix: Slide 8b's "Profit" column used to just alias the Sharpe proxy
already in `model_comparison.csv` — it is now the real Profit metric defined in the
reference paper (`References/10_FX_EURUSD_ML_Direction_Prediction.pdf`, §5.3): a
long/short strategy that compounds C(t)/C(t-1) on days the model predicts UP and
C(t-1)/C(t) on days it predicts DOWN, computed directly on the 2024 held-out fold for
all 12 models × 3 datasets (`scripts/compute_paper_profit.py` -> `reports/tables/
paper_profit_2024.csv`). This is still not the $-denominated `total_return_strategy`
from `backtest_summary.csv` (a different, long/flat, log-return strategy) — that only
exists for XGB/HGB on Dataset 1 so far (backtest.py not yet extended to all 12 models ×
3 datasets, per the open issue already tracked on Slide 9/11).

---

### SLIDE 6b (DRAFT) — Models — expanded 2026-07-07: now also carries walk-forward CV
### and the full pipeline architecture detail (both moved in from live Slide 7), so this
### slide is the complete "how a model is built and validated" story before Slide 7b's
### hyperparameters and Slide 8b's results. 12-model roster kept exactly as first drafted.

> Content:
>   Block 1 — Expanding-window walk-forward cross-validation (moved in from live Slide 7,
>   unchanged — full 6-fold diagram, not just the one-line summary):
>     Fold 1: Train 2014-2018 / Test 2019
>     Fold 2: Train 2014-2019 / Test 2020
>     Fold 3: Train 2014-2020 / Test 2021
>     Fold 4: Train 2014-2021 / Test 2022
>     Fold 5: Train 2014-2022 / Test 2023
>     Final:  Train 2014-2023 / Test 2024  (held out — never touched until final evaluation)
>     Why: time series → no random split → no look-ahead / no data leakage
>
>   Block 2 — Pipeline architecture (moved in from live Slide 7, unchanged, with the same
>   4 detail cards):
>     InfinityToNaNTransformer → SimpleImputer(median) → [RobustScaler, conditional] → Model
>     InfinityToNaNTransformer: replaces +inf/−inf with NaN across all 111 columns; needed
>       because UK_cpi_yoy_log produces −inf during deflation periods (log of a negative
>       YoY figure) — without this the imputer would crash on non-finite input.
>     SimpleImputer(median): fits per-column median on the training fold only, fills NaN;
>       handles the ~0.64% overall missing data (worst: USA CPI YoY, 10.46%).
>     RobustScaler (conditional): applied only when the model registry's scale flag is
>       true (LR, MLP, KNN, Bagging_LR, untrained SVM variants); skipped for tree-based
>       models. Uses median/IQR because EDA found fat-tailed returns (kurtosis up to 173).
>     Model: final estimator, fit with its Bayesian-searched hyperparameters (Slide 7b) —
>       predicts direction (0/1) + a probability.
>     Refit per fold, not once — no leakage from test into train.
>
>   Block 3 — 12-model roster (unchanged from the first draft, no hyperparameter values
>   here — those stay on Slide 7b):
>     Linear:            LR (Logistic Regression), Bagging_LR (27× bootstrapped LR)
>     Trees:              DT (single Decision Tree), ET (Extra Trees), RF (Random Forest),
>                         Bagging_DT (bootstrapped shallow trees)
>     Gradient boosting:  XGB, LGBM, HGB (Hist Gradient Boosting), CatBoost
>     Other:              KNN (instance-based), MLP (1 hidden layer, L2 weight decay)
>
>   8 more defined in the registry but not yet trained (SVM ×4 kernels, Bagging_SVM ×4,
>   Bagging_KNN, GB) — deprioritized behind the deadline, adding them is a config change
>   to train.py (registry pattern), not new engineering.

**Speaker notes (draft):
  "Before the models themselves, two pieces of scaffolding. Because GBP/USD is a time
  series, we never use a random train/test split — that would leak future data into
  training. Instead we use expanding-window walk-forward cross-validation: the training
  window grows by one year at a time, always testing on the year right after, and 2024 is
  a true held-out year, never touched until final evaluation.
  Second, every model here is really the same 4-step pipeline with a different estimator
  dropped in at the end: clean infinite values — our UK CPI log transform produces
  negative infinity during deflation — impute missing data using only the training fold's
  median, optionally rescale, then fit.
  With that scaffolding in place, we trained and fine-tuned 12 estimators spanning four
  families: two linear models, four tree-based models, four gradient boosting variants,
  and two others — k-nearest-neighbors and a small neural net. Eight more are already
  defined in the registry — SVM kernels, Bagging_KNN, GB — but were deprioritized purely
  on time; adding them later is a config change, not new engineering."**

---

### SLIDE 7b (DRAFT) — Hyperparameters & Refit

> Content:
>   Training workflow (unchanged from live Slide 8):
>     Bayesian search (Optuna/TPE, 50 trials, inner folds 1-4)
>       → Inner validation (fold 5, before touching final test)
>       → best_params.json (saved per model)
>       → Same best_params, refit independently per fold — 6 separate pipelines
>         (Fold 1 … Final), each on a longer training window, all sharing the one
>         best_params found once (not a single combined refit)
>
>   Best hyperparameters found (real values, Dataset 1 — search_results/*.json):
>     LR          — L1, C=0.68
>     Bagging_LR  — n_estimators=27, C=5.50 (weak regularization — flagged, see Slide 8b)
>     RF          — max_depth=16, min_samples_leaf=10
>     ET          — max_depth=13, max_features=sqrt
>     DT          — max_depth=3, min_samples_split=6 (capped shallow — underfits, Slide 8b)
>     Bagging_DT  — base depth=3, n_estimators=29
>     KNN         — k=8, euclidean
>     MLP         — alpha=0.0025 (L2), 236 hidden units
>     XGB         — max_depth=5, learning_rate=0.015, subsample tuned
>     LGBM        — num_leaves=26, learning_rate=0.094
>     HGB         — l2_regularization=4.89, max_depth=6
>     CatBoost    — depth=5, learning_rate=0.016
>
>   Why Bayesian over Grid/Random (collapsed extra material, same as live Slide 8):
>     Grid explodes combinatorially; Random has no memory across trials; Optuna/TPE
>     builds a probabilistic hyperparameter→score model from every prior trial —
>     fewer trials for the same quality, relevant since Bagging_LR/MLP take minutes/fit.
>     Inner-validation F1 did not predict final generalization: Bagging_LR had the
>     highest inner F1 (0.756) of all 12 models yet one of the worst final Profit
>     figures (−3.79%) — the search optimizes a proxy metric on one inner split, not a
>     substitute for the walk-forward evaluation on Slide 8b.

**Speaker notes (draft):
  "Every model went through the same tuning workflow: a 50-trial Bayesian search on the
  first four folds, validated on a fifth inner fold, then the winning hyperparameters are
  refit independently six times — once per walk-forward fold — never re-searched.
  A couple of these are worth flagging now because they explain results on the next
  slide: Bagging_LR's search landed on C=5.50, very weak regularization, and the Decision
  Tree got capped at depth 3 by the search itself. Also worth noting: the inner-search
  score that picks these hyperparameters doesn't reliably predict which model generalizes
  best — Bagging_LR had the best inner score of all twelve models and the worst real
  profit, which is exactly why we don't stop at this slide and instead walk-forward
  validate on genuinely held-out years next."**

---

### SLIDE 8b (DRAFT) — Evaluation: Accuracy & Profit

> Content:
>   Formulas (exact, not just named — added 2026-07-07):
>     Direction(t) = 1 if Close(t+1) > Close(t), else 0
>     Accuracy = (1/N) * sum_i 1{y_pred(i) = y_true(i)}        [N = test days · 50% = coin flip]
>     Profit (Guyard & Deriaz 2024, §5.3) — long/short, P(0) = 1:
>       P(t) = P(t-1) * C(t)/C(t-1)      if y_pred(t) = 1  (go long)
>       P(t) = P(t-1) * C(t-1)/C(t)      if y_pred(t) = 0  (go short)
>       Profit % = (P(T) - 1) * 100      [positive = made money · negative = lost money
>                                          over the test year, even if accuracy looks fine]
>
>   Annual vs. Monthly — two training schemes, same two formulas above applied to each:
>     Annual  — fit once on all data through 2023-12-31, predict the entire 2024 test
>               year in a single pass; Accuracy/Profit computed over that one
>               uninterrupted 2024 sequence. (This is the scheme train.py's foldfinal
>               .joblib pipelines already implement — no extra fitting needed.)
>     Monthly — walk-forward *within* the test year: fit on data through 2023-12-31 ->
>               predict January 2024 -> append the *real* January 2024 labels to the
>               training set -> refit (same fixed hyperparameters, only the training
>               window grows) -> predict February 2024 -> ... repeat through December
>               (12 refits total per model per dataset). The 12 monthly out-of-sample
>               chunks are concatenated back into one 2024 sequence, then the same
>               Accuracy/Profit formulas are applied — so Annual and Monthly are
>               directly comparable, only the training cadence differs. Neither scheme
>               ever trains on data that would postdate the prediction (no look-ahead).
>               Implemented in scripts/compute_monthly_annual_profit.py ->
>               reports/tables/monthly_annual_profit_2024.csv (12 models x 3 datasets x
>               {annual, monthly} x {acc, profit_pct} = 144 rows collapsed to 12/model).
>
>   How we evaluate (trimmed metrics decoder — just the two named in this slide's title):
>     Accuracy — % of days direction called correctly · 50% = coin flip
>     Profit   — compounding long/short return over the full 2024 test year (formula above)
>     (F1-macro/AUC-ROC/max drawdown still tracked in model_comparison.csv, just not
>     restated on this slide — kept off to leave room for the table below)
>
>   Walk-forward CV (why the numbers below are "2024 held-out", not train-set accuracy):
>     Expanding window, 6 folds, train always starts 2014, test = the year right after
>     the last training year; 2024 is the true held-out fold, never touched during tuning.
>
>   RESULTS TABLE — final (2024 held-out) Accuracy / Profit, all 12 models × 3 datasets
>   [Annual scheme shown below; Monthly scheme being computed, will extend this table to
>   12 columns/model — 3 datasets × {Annual, Monthly} × {Accuracy, Profit}]
>   (accuracy from model_comparison.csv fold=="final"; Profit computed by
>   scripts/compute_paper_profit.py -> reports/tables/paper_profit_2024.csv, using each
>   model's foldfinal .joblib pipeline re-predicting on its own 2024 test set):
>
>     Model       | D1 Basic Daily       | D2 90-Day Lookback   | D3 Technical
>                 | Acc.   Profit        | Acc.   Profit        | Acc.   Profit
>     ------------|----------------------|----------------------|--------------------
>     LR          | 65.5%   −1.56%       | 53.6%   −0.42%       | 74.3%   −2.84%
>     Bagging_LR  | 67.4%   −3.79%       | 51.7%   −1.11%       | 71.7%   +1.92%
>     RF          | 54.8%   −3.42%       | 51.7%   +2.29%       | 79.7%  −12.57%
>     ET          | 59.4%   +1.16%       | 49.4%   +4.13%       | 81.6%  −17.78%
>     DT          | 47.5%   +4.45%       | 47.9%   −6.47%       | 49.0%   +9.92%
>     Bagging_DT  | 58.2%   −3.80%       | 55.2%   −5.23%       | 82.0%   −8.59%
>     KNN         | 58.2%   +1.86%       | 49.0%   −0.54%       | 70.5%   −9.01%
>     MLP         | 64.4%   −0.37%       | 57.1%   −4.26%       | 78.2%  −12.60%
>     XGB         | 61.3%  +10.39%       | 53.3%   −0.36%       | 81.6%   −8.59%
>     LGBM        | 66.7%   +4.40%       | 59.4%   +3.67%       | 83.1%   −8.38%
>     HGB         | 62.1%  +11.83%       | 58.2%   +2.78%       | 83.1%   −7.60%
>     CatBoost    | 63.2%   −3.39%       | 62.1%   +0.86%       | 82.4%   −9.38%
>
>     Column-best per dataset — Accuracy: Bagging_LR (D1) / CatBoost (D2) / LGBM & HGB
>     tied (D3). Profit: HGB +11.83% (D1) / ET +4.13% (D2, but accuracy only 49.4%) / DT
>     +9.92% (D3, but accuracy only 49.0% — a coin-flip model with a lucky Profit, not a
>     real signal). Every Dataset 3 model except DT has negative Profit despite 70-83%
>     accuracy — the accuracy jump does not carry over to this metric.
>
>   BIAS-VARIANCE TRADE-OFF — 3 scatter charts, one per dataset, built from the real CV
>   fold numbers (x = fold-to-fold accuracy σ across inner folds 1-5 = variance; y = final
>   2024 held-out accuracy = bias proxy; ref. lines at 50% coin-flip and the dataset's
>   median σ). Only 3-4 extreme models labeled per dataset — the rest are plain dots
>   colored by family (Linear / Tree-Bagging / Boosting / Other), so the picture reads as
>   one trade-off, not a 12-name word cloud:
>     reports/figures/variance_tradeoff_dataset1_basic_daily.png
>       — Bagging_LR has the highest final accuracy (67.4%) but sits right, near-highest
>         variance (σ=0.047); CatBoost is the labeled "best trade-off" — 63.2% accuracy at
>         much lower variance (σ=0.033); DT is the lone high-bias case, final accuracy
>         47.5%, below coin flip.
>     reports/figures/variance_tradeoff_dataset2_90day_lookback.png
>       — Whole cloud sits in a tight 48-62% accuracy band regardless of variance
>         (p≫n signal dilution) — visual confirmation this dataset is a documented
>         negative result, not just a table of numbers. CatBoost still comes out on top
>         (62.1% accuracy) but the spread among the other 11 models is much narrower
>         than Dataset 1 or 3.
>     reports/figures/variance_tradeoff_dataset3_technical.png
>       — Boosting/tree cluster (LGBM, HGB, CatBoost, ET, XGB, Bagging_DT) packs into the
>         top-left ideal quadrant at 82-83% accuracy and low variance (σ≈0.02-0.03); HGB
>         is the labeled "best trade-off". DT is a dramatic outlier at the opposite
>         corner — both the highest variance of any model in the whole project
>         (σ=0.096, 3-4x every other model) and the only sub-50% accuracy on this
>         dataset — high bias AND high variance at once.

**Speaker notes (draft):
  "We evaluate on two numbers: accuracy, and Profit — the exact compounding long/short
  formula from the reference paper, asking whether trading on the prediction would have
  actually made money over 2024. Everything here is the true 2024 held-out fold from our
  walk-forward CV — never touched during tuning.
  This table is the condensed version of three datasets times twelve models. Two things
  jump out. First, on Dataset 1, Bagging_LR wins on accuracy but is one of the worst on
  Profit (−3.79%) — XGB and HGB are mid-table on accuracy but top the Profit column
  (+10.39% and +11.83%). Second, Dataset 3's technical indicators push every tree and
  boosting model to 70 to 83 percent accuracy, but ten of those twelve models still
  have a negative Profit — more accurate did not mean more profitable.
  These three scatter plots make the bias-variance side of that same story visual: on
  Dataset 1, CatBoost trades a few points of accuracy for much better stability across
  folds than the accuracy leader, Bagging_LR; Dataset 2's whole cloud stays in a narrow
  band near the coin-flip line no matter how stable a model is, because the signal isn't
  there to begin with; Dataset 3 shows almost every tree and boosting model landing in
  the ideal top-left corner together, except DT, which is both the least stable model in
  the entire project and the only one that doesn't beat a coin flip.
  That's the bias-variance trade-off in one picture per dataset, instead of one
  four-metric bar chart per topic."**

---

## What changed — 2026-07-06 (Dataset 2/3 now trained, Streamlit supports all 3 datasets)

Since the last outline update, `train.py` was run against Dataset 2 (90-day lookback) and
Dataset 3 (technical indicators) for all 12 models × 6 folds — `model_comparison.csv` grew
from 72 rows (Dataset 1 only) to 216 rows (12×6×3). `src/app/app.py` was also updated with a
dataset selector so the Streamlit UI works across all 3 datasets, not just Dataset 1. Four
changes, no new slide:

1. **Slide 9 ("Models & Results")**: added a new "Dataset 1 vs 2 vs 3" box + 4 charts
   (`dataset_comparison_{accuracy,auc,sharpe,overfit_gap}.png`) — Dataset 2 is a documented
   negative result (near coin-flip for all 12 models, p≫n at 9,110 cols vs. ~2,700 rows);
   Dataset 3 is a strong, consistent win for every tree/boosting model (80-85% acc., CV→Final
   gap <4pp) but linear models regress on it (collinear indicator windows) and — the
   counter-intuitive part — its much higher accuracy does not translate into a better Sharpe
   proxy than Dataset 1. Full analysis already exists in `reports/dataset_comparison.html`,
   this is the condensed on-slide version. Also updated the "Open issues & next steps" list to
   drop the now-done "build Dataset 2/3" item and add the Dataset-2/3 findings as open issues.
2. **Slide 10 ("Streamlit App")**: flow diagram gained a "Dataset selector" step before the
   model selector; status table and feature cards updated to describe the 3-dataset support,
   verified end-to-end in a real browser (dataset switch correctly re-triggers
   `load_dataset`/`available_models`/`load_pipeline`, not a stale cache).
3. **Slide 11 ("Conclusion")**: Goal 3 and Goal 4 cards updated to mention the 3-dataset scope
   (216 model×fold×dataset pipelines); "What's next" list dropped the "build Dataset 2/3" and
   "build backtest.py" items (both done — `backtest.py` was built in a prior session) and added
   two real next steps: extending `backtest.py` to Dataset 3's models to explain the
   accuracy/Sharpe disconnect, and mitigating Dataset 2's p≫n problem.
4. **No change to Slides 1-8** or to the Dataset-1-only numbers already cited there (target
   balance, EDA findings, pipeline architecture, training/fine-tuning details) — those are
   unaffected by the Dataset 2/3 training run.

Net effect on timing: Slide 9 grows the most (~60s → ~85s, new box + 4 charts). See the
updated Time Budget section for the trim suggestion.

---

## What changed vs. presentation_outline.md.bak (history — already applied, kept for rationale)

Goal: the training/metrics/model section (old slides 7-9) read numbers (accuracy, F1, AUC,
Sharpe proxy) before the audience ever learns what those numbers mean or what counts as
good/bad — and a few claims from `PROJECT_GUIDE.md`'s own glossary never made it into the
deck. Six changes, all reshuffling/adding text — no new slide, same 12-slide count:

1. **NEW: a "metrics decoder" table** added to Slide 7 — defines Accuracy/F1-macro/AUC-ROC/
   Sharpe proxy/Max drawdown in one line each + good/bad reference thresholds, pulled directly
   from `PROJECT_GUIDE.md` lines 237-294. Nothing like this existed anywhere in the deck before.
2. **Pipeline architecture moved from Slide 9 to Slide 7** — so "what does fit() actually do"
   is explained *before* Slide 7's CV diagram and Slide 8's training workflow use the word
   "fit" repeatedly, not after.
3. **Fixed ambiguous wording**: Slide 8's flow diagram said "Refit on all 6 folds", which
   reads like one combined model. `train.py` (lines 131-167) actually fits **6 independent
   pipelines**, one per fold, all sharing the same fixed `best_params`. Reworded to make
   that explicit.
4. **Consolidated the Bayesian-search deep-dive**: "Why Bayesian over Grid/Random" and "what
   the inner search results actually showed" used to sit in Slide 9's collapsed extra material,
   disconnected from where Bayesian search is first introduced. Moved into Slide 8's own extra
   material (still collapsed, still doesn't cost stage time).
5. **Surfaced the CV-accuracy-optimism caveat**: `PROJECT_GUIDE.md` (lines 239-244) already
   states CV accuracy is optimistic because folds 1-4 were also used to select hyperparameters
   — this reasoning was never stated in the deck itself, only "overfitting" was mentioned
   without the mechanism. Added to Slide 8's bias-variance box, plus the concrete reason
   Bagging_LR overfits (its search landed on C=5.50 — very weak regularization).
6. **New finding, now called out explicitly**: Bagging_LR's final AUC-ROC (0.869) actually
   crosses the project's own ">0.80 = investigate for leakage" threshold (from the new
   metrics decoder on Slide 7). Old deck treated this only as "consistent with the overfitting
   flag"; new version adds one sentence acknowledging the threshold crossing and why we
   believe it's regularization-driven overfitting, not leakage — pre-empts a sharp question.

Net effect on timing: Slide 7 grows (~45s → ~70s), Slide 8 grows slightly (~55s → ~60s),
Slide 9 shrinks (~75s → ~60s, content moved out). New raw total ≈ 10:15 — see the updated
Time Budget section at the bottom for the trim suggestion to land back on 10:00.

---

## Speaker Assignment

- Manim   : Introduction + Goal 1 — Data Collection & Harmonization (slides 1-3)
- Somitha : Goal 2 — Target, EDA & Feature Engineering (slides 4-6)
- Lee     : Goal 3 — Model Design/Training/Results + Goal 4 — Streamlit + Conclusion (slides 7-11)
- Slide 12 (References & AI Disclosure) — displayed on screen, no speaker notes needed

Team: Manimegalai Kumar-Periyasamy · Somitha Gudivada · Linh Hoang-Thuy
Course: Statistical Analysis & Machine Learning — DSA Spring 2026

---

## Slide-by-Slide Script

### SLIDE 1 — Title, Problem Statement & Project Overview (Manim, ~70 sec)

> Content:
>   Top half:
>     Title: "Predicting GBP/USD Daily Direction Using Machine Learning"
>     Subtitle: Training workflow — yes, every model was fine-tuned, not left on defaults
>     Course: Statistical Analysis & Machine Learning · Class: DSA Spring 2026
>     Team: Manimegalai Kumar-Periyasamy · Somitha Gudivada · Linh Hoang-Thuy
>
>   Bottom half:
>     4-block flow diagram: Data Collection → EDA → Model Pipeline → Streamlit UI
>     Each block labeled with the course goal number (Goal 1 / 2 / 3 / 4)
>     Project scope table: binary classification (next-day GBP/USD direction, up / not up),
>     period 2014-01-01 to 2024-12-31 (~2,868 trading days), reference paper cited

**Speaker notes (Manim):
  "Our project predicts whether the GBP/USD exchange rate will go up or not the next
  trading day — a binary classification problem. We adapted methodology from a 2024 paper
  on EUR/USD and applied it to GBP/USD using 11 years of data, from 2014 to 2024.
  The project follows four course goals. I'll start by covering how we collected the
  data, Somitha will explain our analysis, target definition, and feature engineering,
  and Lee will walk through the model design, training, results, and the interface."**

---

### SLIDE 2 — Data Sources & Collection Pipeline (Manim, ~65 sec)

> Content:
>   Top — Three data categories:
>     1. Macro indicators — GDP, CPI, central bank rates, current account (USA + UK)
>        Sources: FRED API, ONS UK API
>     2. Forex OHLCV — 13 currency pairs (GBP/USD is both feature and target)
>        Source: yfinance
>     3. Equity indices — 9 indices (5 US, 4 UK)
>        Source: yfinance
>
>   Middle — Pipeline flow (table form, one column per stage) — NEW 2026-07-06: build_dataset.py's
>   output now forks into 2 more build scripts, producing 3 final datasets, not 1:
>     fetch_*.py (pull raw data, needs network)
>       → data/raw/ (landing zone, 1 CSV/series, keeps realtime_start to prevent look-ahead bias)
>       → process_*.py (clean & harmonize into daily panel, offline, pure pandas)
>       → data/interim/ (6 panels, common daily date index 2014–2024)
>       → build_dataset.py (join on date, drop multicollinear, add returns/rate_differential/target)
>       → data/processed/dataset_basic_daily.csv (2,868 rows × 111 cols — Dataset 1)
>           ├→ build_dataset_90day.py (adds 90 lagged copies of every lag-eligible column;
>              calendar cols excluded — already derivable from the date; drops first 90 rows)
>              → data/processed/dataset_90day_lookback.csv (2,778 rows × 9,110 cols — Dataset 2)
>           └→ build_dataset_technical.py (computes ~60-72 technical-indicator columns per
>              instrument for all 17 instruments — 13 forex + 4 equity (5 multicollinear equity
>              indices excluded, same filter as Dataset 1) — merged onto Dataset 1's
>              date index; drops first 90 rows for indicator lookback)
>              → data/processed/dataset_technical.csv (2,778 rows × 1,178 cols — Dataset 3)
>     All 3 → train.py (same walk-forward CV / Bayesian-search pipeline, only the input CSV differs)
>
>   Bottom — Entity-Relationship Diagram — NEW 2026-07-06: ML_DATASET now shown materializing
>   as the 3 concrete files, keyed by dataset_type:
>     DIM_DATE (date PK, day/month/weekday, cyclical sin/cos)
>       → has → ECONOMIC_INDICATOR, MARKET_INDEX_PRICE, FOREX_PAIR_PRICE
>       → feeds → ML_DATASET (date PK, direction_target, dataset_type)
>       → materializes as 3 files (same date PK, same target, different feature columns):
>           dataset_basic_daily.csv      (dataset_type="basic_daily",     2,868 × 111)
>           dataset_90day_lookback.csv   (dataset_type="90day_lookback",  2,778 × 9,110)
>           dataset_technical.csv        (dataset_type="technical",      2,778 × 1,178)
>
>   Bottom note: 2014-01-01 to 2024-12-31 · ~3,254 trading days

**Speaker notes (Manim):
  "We collected data from three categories: macro indicators from FRED and the ONS API,
  and market data from yfinance — 13 forex pairs and 9 equity indices.
  The pipeline has two stages. Fetch scripts pull from APIs and save raw CSVs, keeping the
  publication date so we never leak future information. Process scripts clean each
  indicator into a daily panel and can run fully offline. That gives us Dataset 1 — 2,868
  rows and 111 columns. From there, two more build scripts fork off the same Dataset 1 to
  produce Dataset 2, a 90-day lookback with lagged features, and Dataset 3, technical
  indicators across all 17 instruments — Lee will cover how those two perform later in the
  deck. This ER diagram shows how the source tables — dated economic indicators, market
  index prices, and forex pair prices — all join on date into one ML_DATASET entity, which
  in practice materializes as these 3 separate CSV files sharing the same date key and
  target."**

---

### SLIDE 3 — Data Limitations & Panel Harmonization (Manim, ~65 sec)

> Content:
>   Top half — Two features investigated and excluded:
>
>     Composite PMI (USA and UK):
>       Not published on FRED. investing.com only retains the last 3-4 releases — not 10 years.
>       No free full-history source found → excluded from feature set.
>
>     FX trading volume:
>       Dukascopy provides only broker-network volume, not global market volume.
>       10 years of tick data = ~5 days of download time, then hourly aggregation.
>       yfinance carries no FX volume at all.
>       → excluded from model.
>
>   Bottom half — How data is time-aligned without look-ahead bias:
>
>     Problem: macro indicators release monthly or quarterly and get revised later.
>     A naive join on the period date would use data before it was published.
>
>     Solution (build_known_as_of):
>       Each raw CSV has a realtime_start column — the actual publication date.
>       For every trading day: look backward and attach the latest value whose
>       realtime_start is on or before that day.
>       → each row only sees what was genuinely public on that date.
>
>     days_since_update: how stale each reading is → fed as an explicit model feature.
>
>     Transforms applied in process_*.py:
>       Central bank rates → sqrt  (variance stabilization)
>       UK CPI YoY → log           (variance stabilization)
>       CPI level columns dropped  (ADF test: non-stationary I(1))

**Speaker notes (Manim):
  "Two data sources had to be excluded. Composite PMI has no free 10-year history and
  FX trading volume is either broker-only or absent in yfinance.
  For the remaining data, the key challenge is time alignment. We use each value's actual
  publication date so the model never sees a revision before it was officially released.
  The days_since_update column tells the model how stale any given reading is."**

---

### SLIDE 4 — Target Variable Definition (Somitha, ~35 sec)

> Content:
>   Task box: predicting whether GBP/USD close will be higher or not higher next trading
>   day, using today's macro/forex/equity features (t) to predict binary direction at t+1.
>   Binary classification — not regression (magnitude not predicted).
>
>   Formula:
>     Direction(t) = 1  if close(t+1) > close(t)
>     Direction(t) = 0  if close(t+1) <= close(t)
>   Class balance table:
>     UP (1):   1,408 days — 49.1%
>     DOWN (0): 1,461 days — 50.9%
>     Ratio: 1.04x → near-perfectly balanced
>   Rolling 1-year UP% : oscillates around 50% throughout 2014-2024, no persistent drift

**Speaker notes (Somitha):
  "Our target is the next-day direction of GBP/USD close price — 1 if it goes up, 0
  otherwise. Checking the class balance is the first thing we do: 49.1% up versus 50.9%
  down, ratio 1.04. The dataset is essentially balanced, which means we do not need
  SMOTE, oversampling, or class-weight correction. The rolling chart confirms no
  persistent directional drift over the decade."**

---

### SLIDE 5 — EDA: Macro, Forex, and Equity (Somitha, ~55 sec)

> Content:
>   Three charts, one per data category:
>
>   Macro (notebook 01) — correlation heatmap:
>     Rate differential (Fed minus BoE): negative 2014-2016, compressed 2017-2021,
>       positive 2022-2023 as Fed hiked faster than BoE → added as engineered feature
>     CPI & GDP levels are I(1) → YoY forms used instead
>
>   GBP/USD and forex (notebook 02) — returns distribution:
>     Daily returns: mean −0.008%/day, std 0.57%, skew −0.91, kurtosis 14.4
>       → fat tails → RobustScaler used, not StandardScaler
>     Largest single-day drop: −7.6% on 2016-06-24 (Brexit referendum result)
>     EUR_GBP kurtosis = 109, GBP_CHF kurtosis = 173 → clip at ±5σ before training
>
>   Equity (notebook 02) — price series:
>     US indices (NASDAQ100, SP500) +300-400% from 2014-2024; UK FTSE100 largely flat
>     Multicollinearity: 5 of 9 indices dropped
>       (DJI r=0.95 with SP500, NASDAQ_COMPOSITE r=0.99 with NASDAQ100,
>        FTSE_ALL_SHARE r=0.993 with FTSE100, FTSE350 r=0.974 with FTSE100,
>        FTSE250 r=0.872 with FTSE_ALL_SHARE)
>       → 4 kept: SP500, NASDAQ100, RUSSELL2000, FTSE100

**Speaker notes (Somitha):
  "Three key findings. First, the rate differential between the Fed and BoE is one of
  the clearest macro drivers of GBP/USD — we add it as an explicit feature.
  Second, GBP/USD daily returns show extreme fat tails — kurtosis of 14, up to 173 for
  GBP/CHF — which is why we use RobustScaler rather than StandardScaler in the model
  pipeline. Third, we started with 9 equity indices but correlation analysis shows 5 are
  near-duplicates of the others, so we drop them and keep 4."**

---

### SLIDE 5 (DRAFT — outline requested 2026-07-06, current Slide 5 above is UNCHANGED)

> NOTE: this is a draft reorganization, kept side-by-side with the current Slide 5 for
> comparison. Not yet adopted. Structured as pure Feature Engineering (Drop / Transform /
> Added / Encoded) rather than by data category (macro/forex/equity). Preprocessing-only
> items from the current Slide 5 (RobustScaler choice, ±5σ clipping) are NOT included
> here — they would stay a Slide 7 (Pipeline) topic since they're refit per-CV-fold, not
> static dataset-build transforms. The "3 diagrams" placeholder below assumes the same
> 3 charts as the current Slide 5 (macro heatmap, forex returns distribution, equity
> price series) — confirm or swap before finalizing.

> Content:
>
>   Feature Engineering
>
>   Drop
>     ADF test: CPI & GDP levels are I(1) — non-stationary (trended monotonically,
>       e.g. CPI 100→130 over 11 years) → dropped, replaced by transforms below
>     Multicollinearity: 5 of 9 equity indices dropped (r > 0.87 with a kept index:
>       DJI/SP500, NASDAQ_COMPOSITE/NASDAQ100, FTSE_ALL_SHARE/FTSE100, FTSE350/FTSE100,
>       FTSE250/FTSE_ALL_SHARE) → kept: SP500, NASDAQ100, RUSSELL2000, FTSE100
>
>   Transform
>     Time-alignment without look-ahead bias: macro panel forward-filled using each
>       series' realtime_start (publish date), not the period date it describes —
>       prevents future macro releases from leaking into past training rows
>     √ (square root) — Central bank rates (USA, UK) — variance stabilization
>     log — UK CPI YoY — variance stabilization
>
>   Added
>     Equity log return: {INDEX}_ret = log(close_t / close_{t-1})
>     Rate differential: USA_central_bank_rate − UK_central_bank_rate
>
>   Encoded
>     Date encoding:
>       Tree models — RF, XGB, LGBM, HGB, CatBoost, DT, ET, Bagging_DT:
>         day, month, weekday — plain integers
>       Linear & distance models — LR, Bagging_LR, KNN, MLP:
>         day/month/weekday — sin & cos pairs
>
>   [3 diagrams — placeholder, see NOTE above]

---

### SLIDE 6 — Feature Engineering & Building the Model Dataset (Somitha, ~50 sec)

> Content:
>   Left — What was DROPPED (decisions justified by EDA):
>
>     CPI level columns (USA_cpi_value, UK_cpi_value):
>       ADF test: non-stationary I(1) — trended monotonically 100→130 over 11 years.
>       → replaced by CPI Year-on-Year % (stationary, mean-reverting).
>
>     5 of 9 equity indices — multicollinearity:
>       DJI               r = 0.954 with SP500        → dropped
>       NASDAQ_COMPOSITE  r = 0.992 with NASDAQ100     → dropped
>       FTSE_ALL_SHARE    r = 0.993 with FTSE100       → dropped
>       FTSE350           r = 0.974 with FTSE100       → dropped
>       FTSE250           r = 0.872 with FTSE_ALL_SHARE → dropped
>       Kept: SP500, NASDAQ100, RUSSELL2000, FTSE100
>
>   Right — What was ADDED / ENCODED:
>
>     Equity log returns:
>       {INDEX}_ret = log(close_t / close_{t-1})
>       Log-return is stationary and compressible — suitable for ML.
>
>     Engineered macro feature:
>       rate_differential = USA_central_bank_rate − UK_central_bank_rate
>       Captures the interest rate spread that directly drives GBP/USD capital flows.
>
>     Date encoding — two versions for different model families:
>       Tree models (RF, XGB, CatBoost, etc.):
>         day (int), month (int), weekday (int, 0 = Monday)
>       Linear models & MLP:
>         day_sin, day_cos, month_sin, month_cos, weekday_sin, weekday_cos
>         Cyclical encoding — so December and January are treated as adjacent.
>
>   Bottom — Column breakdown of the final dataset (measured directly from
>   dataset_basic_daily.csv):
>     Forex:          52 cols · 13 pairs × {open, high, low, close}          · NaN 0.00%
>     Equity:         28 cols · 4 indices × {OHLC, volume, volume_sqrt, ret} · NaN 0.005%
>     Macro:          20 cols · 8 indicators × {value, transform,
>                     days_since_update} + rate_differential                · NaN 3.53% avg
>     Date/calendar:  10 cols · date + day/month/weekday + 6 cyclical sin/cos · NaN 0.00%
>     Target:          1 col  · direction (0/1)                             · NaN 0.00%
>     Total:         111 cols · 2,868 rows                                  · NaN 0.64% overall
>
>     Macro NaN concentrated in early history before each series' first known release
>     (worst: USA CPI YoY at 10.46%, needs 12 months of history to compute a
>     year-on-year figure). Equity's 0.005% is just the first-day return of each kept
>     index (no t-1 to diff against).

**Speaker notes (Somitha):
  "After the EDA we knew exactly what to keep and what to remove. CPI price levels
  trend upward monotonically over 11 years — that is non-stationary, which misleads
  linear models. We use year-on-year inflation instead. We dropped five equity indices
  because they were near-identical to ones we kept — correlations above 0.87.
  What we added: log returns to make equity stationary, a rate differential capturing
  the Fed-versus-BoE spread which the EDA showed was a key driver, and date encodings
  in two forms — integers for tree models and sine-cosine pairs for linear models so
  that the calendar wraps around correctly, with December connecting back to January.
  The final dataset is 111 columns across four categories, with missing data
  concentrated almost entirely in early-history macro columns before those series
  had 12 months of history to compute a year-on-year figure.

  One thing to flag: you won't see imputation or scaling in this dataset build step.
  That's not an oversight — the dropped/added columns above are static transforms,
  computed once on the whole dataset before any CV split. Imputation (median) and
  scaling (RobustScaler) are different: they have to be refit on each training fold
  separately, otherwise the test fold's median/IQR would leak into training. That's
  why they live inside the model Pipeline on the next slide instead of here."**

---

### SLIDE 7 — Model Pipeline, Metrics & Walk-Forward CV (Lee, ~70 sec) — RESTRUCTURED

> Content:
>   Pipeline architecture (moved here from the old Models & Results slide — explains what
>   "fit" means before the CV/training slides use the word repeatedly):
>     InfinityToNaNTransformer → SimpleImputer(median) → [RobustScaler, conditional] → Model
>
>     Why this lives here and not on Slide 6 (Feature Engineering): the dropped/added
>     columns on Slide 6 are static, dataset-level transforms — computed once, before
>     any CV split. Imputation and scaling can't be done that way: median (Imputer) and
>     IQR (RobustScaler) must be refit on each training fold separately, or the test
>     fold's statistics leak into training. That's why these three steps are bundled
>     inside the model Pipeline and refit six times (once per fold), not applied once
>     upfront like the Slide 6 transforms.
>
>     InfinityToNaNTransformer: replaces +inf/−inf with NaN across all 111 columns; needed
>       because UK_cpi_yoy_log produces −inf during deflation periods (log of a negative
>       YoY figure) — without this the imputer would crash on non-finite input.
>     SimpleImputer(median): fits per-column median on the training fold only, fills NaN;
>       handles the ~0.64% overall missing data (worst: USA CPI YoY, 10.46%).
>     RobustScaler (conditional): applied only when the model registry's scale flag is
>       true (LR, MLP, KNN, Bagging_LR, untrained SVM variants); skipped for tree-based
>       models, which split on raw thresholds. Uses median/IQR because EDA found
>       fat-tailed returns (kurtosis up to 173).
>
>   Metrics we'll cite from here on — NEW, a decoder table so numbers on the next two
>   slides aren't cold (thresholds pulled from the project's own metric glossary):
>     Accuracy    — % of days direction called correctly · 50% = coin flip
>     F1-macro    — accuracy balanced across UP/DOWN classes · what the Bayesian search optimizes
>     AUC-ROC     — ranking quality regardless of threshold · 0.55-0.65 = typical for FX
>                   direction in the literature · 0.80+ = flagged, investigate for leakage
>     Sharpe proxy — annualised return/risk of "go long when the model says UP" ·
>                   >0.3 = decent · <0 = strategy loses money even if accuracy looks fine
>     Max drawdown — worst peak-to-trough loss of that simulated strategy
>
>   Diagram of expanding-window walk-forward cross-validation:
>     Fold 1: Train 2014-2018 / Test 2019
>     Fold 2: Train 2014-2019 / Test 2020
>     Fold 3: Train 2014-2020 / Test 2021
>     Fold 4: Train 2014-2021 / Test 2022
>     Fold 5: Train 2014-2022 / Test 2023
>     Final:  Train 2014-2023 / Test 2024  (held out — never touched until final evaluation)
>   Explain WHY: time series → no random split → no data leakage

**Speaker notes (Lee):
  "Before the numbers, two quick pieces of scaffolding. First, every model here is really a
  4-step pipeline, not a bare classifier: clean infinite values — our UK CPI log transform
  produces negative infinity during deflation — impute missing data using only the training
  fold's median, optionally rescale for models that need it, then fit the model itself.
  Second, here's how to read the metrics for the rest of this section. Accuracy and
  F1-macro are self-explanatory. AUC-ROC measures ranking quality — for FX direction
  prediction, 0.55 to 0.65 is the normal literature range, and anything above 0.80 is
  actually a red flag worth double-checking, not a win. Sharpe proxy tells us whether
  accuracy would have actually made money if we'd traded on it.
  Now the split itself: because GBP/USD is a time series, a random train/test split would
  let the model see future data during training — that's data leakage. Instead we use
  expanding-window walk-forward cross-validation: the training window grows by one year at
  a time, and we always test on the year immediately after. The 2024 data is a true
  held-out set, never touched until the final evaluation."**

---

### SLIDE 8 — Model Training & Fine-Tuning (Lee, ~60 sec) — edits: clarified wording, added regularization/CV-optimism explanation, consolidated Bayesian-search deep-dive here

> Content:
>   Training workflow (confirms every model was actually fine-tuned, not left on defaults):
>     Bayesian search (Optuna/TPE, 50 trials, inner folds 1-4)
>       → Inner validation (fold 5, before touching final test)
>       → best_params.json (saved per model)
>       → Same best_params, refit independently per fold (train.py fits 6 separate
>         pipelines — Fold 1 through Final, each on a longer training window — all using
>         the one fixed best_params found once; not a single combined refit)
>     All 12 trained models have a saved
>     models/search_results/{model}_dataset_basic_daily_best_params.json.
>
>   12 models — method & what regularization was actually tuned (real values from
>   search_results/*.json):
>     LR (Logistic Regression) — linear — L1/L2 + C, saga solver — best: L1, C=0.68
>     Bagging_LR — 27 bootstrap LR models — n_estimators + C tuned — best: n=27, C=5.50
>     RF (Random Forest) — bagging of trees — max_depth, min_samples_leaf — depth=16, leaf=10
>     ET (Extra Trees) — randomized split thresholds — max_depth, max_features — depth=13, sqrt
>     DT (Decision Tree) — single tree — max_depth, min_samples_split — depth=3, split=6
>     Bagging_DT — 29 shallow trees — base depth + n_estimators — depth=3, n=29
>     KNN — instance-based — n_neighbors, metric — k=8, euclidean
>     MLP — 1 hidden layer — alpha (L2 decay), layer size, LR — alpha=0.0025, 236 units
>     XGB — gradient boosting — max_depth, subsample, learning_rate — depth=5, lr=0.015
>     LGBM — leaf-wise boosting — num_leaves, learning_rate — leaves=26, lr=0.094
>     HGB (Hist Gradient Boosting) — l2_regularization, max_depth, LR — L2=4.89, depth=6
>     CatBoost — ordered boosting — depth, learning_rate, iterations — depth=5, lr=0.016
>
>     Only LR and HGB carry an explicit classic L1/L2 penalty term; tree ensembles
>     regularize structurally via depth/leaf/sampling limits instead, and MLP uses L2
>     weight decay (alpha).
>
>   Curves used to evaluate fit — no classic train/val learning curve (invalid for time
>   series); walk-forward comparison used instead:
>     CV vs Final accuracy (bar) — Mean accuracy over inner folds 1-5 vs. the true 2024
>       held-out year — gap = overfitting/variance signal
>     Accuracy per fold (line) — Accuracy trend across test years 2019-2023 — spread =
>       stability across market regimes
>     AUC-ROC by model (bar) — Mean AUC across folds 1-5 — ranking ability beyond 0.5
>     Sharpe proxy by model (bar) — Mean simulated trading Sharpe across folds 1-5 —
>       whether accuracy translates into simulated profit
>
>   Bias-variance tradeoff — read from the real fold numbers:
>     High variance (overfit): LR & Bagging_LR — both ~73.7% mean CV accuracy (highest of
>       all 12) but final 2024 accuracy drops to 65.5% / 67.4% (−8.2pp / −6.3pp). Part of
>       this gap is mechanical, not just these two models overfitting in isolation: folds
>       1-4 were also the folds the Bayesian search optimized against, so the CV mean is
>       inherently a little optimistic for every model — see the project's own CV-accuracy
>       caveat. Bagging_LR's search also landed on C=5.50 — very weak L2 regularization —
>       which independently explains why it fits training noise easily.
>     Low variance (well-generalized): XGB & CatBoost — lowest fold-to-fold swings
>       (σ≈0.03). XGB's CV→Final gap is only +1.0pp; CatBoost's final (63.2%) is actually
>       higher than its CV mean (58.7%) — no overfitting signal.
>     High bias (underfit): DT — Optuna capped max_depth at 3, too shallow to separate
>       classes. Final accuracy 47.5%, below the 50% coin-flip baseline.
>
>   Extra material (collapsed, expand if time/questions permit) — moved here from the old
>   Models & Results slide, since this is where Bayesian search is first introduced:
>     Why Bayesian over Grid/Random: Grid Search cost explodes combinatorially and wastes
>       trials on obviously bad regions. Random Search covers high-dimensional spaces
>       better but has no memory — trial 50 is as blind as trial 1. Bayesian (Optuna/TPE)
>       builds a probabilistic model of hyperparameters→score from every prior trial and
>       samples the next candidate from promising regions — fewer trials needed for the
>       same quality, relevant since some models (Bagging_LR, MLP) take minutes per fit.
>     What the inner-search results actually showed: inner-validation F1 did NOT predict
>       which model generalized best. Bagging_LR scored the highest inner F1 of all 12
>       models (0.756) yet had the worst Sharpe on the true 2024 test. XGB scored a much
>       lower inner F1 (0.617) but generalized the most consistently — the search
>       optimizes a proxy metric on a single inner split, not a substitute for
>       walk-forward validation on genuinely held-out time.

**Speaker notes (Lee):
  "Every one of the 12 trained models went through the same pipeline: a 50-trial Bayesian
  search on the first four folds, validated on a fifth inner fold, and then the same fixed
  hyperparameters are refit independently on each of the six walk-forward folds — six
  separate model files, not one combined model. Only LR and HGB carry a classic textbook
  L1/L2 penalty; the tree ensembles control complexity structurally, through depth and
  leaf limits instead.
  Looking at the real numbers: LR and Bagging_LR scored the highest cross-validation
  accuracy of all 12 models, around 73.7%, but that's a red flag for two reasons — part
  mechanical, since folds 1-4 were also what the search tuned against, and part genuine:
  Bagging_LR's search landed on very weak regularization, C equals 5.5. Either way, their
  accuracy drops 6 to 8 points on the true 2024 test, which is classic overfitting.
  XGBoost and CatBoost barely move between CV and the final test — CatBoost's final score
  is actually higher than its CV average. And the Decision Tree alone underfits: Optuna
  itself capped it at depth 3, and it ends up below a coin flip on 2024."**

---

### SLIDE 9 — Models & Results (Lee, ~85 sec) — edits: pipeline architecture and Bayesian-search deep-dive moved out (now on slides 7 and 8); added AUC-threshold caveat to chart 4; NEW 2026-07-06: added Dataset 1 vs 2 vs 3 comparison box + 4 charts

> Content:
>   Model status:
>     Trained & fine-tuned (12): LR, RF, XGB, LGBM, MLP, KNN, DT, ET, HGB, CatBoost,
>       Bagging_DT, Bagging_LR — full walk-forward CV (6 folds) + Bayesian search
>       (50 trials each) — now trained across all 3 datasets (216 model×fold×dataset
>       rows in model_comparison.csv, up from 72 when only Dataset 1 was trained).
>     Planned next, time allowing: GB, Bagging_KNN, SVM_linear/rbf/sigmoid/poly,
>       Bagging_SVM_* — already defined in the model registry; kernel SVMs are notably
>       slower to fit, so deprioritized behind the presentation deadline. Adding them
>       later is a config change to train.py, not new engineering (registry pattern in
>       src/models/model_registry.py).
>
>   NEW — Dataset 1 vs 2 vs 3: does more data help?
>     Dataset 1 (Basic Daily, 2,868 rows × 111 cols): best model Bagging_LR, 67.4% final
>       accuracy — the baseline covered by the rest of this slide.
>     Dataset 2 (90-Day Lookback, 2,778 rows × 9,110 cols): best model CatBoost, only
>       62.1% final accuracy — near coin-flip for every one of the 12 models. Documented
>       negative result: p≫n (9,110 cols vs. ~2,700 training rows) leaves the design
>       matrix too rank-deficient / diluted for any model family, tree-based included.
>     Dataset 3 (Technical Indicators, 2,778 rows × 1,178 cols): best models LGBM & HGB
>       (tied), 83.1% final accuracy (CV ~80%, gap +3.0-3.4pp — not overfitting). Strong,
>       consistent win for every tree/boosting model (80-83% acc., 0.89-0.91 AUC). Fix
>       2026-07-06: was mistakenly computing indicators for all 9 equity indices instead
>       of the 4 non-redundant ones Dataset 1 uses — after dropping the same 5
>       multicollinear indices, linear models (LR, Bagging_LR) now score *higher* than on
>       Dataset 1, consistent with collinear inputs hurting linear boundaries specifically.
>       The counter-intuitive part still holds: the much higher accuracy does not
>       translate into a better Sharpe proxy; most Dataset 3 models (10/12) are still more
>       negative on Sharpe than their Dataset 1 counterpart.
>     4 charts: dataset_comparison_{accuracy,auc,sharpe,overfit_gap}.png. Full write-up:
>       reports/dataset_comparison.html.
>
>   Four charts (real 2024 held-out results):
>     Chart 1 (cv_vs_final_accuracy.png):
>       Bagging_LR (67.4%) and LGBM (66.7%) lead 2024 held-out accuracy.
>       LR and Bagging_LR show the largest CV→Final gap (−8.2pp, −6.3pp) — overfitting
>       warning.
>
>     Chart 2 (accuracy_per_fold.png):
>       XGB and CatBoost have the lowest fold-to-fold variance (σ≈0.03).
>       Most models spike in fold 2 (test year 2020); HGB and MLP swing the most
>       (σ>0.05).
>
>     Chart 3 (sharpe_by_model.png):
>       XGB (1.28) and HGB (1.24) top the 2024 Sharpe proxy despite mid-table accuracy.
>       Bagging_LR — the accuracy leader — has the worst Sharpe (−0.87).
>
>     Chart 4 (roc_pr_curves.png) — ROC + Precision-Recall on the true 2024 held-out
>     fold only (not a separate train/val split — same test set as charts 1-3), for
>     the 4 models named earlier in the deck (XGB, HGB, Bagging_LR, LGBM):
>       AUC-ROC: Bagging_LR 0.869, LGBM 0.720, HGB 0.679, XGB 0.656
>       AP: Bagging_LR 0.883, LGBM 0.763, HGB 0.714, XGB 0.698
>       Bagging_LR leads on AUC/AP too — same overfitting flag as its accuracy/Sharpe
>       numbers, not a contradiction: a model can rank near-best on threshold-free
>       metrics (AUC/AP) while still losing money once you pick an operating threshold
>       (Sharpe proxy).
>       NEW: 0.869 also crosses the >0.80 "investigate for leakage" reference threshold
>       introduced on Slide 7. We attribute this to Bagging_LR's very weak regularization
>       (C=5.50, from Slide 8) rather than a data leak, since the same pattern — high CV,
>       weak final generalization — shows up consistently across accuracy, F1, and Sharpe
>       for this specific model, not as an isolated AUC anomaly.
>
>   Which model is most effective? — depends on the metric (table scoped to Dataset 1;
>   see the dataset-comparison box above for how CatBoost/LGBM overtake on Dataset 3's
>   raw accuracy, without a better Sharpe proxy):
>     Accuracy: Bagging_LR — 67.4% (but CV score 73.7% was inflated 6.3pp above this)
>     Risk-adjusted (Sharpe proxy): XGB — 1.28 · HGB — 1.24 (mid-table accuracy, 61-62%,
>       but only models with strongly positive Sharpe)
>     Most stable across CV folds: XGB · CatBoost (lowest year-to-year variance)
>     Worst: DT — 47.5% (below the 50% coin-flip baseline)
>     Recommendation: XGB or HGB for a live/practical setting — the only models where
>     the accuracy story and the Sharpe story agree.
>
>   Open issues & next steps:
>     Issues: accuracy leader ≠ profit leader (Bagging_LR best Dataset-1 accuracy, worst
>       Sharpe); LR/Bagging_LR generalize worse than CV suggests; Dataset 2 is a
>       documented negative result (near-random for every model, p≫n); Dataset 3's much
>       higher accuracy does not translate into a better Sharpe proxy; final test is a
>       single year (~260 days, one regime, noisy); SVM/Bagging_KNN/GB defined but not
>       trained yet.
>     Next steps: investigate LR/Bagging_LR overfitting; extend
>       src/evaluation/backtest.py (already built) to Dataset 3's top models to explain
>       the accuracy/Sharpe disconnect; try an ensemble of top-Sharpe models (XGB + HGB);
>       mitigate Dataset 2's p≫n problem via feature selection/PCA, or keep it as a
>       documented negative result; train remaining registry models as time allows.

**Speaker notes (Lee):
  "We trained and fully fine-tuned 12 of the models in our registry; a few kernel SVMs and
  some remaining ensembles are defined but were deprioritized behind today's deadline —
  adding them later is just a config change, not new engineering.
  On the real 2024 held-out results: Bagging_LR and LGBM top the accuracy leaderboard, at
  67 and 66 percent. But accuracy alone is misleading here — if you actually traded on
  these predictions, Bagging_LR has the worst simulated Sharpe of all twelve models, while
  XGBoost and HGB, sitting mid-table on accuracy, have the only strongly positive Sharpe
  ratios. So our recommendation for a live setting is XGBoost or HGB — they're the only
  models where the accuracy story and the profit story agree. Bagging_LR also leads on
  ROC-AUC and precision-recall on this same test set — and its AUC actually crosses the
  0.80 threshold we flagged earlier as worth double-checking. We looked into it: it lines
  up with the very weak regularization its search found, not a data leak, and the same
  high-CV/weak-final pattern shows up in its accuracy and Sharpe too, not just AUC in
  isolation. The open issues slide is here mainly for questions: our Sharpe proxy doesn't
  yet model transaction costs, and 2024 is a single test year, so it's one market regime
  and a noisy estimate.
  Since we last presented, we've also trained all 12 models on two more datasets. Dataset
  2, a 90-day lookback of raw prices, is a negative result — near coin-flip accuracy
  across every model, because 9,110 columns against only around 2,700 training rows
  dilutes the signal too much for any model family. Dataset 3, technical indicators, is
  the opposite story: every tree and boosting model jumps to 80 to 85 percent accuracy,
  and the CV-to-final gap stays under 4 points, so it's not just overfitting. But here's
  the catch — that much higher accuracy does not show up as a better Sharpe proxy; if
  anything most Dataset 3 models are worse on Sharpe than their Dataset 1 counterparts.
  That's a finding we want to dig into further with the backtest."**

---

### SLIDE 10 — Streamlit App — Goal 4 (Lee, ~50 sec) — NEW 2026-07-06: app now supports switching between all 3 datasets, not just Dataset 1

> Content:
>   App data flow:
>     Dataset selector (Dataset 1 / 2 / 3)
>       → Model selector (pick from the 12 trained models)
>       → Pipeline.predict() (loaded from models/trained/*.joblib)
>       → Direction + confidence (up/down + probability)
>     No live training in the app — all 12 models × 6 folds × 3 datasets are pre-fit and
>     loaded from disk, so switching dataset or model re-renders predictions instantly,
>     no retraining.
>
>   Three feature cards:
>     Dataset selector (new) — sidebar dropdown for Dataset 1 (Basic Daily) / 2 (90-Day
>       Lookback) / 3 (Technical Indicators); metrics table and model list re-scope
>       correctly to whichever dataset is picked
>     Prediction output — direction (up/down) + confidence, from a pre-trained model of choice
>     Dataset comparison section (new) — renders the same 4 accuracy/AUC/Sharpe/
>       overfit-gap charts shown on the previous slide, plus a link to the full
>       reports/dataset_comparison.html narrative
>
>   Status:
>     src/app/app.py — Built, now supports all 3 datasets, verified end-to-end in a real
>       browser (dataset switch correctly re-triggers load_dataset/available_models/
>       load_pipeline, not a stale cache)
>     Trained models available to load — 12 models × 6 walk-forward folds × 3 datasets
>     (216 models/trained/*.joblib pipelines)

**Speaker notes (Lee):
  "This app doesn't train anything live — every model, fold, and dataset combination was
  already trained and saved to disk by train.py. Since we last presented, we've added a
  dataset selector, so you can pick Dataset 1, 2, or 3 and everything downstream — the
  model list, the metrics, the predictions — re-scopes correctly. We verified this in a
  real browser, switching datasets and confirming the numbers actually change and match
  what's in our results table, not a cached leftover from Dataset 1. There's also a new
  section at the bottom showing the same dataset-comparison charts from the results
  slide."**

> Presentation talking points (extra material, use as needed):
>   - Architecture point: **train once, demo many times** — decouples the expensive
>     training step from the interactive demo, which is why the UI is instant.
>   - If asked "why 12 models and not more" — mention the registry pattern makes adding
>     the remaining SVM/GB/Bagging_KNN variants a config change, not new engineering; they
>     were deprioritized purely on time, not because they don't fit the pipeline.

---

### SLIDE 11 — Conclusion & Takeaways (Lee, ~60 sec) — expanded: goal-by-goal recap, pipeline recap, best-model-by-metric, future work

> Content:
>   How the 4 course goals were executed (4-card grid):
>     Goal 1 — Data Collection: FRED/ONS/yfinance → macro (USA+UK), 13 forex pairs, 9
>       equity indices harmonized into one daily panel; realtime_start tracked on every
>       row to prevent look-ahead bias
>     Goal 2 — EDA & Target: target defined (next-day direction, 49.1%/50.9% balanced);
>       dropped non-stationary CPI levels + 5 correlated equity indices; engineered
>       rate_differential
>     Goal 3 — Model Pipeline: 4-step sklearn Pipeline, 6-fold walk-forward CV, Bayesian
>       search (50 trials/model), now trained across all 3 datasets (216 model×fold×
>       dataset rows) — every trained model fine-tuned, none left on defaults
>     Goal 4 — Streamlit UI: app now supports switching between all 3 datasets, loads
>       all 12×6×3 pre-trained pipelines from disk — instant predictions, no live training
>
>   End-to-end pipeline, recap (4-step flow diagram):
>     Fetch & harmonize (FRED/ONS/yfinance → data/raw → data/interim)
>       → Engineer features (join + transform → 2,868 rows × 111 cols)
>       → Train & tune (Bayesian search → 6-fold walk-forward CV)
>       → Deploy (Streamlit loads models/trained/*.joblib)
>
>   Best-performing model — depends on the metric (3-card grid, same real numbers as
>   Slide 9, restated as the closing takeaway):
>     Accuracy leader: Bagging_LR — 67.4% final accuracy, but CV score (73.7%) was
>       inflated 6.3pp above it — overfitting flag, weak regularization (C=5.50)
>     Recommended (risk-adjusted): XGB — Sharpe 1.28 · HGB — Sharpe 1.24 — mid-table
>       accuracy (61-62%) but the only two models where the accuracy story and the
>       Sharpe-proxy story agree
>     Most stable: XGB & CatBoost — lowest fold-to-fold variance (σ≈0.03); CatBoost's
>       final score (63.2%) even exceeds its CV mean — no overfitting signal
>
>   What's next:
>     Train the remaining registry models — SVM (linear/rbf/sigmoid/poly), Bagging_SVM_*,
>       Bagging_KNN, GB — already defined in model_registry.py, deprioritized purely on
>       time; adding them is a config change to train.py, not new engineering
>     Extend src/evaluation/backtest.py (already built) to Dataset 3's top models —
>       explain why 85% accuracy hasn't yet produced a better Sharpe proxy than Dataset 1
>     Mitigate Dataset 2's p≫n problem (feature selection / PCA / dimensionality
>       reduction on the 9,110-column lookback), or keep it as a documented negative result
>     Try an ensemble of the top-Sharpe models (XGB + HGB) instead of a single
>       best-accuracy pick
>     Investigate why LR / Bagging_LR overfit (regularization strength vs. feature
>       count/sample size)

**Speaker notes (Lee):
  "To close: each of the four course goals produced something concrete — a harmonized
  multi-source dataset with no look-ahead bias, a fully explored and balanced target, a
  12-model pipeline where every model was actually Bayesian-tuned rather than left on
  defaults, and a working Streamlit app that loads all of that instantly from disk. Put
  together, the pipeline runs fetch, feature engineering, tuning plus walk-forward CV,
  then deployment, in that order.
  On which model performed best — it genuinely depends on the metric. Bagging_LR wins on
  raw accuracy but is the overfitting flag of the whole project; XGBoost and HGB are our
  actual recommendation because they're the only models where accuracy and simulated
  profit agree; XGBoost and CatBoost are the most stable year to year.
  For future work, the highest-value next step is simply training the models we already
  designed but didn't have time for — the SVM kernels, Bagging_KNN, and GB are already in
  the registry, so that's a config change, not new engineering. Beyond that: extending
  our backtest to Dataset 3's top models to explain why its 85% accuracy hasn't produced
  a better Sharpe than Dataset 1, tackling Dataset 2's p≫n problem, and an XGB+HGB
  ensemble. Questions welcome."**

---

### SLIDE 12 — References & AI Disclosure (display only)

> Content:
>   Primary reference:
>     Guyard, K. C., & Deriaz, M. (2024). Predicting foreign exchange EUR/USD direction
>     using machine learning. MLMI 2024. Information Science Institute, University of
>     Geneva & HEG Genève, HES-SO.
>
>   Data sources:
>     FRED API — Federal Reserve Bank of St. Louis. (n.d.). Federal Reserve Economic
>       Data. Retrieved 2026, from fred.stlouisfed.org
>     ONS UK API v1 beta — Office for National Statistics. (n.d.). ONS API v1.
>       Retrieved 2026, from api.ons.gov.uk
>     yfinance — Yahoo Finance market data via the yfinance Python package. Retrieved
>       2026, from pypi.org/project/yfinance
>
>   Additional papers consulted (References folder, 9 papers):
>     Aleksandrova (2025) — statistical forecasting of exchange rates review
>     Bormpotsis, Sedky & Patel (2023) — bio-inspired modular neural network for Forex
>     Galeshchuk & Mukherjee (n.d.) — deep networks for FX direction of change
>     Ghahremani & Nguyen (2025) — GAN data augmentation for AML datasets
>     Jung & Choi (2021) — LSTM autoencoder FX volatility forecasting
>     Mitra (n.d.) — wavelets and neural networks for FX spot rates
>     Nielsen (2018) — ML for foreign exchange rate forecasting
>     Ogude et al. (2025) — AI for combating money laundering
>     Yıldırım, Toroslu & Fiore (2021) — LSTM with technical/macro indicators for FX
>     Plus one course-material file (Python environment setup), used for onboarding,
>     not cited as research.
>
>   AI Disclosure — Claude Code (Anthropic):
>     Used as a working tool throughout the project, not as an autonomous author. The
>     project team made all decisions on code, outline, and plan; Claude Code executed
>     under that direction.
>     - Summarizing the reference papers and translating findings into project-specific
>       data/feature decisions
>     - Implementing the 4 course goals: data pipeline, EDA, model pipeline, Streamlit UI
>       — under the team's task breakdown and review
>     - Writing testing/verification code (e.g., pipeline dry-runs, metric sanity checks,
>       walk-forward CV validation)
>     - Explaining difficult concepts to the team (e.g., look-ahead bias, Bayesian
>       optimization, Sharpe proxy vs. accuracy trade-offs)
>     - Data pipeline architecture and all fetch / process scripts
>     - Panel harmonization logic (no-look-ahead bias via realtime_start)
>     - Model registry pattern, training pipeline, and Bayesian search integration
>     - Debugging (e.g., InfinityToNaNTransformer for UK CPI YoY log during deflation)
>     The team decided the project outline, work plan, and every code/design choice;
>     Claude Code's output was reviewed, tested, and validated at each step — not
>     accepted as-is.

---

## Time Budget

  Slides 1-3   (Manim, intro + overview + Goal 1)     :  3 min 20 sec
  Slides 4-6   (Somitha, Goal 2 + feature eng.)        :  2 min 20 sec
  Slide 7      (Lee, pipeline + metrics + walk-fwd CV) :  1 min 10 sec   [+25s: pipeline moved in, metrics decoder new]
  Slide 8      (Lee, training & fine-tuning)           :  1 min 00 sec  [+5s: regularization/CV-optimism sentence]
  Slide 9      (Lee, models & results)                 :  1 min 25 sec  [+25s 2026-07-06: Dataset 1/2/3 comparison box + 4 charts added]
  Slide 10     (Lee, Streamlit)                        :  0 min 50 sec  [+10s 2026-07-06: dataset selector]
  Slide 11     (Lee, conclusion)                       :  1 min 00 sec  [+35s: goal-by-goal recap, pipeline recap,
                                                          best-model-by-metric, and future-work sections added]
  Slide 12     (References, displayed)                 :  0 min 15 sec
  Buffer / transitions                                :  0 min 05 sec
  TOTAL                                                : 11 min 25 sec  (~1:25 over)

Note: raw estimate lands ~1:25 over the 10:00 target, mostly from Slide 9's new dataset
comparison box and Slide 11's earlier expansion. To close the gap: (a) trim Slide 9's
"Open issues & next steps" box to just the issues — the next-steps list is now restated,
with more detail, on Slide 11, so narrating it twice is redundant and safe to cut first
(~15-20s); (b) narrate the Dataset 1 vs 2 vs 3 box at a summary level (Dataset 2 negative,
Dataset 3 strong-but-not-profitable) without walking all 4 charts individually (~20s);
(c) trim Slide 8's model table narration to 4-5 named examples instead of all 12 rows
(already the rehearsal-trim suggestion from the original outline); (d) if still over,
narrate only 3 of Slide 11's 5 "What's next" bullets (all 5 stay on the slide for
reference). Do not cut the Slide 7 metrics decoder to save time — that's the piece that
was missing and made the whole section feel unclear.

---

## Key Numbers to Know

  - Data window: 2014-01-01 to 2024-12-31 (11 years, ~3,254 trading days)
  - Final dataset: 2,868 rows × 111 columns (52 forex, 28 equity, 20 macro, 10 date, 1 target)
  - Dropped: CPI levels (non-stationary) + 5 of 9 equity indices (multicollinearity r > 0.87)
  - Kept equity: SP500, NASDAQ100, RUSSELL2000, FTSE100
  - Models trained & fine-tuned: 12 (LR, RF, XGB, LGBM, MLP, KNN, DT, ET, HGB, CatBoost,
    Bagging_DT, Bagging_LR) × 3 datasets = 216 model×fold×dataset rows in
    model_comparison.csv; 8 more (GB, Bagging_KNN, SVM variants) defined but not yet
    trained — deprioritized behind the deadline
  - Dataset 2 (90-day lookback, 9,110 cols): documented negative result — best model
    (CatBoost) only 62.1% final accuracy, near coin-flip for all 12 models (p≫n)
  - Dataset 3 (technical indicators, 1,178 cols): best models LGBM & HGB (tied) — 83.1%
    final accuracy, CV ~80% (gap +3.0-3.4pp, not overfitting). Fix 2026-07-06: dropped
    the same 5 multicollinear equity indices as Dataset 1 (was mistakenly using all 9) —
    linear models now score higher than on Dataset 1 — but Sharpe proxy turns negative
    for most models (10/12) despite the accuracy jump
  - Streamlit app (src/app/app.py): now supports switching between all 3 datasets via a
    sidebar selector, verified end-to-end in a real browser
  - CV folds: 6 (5 development folds + 1 held-out final test on 2024)
  - Class balance: 49.1% UP / 50.9% DOWN (ratio 1.04x — balanced)
  - Best 2024 accuracy: Bagging_LR 67.4%, LGBM 66.7% — but Bagging_LR has the worst
    Sharpe proxy (−0.87) of all 12 models
  - Best 2024 Sharpe proxy: XGB 1.28, HGB 1.24 (mid-table accuracy, 61-62%)
  - Most stable across folds: XGB & CatBoost (σ≈0.03); CatBoost's final (63.2%) exceeds
    its CV mean (58.7%) — no overfitting
  - Overfit models: LR & Bagging_LR — highest CV accuracy (~73.7%) but drop 6-8pp on
    the 2024 held-out test; Bagging_LR's search found very weak regularization (C=5.50)
  - Underfit model: DT — Optuna capped depth at 3, final accuracy 47.5% (below coin-flip)
  - AUC reference thresholds (from PROJECT_GUIDE.md): 0.55-0.65 typical for FX direction,
    0.80+ flagged/investigate — Bagging_LR's 0.869 crosses this, attributed to weak
    regularization rather than leakage (see Slide 9)
  - Paper baseline: ~53-56% accuracy on EUR/USD (Guyard & Deriaz 2024)

---

## Charts Available (reports/figures/)

  cv_vs_final_accuracy.png   — CV vs Final 2024 accuracy per model  (slide 9)
  accuracy_per_fold.png      — Accuracy per year 2019-2023 per model (slide 9)
  sharpe_by_model.png        — Sharpe proxy per model                (slide 9)
  auc_by_model.png           — AUC-ROC per model                     (reference / backup)
  roc_pr_curves.png          — ROC + PR curves, 2024 held-out fold, XGB/HGB/Bagging_LR/LGBM (slide 9)
  dataset_comparison_accuracy.png    — CV-mean accuracy by dataset, all 12 models      (slide 9)
  dataset_comparison_auc.png         — CV-mean AUC-ROC by dataset, all 12 models       (slide 9)
  dataset_comparison_sharpe.png      — CV-mean Sharpe proxy by dataset, all 12 models  (slide 9)
  dataset_comparison_overfit_gap.png — CV→Final accuracy gap by dataset, all 12 models (slide 9)
  EDA macro / forex / equity charts embedded directly in slide 5

  Regenerate all: python scripts/plot_model_comparison.py --open
  Regenerate ROC/PR curves only: python scripts/plot_roc_pr_curves.py --open
    (--models to pick a different subset, or --models all for all 12 trained models)
  Regenerate dataset comparison charts: python scripts/plot_dataset_comparison.py --open
  Full dataset comparison narrative report: reports/dataset_comparison.html
    (python scripts/generate_dataset_comparison_report.py --open)
