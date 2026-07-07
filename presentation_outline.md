# Presentation Outline — GBP/USD Direction Prediction
# Duration: 15 minutes | Date: July 8, 2026
# Source of truth: reports/draft_final_presentation.html (11 slides, deployed at
# https://bet14.github.io/ML_prediction_project/reports/draft_final_presentation.html)
# STATUS: fully re-synced 2026-07-07 to the live HTML after the Slide 7/8 rework
# (formulas box, Accuracy&Profit-by-dataset table, bias-variance trade-off charts,
# "Which model is most effective" table, tag-pill issues/next-steps). All prior
# DRAFT / "what changed" history sections have been retired — git history has that
# if it's ever needed again.

---

## Speaker Assignment (by course goal) & Time Budget — 15:00 total

| # | Slide (live H2 title)                       | Goal      | Speaker  | Budget |
|---|----------------------------------------------|-----------|----------|--------|
| 1 | Title / Problem Statement                     | —         | Manim    | 0:80   |
| 2 | Data                                           | Goal 1    | Manim    | 2:10   |
| 3 | Target Variable Definition                    | Goal 2    | Somitha  | 0:50   |
| 4 | EDA: Macro, Forex, and Equity                 | Goal 2    | Somitha  | 1:40   |
| 5 | Pre-processing & Feature Engineering          | Goal 2    | Somitha  | 2:00   |
| 6 | Model Pipeline & Walk-Forward Folds           | Goal 3    | Linh     | 1:30   |
| 7 | Hyperparameter & Model Training                | Goal 3    | Linh     | 1:30   |
| 8 | Evaluation & Results                          | Goal 3    | Linh     | 2:20   |
| 9 | Streamlit App — Goal 4                        | Goal 4    | Linh     | 0:45   |
|10 | Conclusion & Takeaways                        | Goal 3+4  | Linh     | 0:55   |
|11 | References & AI Disclosure                    | —         | (screen) | 0:00   |

Manim ≈ 2:30 · Somitha ≈ 4:30 · Linh ≈ 7:00 · Total ≈ 15:00 (references shown on
screen, no spoken notes — mention it exists, don't read it).

Team: Manimegalai Kumar-Periyasamy · Somitha Gudivada · Linh Hoang-Thuy
Course: Statistical Analysis & Machine Learning — DSA Spring 2026

---

## SLIDE 1 — Title, Problem Statement & Project Overview (Manim, ~80 sec)

> Content:
>   Title: "Predicting GBP/USD Daily Direction Using Machine Learning"
>   Course: Statistical Analysis & Machine Learning · Class: DSA Spring 2026
>   Team: Manimegalai Kumar-Periyasamy · Somitha Gudivada · Linh Hoang-Thuy
>   4-block flow diagram: Data Collection (Goal 1) → EDA (Goal 2) → Model Pipeline
>   (Goal 3) → Streamlit UI (Goal 4)
>   Project scope table: binary classification (next-day GBP/USD direction, up / not
>   up), period 2014-01-01 to 2024-12-31 (~2,868 trading days), reference paper cited
>   (Guyard & Deriaz 2024, EUR/USD, University of Geneva)

**Speaker notes (Manim):
  "Our project predicts whether the GBP/USD exchange rate will go up or not the next
  trading day — a binary classification problem. We adapted methodology from a 2024
  paper on EUR/USD and applied it to GBP/USD using 11 years of data, from 2014 to
  2024. The project follows four course goals: I'll cover how we collected the data,
  Somitha will explain our analysis, target definition, and feature engineering, and
  I'll come back to walk through the model design, training, results, and the
  Streamlit interface."**

---

## SLIDE 2 — Data (Manim, ~130 sec) — Goal 1

> Content merges what used to be two slides (collection + limitations) into one:
>
>   Block 1 — Three data categories:
>     Macro indicators — GDP, CPI, central bank rates, current account (USA + UK)
>       · Sources: FRED API, ONS UK API
>     Forex OHLCV — 13 currency pairs (GBP/USD is both feature and target)
>       · Source: yfinance
>     Equity indices — 9 indices (5 US, 4 UK) · Source: yfinance
>
>   Block 2 — Pipeline flow (now forks into 3 datasets, not 1):
>     fetch_*.py (needs network) → data/raw/ (1 CSV/series, keeps realtime_start)
>       → process_*.py (offline, pandas) → data/interim/ (6 daily panels)
>       → build_dataset.py (join, drop multicollinear, add returns/rate_differential/
>         target) → dataset_basic_daily.csv (2,868 × 111 — Dataset 1)
>           ├→ build_dataset_90day.py → dataset_90day_lookback.csv (2,778 × 9,111 —
>              Dataset 2, adds 90 lagged copies of every lag-eligible column)
>           └→ build_dataset_technical.py → dataset_technical.csv (2,778 × 1,178 —
>              Dataset 3, ~60-72 technical-indicator cols per instrument × 17
>              instruments)
>     All 3 datasets share the same train.py / walk-forward CV / Bayesian-search
>     pipeline (Slides 6-7) — only the input CSV changes.
>
>   Block 3 — Entity-Relationship Diagram: DIM_DATE → {ECONOMIC_INDICATOR,
>   MARKET_INDEX_PRICE, FOREX_PAIR_PRICE} → ML_DATASET → materializes as the 3 CSV
>   files above (same date PK, same target, different feature columns).
>
>   Block 4 — Data Limitations (2 excluded features):
>     Composite PMI (USA & UK) — not on FRED; investing.com only keeps 3-4 releases,
>       not 10 years → excluded, no free full-history source found
>     FX trading volume — Dukascopy is broker-only, not global; 10yr tick data ≈ 5
>       days to download; yfinance has none at all → excluded

**Speaker notes (Manim):
  "We collected data from three categories: macro indicators from FRED and the ONS
  API, and market data from yfinance — 13 forex pairs and 9 equity indices. The
  pipeline fetches raw CSVs, keeping the publication date so we never leak future
  information, then cleans each indicator into a daily panel. That gives us Dataset
  1 — 2,868 rows, 111 columns. From there two more build scripts fork off the same
  Dataset 1: Dataset 2 adds a 90-day lookback of lagged features, Dataset 3 adds
  technical indicators across all 17 instruments — I'll cover how those two perform
  later. This ER diagram shows how the source tables all join on date into one
  ML_DATASET entity that in practice materializes as these 3 separate files. Two
  features we investigated and had to exclude: Composite PMI has no free 10-year
  history, and FX trading volume is either broker-only or absent in yfinance
  entirely."**

---

## SLIDE 3 — Target Variable Definition (Somitha, ~50 sec) — Goal 2

> Content:
>   Task: predict whether GBP/USD close will be higher or not higher next trading
>   day, using today's macro/forex/equity features (t) to predict binary direction
>   at t+1. Binary classification, not regression (magnitude not predicted).
>   Formula: Direction(t) = 1 if close(t+1) > close(t), else 0
>   Class balance: UP (1) 1,408 days (49.1%) · DOWN (0) 1,461 days (50.9%) · ratio
>   1.04x → near-perfectly balanced
>   Rolling 1-year UP% oscillates around 50% throughout 2014-2024, no persistent drift

**Speaker notes (Somitha):
  "Our target is the next-day direction of GBP/USD close price — 1 if it goes up, 0
  otherwise. Checking class balance first: 49.1% up versus 50.9% down, ratio 1.04.
  The dataset is essentially balanced, so we don't need SMOTE, oversampling, or
  class-weight correction. The rolling chart confirms no persistent directional drift
  over the decade."**

---

## SLIDE 4 — EDA: Macro, Forex, and Equity (Somitha, ~100 sec) — Goal 2

> Content — three charted categories, each with 2-3 charts + a "Key EDA findings"
> tag-pill box at the bottom:
>
>   Macro (notebook 01): correlation heatmap (Fed↔BoE rate r≈0.94, USA↔UK CPI
>   r≈0.98 → rate_differential engineered; CPI/GDP levels I(1) → YoY used instead) +
>   missingness heatmap (gaps concentrated in early 2014, worst: USA CPI YoY 10.5%)
>
>   Forex — GBP/USD & 13 pairs (notebook 02): returns distribution (GBP/USD skew
>   −0.91, kurtosis 14.4, up to 230 for USD/CHF → RobustScaler + clip ±5σ) +
>   correlation matrix (GBP crosses cluster, USD crosses cluster) + rolling 30-day
>   volatility (Brexit 2016-07-22 peak 2843% annualised)
>
>   Equity — 9 indices (notebook 02): price series (US +300-400%, UK FTSE100 flat;
>   5/9 indices dropped for multicollinearity) + volume vs sqrt-volume (skew 1.66 →
>   0.76) + equity↔GBP/USD cross-correlation (UK positive/risk-on, US
>   weak/negative, all |r|<0.3)

**Speaker notes (Somitha):
  "Three key findings. First, the rate differential between the Fed and BoE is one
  of the clearest macro drivers of GBP/USD, so we add it as an explicit feature.
  Second, GBP/USD daily returns show extreme fat tails — kurtosis of 14, up to 230
  for USD/CHF — which is why we use RobustScaler rather than StandardScaler, plus
  clipping outliers at 5 standard deviations. Third, we started with 9 equity
  indices but correlation analysis shows 5 are near-duplicates of the others, so we
  drop them and keep 4: SP500, NASDAQ100, RUSSELL2000, FTSE100."**

---

## SLIDE 5 — Pre-processing & Feature Engineering (Somitha, ~120 sec) — Goal 2

> Content — four short blocks, then 3 class diagrams (one per final dataset):
>
>   Drop: CPI & GDP level columns (ADF test: non-stationary I(1), replaced by YoY);
>   5 of 9 equity indices for multicollinearity (DJI r=0.95 vs SP500,
>   NASDAQ_COMPOSITE r=0.99, FTSE_ALL_SHARE r=0.99, FTSE350 r=0.97, FTSE250 r=0.87)
>   → kept SP500, NASDAQ100, RUSSELL2000, FTSE100
>
>   Transform: forward-fill by realtime_start (all macro, no look-ahead); √ on
>   central bank rates; log on UK CPI YoY (both variance stabilization)
>
>   Added: equity log returns {INDEX}_ret; rate_differential = USA_rate − UK_rate
>
>   Encoded: tree models get plain int day/month/weekday; linear & distance models
>   (LR, Bagging_LR, KNN, MLP) get sin/cos cyclical pairs — same split the reference
>   paper uses (§4.4)
>
>   Class diagrams (measured from the actual rebuilt files):
>     Dataset 1 (Basic Daily): Forex 52 + Equity 28 + Macro 20 + Date 10 + Target 1
>       = 111 cols · 2,868 rows · 0.64% NaN overall
>     Dataset 2 (90-Day Lookback): 100 lag-eligible base cols × 90 lag depths =
>       9,000 + 100 base + 10 date + 1 target = 9,111 cols · 2,778 rows · 0.53% NaN
>     Dataset 3 (Technical Indicators): 111 carried-through (Dataset 1) + 780 forex
>       technical (13 pairs × 60 cols) + 288 equity technical (4 indices × 72 cols,
>       includes volume MA/WMA) = 1,178 cols · 2,778 rows · 0.083% NaN

**Speaker notes (Somitha):
  "After the EDA we knew exactly what to keep and remove. CPI price levels trend
  upward monotonically — non-stationary — so we use year-on-year inflation instead,
  and we dropped five equity indices that were near-identical to ones we kept. What
  we added: log returns for equity, the rate differential the EDA flagged as a key
  driver, and two date encodings — integers for tree models, sine-cosine pairs for
  linear models so December wraps around to January correctly. One thing to flag:
  imputation and scaling aren't in this dataset-build step — those are static,
  whole-dataset transforms computed once, while median imputation and RobustScaler
  have to be refit per CV fold, so they live inside the model pipeline Linh will
  cover next. From this base dataset we branch into two more: a 90-day lookback with
  9,111 columns, and a technical-indicators version with about 1,178 columns across
  17 instruments — Linh will show how those two actually perform."**

---

## SLIDE 6 — Model Pipeline & Walk-Forward Folds (Linh, ~90 sec) — Goal 3

> Content:
>   Expanding-window walk-forward cross-validation (no look-ahead: test year always
>   strictly after training):
>     Fold 1: Train 2014-2018 / Test 2019   Fold 2: Train 2014-2019 / Test 2020
>     Fold 3: Train 2014-2020 / Test 2021   Fold 4: Train 2014-2021 / Test 2022
>     Fold 5: Train 2014-2022 / Test 2023
>     Final:  Train 2014-2023 / Test 2024  (held out — never touched until final
>             evaluation)
>
>   Pipeline architecture (refit per fold, not once — no leakage from test into
>   train):
>     InfinityToNaNTransformer → SimpleImputer(median) → RobustScaler (conditional)
>     → Model
>     InfinityToNaNTransformer: −inf/+inf → NaN (UK_cpi_yoy_log produces −inf during
>       deflation)
>     SimpleImputer(median): fits per-column median on the training fold only
>     RobustScaler: only for scale-sensitive models (LR, MLP, KNN, Bagging_LR, SVM
>       variants); skipped for tree models; median/IQR chosen for the fat tails found
>       in EDA
>     Model: final estimator, Bayesian-searched hyperparameters, predicts
>       direction + probability
>
>   12 trained & fine-tuned models, 4 families:
>     Linear: LR, Bagging_LR (27× bootstrapped LR)
>     Trees: DT, ET, RF, Bagging_DT
>     Gradient boosting: XGB, LGBM, HGB, CatBoost
>     Other: KNN, MLP
>   (8 more defined in the registry but not yet trained — SVM ×4 kernels,
>   Bagging_SVM ×4, Bagging_KNN, GB — deprioritized behind the deadline; adding them
>   is a config change to train.py, not new engineering)

**Speaker notes (Linh):
  "Two things before the models themselves. First: GBP/USD is a time series, so we
  never use a random train/test split — that would leak future data into training.
  Instead, we use walk-forward cross-validation. The training window grows by one
  year each time. We always test on the year right after. And 2024 is held out
  completely — never touched until the final check.

  Second: every model uses the same 4-step pipeline. Clean infinite values. Fill
  missing data using only the training fold's median. Rescale, if the model needs
  it. Then fit. We repeat this six times, once per fold, so nothing leaks between
  folds.

  With that in place, we trained and tuned 12 models across four families: two
  linear models, four tree-based models, four gradient boosting models, and two
  others — KNN and a small neural net. Eight more models are already coded in our
  registry, just not trained yet — purely a time trade-off."**

---

## SLIDE 7 — Hyperparameter & Model Training (Linh, ~90 sec) — Goal 3

> Content:
>   Two-phase timeline:
>     Phase 1 — Hyperparameter Search: Optuna/TPE, 50 trials, scored on inner Folds
>       1-4, validated on Fold 5 → best_params.json (params only, no fitted model)
>     Phase 2 — Final Refit per Fold: reloads Phase 1's frozen best_params, refits
>       independently on all 6 folds (1-5 + Final) → 6 .joblib files +
>       model_comparison.csv. Same hyperparameters reused every fold — not
>       re-searched, not a single combined model.
>
>   12 models — regularization actually tuned (real values, Dataset 1):
>     LR — L1, C=0.68 · Bagging_LR — n=27, C=5.50 (weak — flagged next slide)
>     RF — depth=16, leaf=10 · ET — depth=13, sqrt · DT — depth=3, split=6 (capped
>       shallow — underfits) · Bagging_DT — depth=3, n=29
>     KNN — k=8, euclidean · MLP — alpha=0.0025, 236 units
>     XGB — depth=5, lr=0.015 · LGBM — leaves=26, lr=0.094 · HGB — L2=4.89, depth=6
>     CatBoost — depth=5, lr=0.016
>     Only LR and HGB carry a classic explicit L1/L2 term; trees regularize
>     structurally via depth/leaf/sampling limits; MLP uses L2 weight decay.
>
>   Extra material (collapsed — expand if time permits): why Bayesian over
>   Grid/Random (TPE builds a probabilistic model from every prior trial vs. Grid's
>   combinatorial explosion / Random's no-memory sampling); inner-validation F1 did
>   NOT predict final generalization — Bagging_LR had the highest inner F1 (0.756) of
>   all 12 models yet the worst final Sharpe/Profit.

**Speaker notes (Linh):
  "Every model goes through the same tuning steps. First, a Bayesian search — 50
  trials — tunes hyperparameters on folds 1 through 4, then checks them on fold 5.
  Once we pick the best settings, we freeze them. Then we refit the model six
  times, once per fold — we never search again.

  Two results are worth flagging now, because they explain the next slide. Bagging
  LR's search landed on very weak regularization, C equals 5.50. And the Decision
  Tree got capped at depth 3.

  One more important point: the tuning score does not reliably predict how well a
  model generalizes. Bagging_LR had the best tuning score of all 12 models — but,
  as you'll see, one of the worst real results. That's exactly why we don't stop
  here, and validate on genuinely held-out years next."**

---

## SLIDE 8 — Evaluation & Results (Linh, ~140 sec) — Goal 3

> Content, in the order it appears on the slide:
>
>   Formulas — Accuracy & Profit (Guyard & Deriaz 2024, §5.3), computed annually (a
>   single fit on 2014-2023, predicting the full 2024 test year in one pass):
>     Direction(t) = 1 if Close(t+1) > Close(t), else 0
>     Accuracy = (1/N) · Σ 1{ŷ(i) = y(i)} · N = test days · 50% = coin flip
>     Profit — long/short, P(0)=1: P(t) = P(t−1) × C(t)/C(t−1) if predicted UP (go
>       long); P(t) = P(t−1) × C(t−1)/C(t) if predicted DOWN (go short); Profit% =
>       (P(T) − 1) × 100 → positive = made money, negative = lost money even if
>       accuracy looks fine
>
>   Accuracy & Profit by model and dataset (2024, Annual scheme) — 12 models × 3
>   datasets:
>     Dataset 1 highlights: Bagging_LR best accuracy (67.4%) but worst-ish Profit
>       (−3.79%); XGB (+10.39%) and HGB (+11.83%) top Profit despite mid-table
>       accuracy (61.3%/62.1%)
>     Dataset 3: every model except DT scores 70-83% accuracy, yet 10/12 still have
>       negative Profit — accuracy jump did not carry over to Profit
>
>   Bias-variance trade-off — 3 scatter charts (x = fold-to-fold accuracy σ across
>   inner folds 1-5, y = final 2024 accuracy), 4 models labeled per dataset:
>     Dataset 1: CatBoost = best trade-off (63.2% acc, low variance); Bagging_LR
>       tops accuracy (67.4%) at the highest variance; DT is the lone high-bias case
>       (47.5%, below coin flip)
>     Dataset 2: whole cloud packs into a tight 48-62% band regardless of variance
>       (p≫n signal dilution) — visual confirmation of a documented negative result
>     Dataset 3: boosting/tree cluster (LGBM, HGB, CatBoost, ET, XGB, Bagging_DT)
>       sits in the ideal low-variance/high-accuracy corner (82-83%); HGB = best
>       trade-off; DT is a dramatic outlier — highest variance AND only sub-50%
>       accuracy on this dataset
>
>   Dataset 1 vs 2 vs 3 — does more data help?
>     Dataset 2 (90-day lookback, 9,111 cols): negative result, near coin-flip for
>       every model, p≫n
>     Dataset 3 (technical indicators, 1,178 cols): strong consistent win for every
>       tree/boosting model (80-83% acc, 0.89-0.91 AUC) — but Sharpe proxy still
>       negative for 10/12 models despite the accuracy jump
>
>   Which model is most effective? — depends on the metric (Dataset 1):
>     Accuracy winner: Bagging_LR 67.4% (but CV score 73.7% was inflated 6.3pp)
>     Risk-adjusted winner: XGB (Sharpe 1.28) · HGB (Sharpe 1.24) — the only models
>       where accuracy and Sharpe stories agree
>     Most stable: XGB & CatBoost (lowest fold-to-fold variance)
>     Worst: DT 47.5%, below coin flip
>     → Recommendation: XGB or HGB for a live/practical setting
>
>   4 dataset-comparison charts (accuracy / AUC / Sharpe / overfit-gap by dataset) +
>   4 per-model charts (CV vs Final accuracy, accuracy per fold, Sharpe by model,
>   ROC/PR curves) — Bagging_LR's AUC (0.869) crosses the >0.80 "investigate for
>   leakage" reference point; attributed to weak regularization (C=5.50), not a data
>   leak, since the same high-CV/weak-final pattern shows up across accuracy, F1,
>   and Sharpe too.
>
>   Open issues & next steps (tag-pill chips):
>     Issues: accuracy leader ≠ profit leader · LR/Bagging_LR overfit (6-8pp
>       CV→Final drop) · Dataset 2 negative result (p≫n) · Dataset 3 high accuracy
>       but weak Sharpe · 2024 test = 1 year, noisy · SVM/Bagging_KNN/GB not trained
>     Next steps: investigate LR/Bagging_LR overfitting · extend backtest.py to
>       Dataset 3 top models · try XGB+HGB ensemble · mitigate Dataset 2 p≫n
>       (feature selection/PCA) · train remaining registry models

**Speaker notes (Linh):
  "We check two numbers: accuracy, and Profit. Profit uses the same long/short
  formula as the reference paper. It asks a simple question: if you traded on this
  prediction, would you actually make money in 2024? Everything here is the true
  2024 test year — never touched during tuning.

  Two things stand out. First, on Dataset 1, Bagging_LR wins on accuracy, but it's
  one of the worst models on Profit. Meanwhile XGB and HGB are mid-table on
  accuracy, but top the Profit ranking. Second, on Dataset 3, almost every tree and
  boosting model reaches 70 to 83% accuracy. But 10 of those 12 models still lose
  money. So higher accuracy did not mean higher profit.

  The three bias-variance charts show this visually. On Dataset 1, CatBoost gives
  up a little accuracy for much better stability than the accuracy leader. On
  Dataset 2, every model sits near the coin-flip line, no matter how stable it is
  — the signal just isn't there. On Dataset 3, almost every tree and boosting
  model lands in the best corner, high accuracy and low variance, except the
  Decision Tree, which is both the least stable model and the only one below a
  coin flip.

  Zooming out: Dataset 2 is a clear negative result. Dataset 3 wins on accuracy,
  but that win doesn't carry over to risk-adjusted returns. So which model is
  'best' depends on what you're measuring. Bagging_LR wins on raw accuracy. But we
  recommend XGB and HGB, because they're the only two models where accuracy and
  Sharpe ratio agree."**

---

## SLIDE 9 — Streamlit App (Linh, ~45 sec) — Goal 4

> Content:
>   Flow: Dataset selector (1/2/3) → Model selector (12 trained models) →
>   Pipeline.predict() (loaded from models/trained/*.joblib) → Direction +
>   confidence (up/down + probability)
>   No live training in the app — all 12 × 6 × 3 = 216 pipelines are pre-fit and
>   loaded from disk, so switching dataset/model re-renders instantly
>   Status: src/app/app.py built, verified end-to-end in a real browser (dataset
>   switch correctly re-triggers load_dataset/available_models/load_pipeline, not a
>   stale cache); dataset-comparison charts also rendered in-app with a link to the
>   full reports/dataset_comparison.html narrative

**Speaker notes (Linh):
  "The Streamlit app lets a user pick a dataset, pick one of the 12 trained
  models, and get an instant prediction — up or down — with a confidence score.
  Everything is pre-trained and loaded from disk, so nothing trains live. This
  session we added the dataset selector, so the app now works across all 3
  datasets. We also tested it in a real browser, and confirmed switching datasets
  correctly reloads the right models, instead of showing old results."**

---

## SLIDE 10 — Conclusion & Takeaways (Linh, ~55 sec)

> Content:
>   How the 4 goals were executed: Goal 1 (FRED/ONS/yfinance, harmonized daily panel,
>   look-ahead-safe) · Goal 2 (target defined, EDA-driven drops/adds) · Goal 3 (12
>   models × 3 datasets, 4-step pipeline, 6-fold walk-forward CV, Bayesian search —
>   216 model×fold×dataset rows) · Goal 4 (Streamlit app, all 3 datasets, no live
>   training)
>   End-to-end pipeline recap: Fetch & harmonize → Engineer features → Train & tune
>   → Deploy
>   Best-performing model — depends on the metric: Accuracy leader Bagging_LR
>   (67.4%, but overfitting flag) · Recommended (risk-adjusted) XGB/HGB (Sharpe
>   1.28/1.24) · Most stable XGB & CatBoost
>   What's next: train remaining registry models (SVM kernels, Bagging_KNN, GB) ·
>   extend backtest.py to Dataset 3's top models · mitigate Dataset 2's p≫n problem ·
>   try an XGB+HGB ensemble · investigate LR/Bagging_LR overfitting

**Speaker notes (Linh):
  "To wrap up: we completed all four course goals. We collected data through a
  look-ahead-safe pipeline. We ran EDA-driven feature engineering. We trained and
  validated 12 models with proper walk-forward cross-validation, across all 3
  datasets. And we built a working Streamlit app on top of it.

  If you remember one thing: there is no single best model. It depends whether
  you care about raw accuracy, or whether the strategy actually makes money. We
  recommend XGB and HGB, because they're the only models where those two stories
  agree. Next steps: train the remaining registry models, extend our backtest to
  Dataset 3, and dig into why more data didn't automatically mean better trading
  results."**

---

## SLIDE 11 — References & AI Disclosure (displayed on screen, no speaker notes)

> Content: primary reference (Guyard & Deriaz 2024), 3 data source citations
> (FRED, ONS, yfinance), 9 additional consulted papers, and an AI Disclosure section
> describing Claude Code's role as a working tool (implementation under the team's
> direction, not an autonomous author) — team made all decisions on code, outline,
> and plan.

(No speaker notes — shown on screen while transitioning to Q&A.)
