# Presentation Outline — GBP/USD Direction Prediction
# Duration: 10 minutes | Date: July 8, 2026
# Source of truth: reports/draft_final_presentation.html (12 slides) — this outline mirrors it exactly

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
>   Middle — Pipeline flow (table form, one column per stage):
>     fetch_*.py (pull raw data, needs network)
>       → data/raw/ (landing zone, 1 CSV/series, keeps realtime_start to prevent look-ahead bias)
>       → process_*.py (clean & harmonize into daily panel, offline, pure pandas)
>       → data/interim/ (6 panels, common daily date index 2014–2024)
>       → build_dataset.py (join on date, drop multicollinear, add returns/rate_differential/target)
>       → data/processed/dataset_basic_daily.csv (2,868 rows × 111 cols → train.py)
>
>   Bottom — Entity-Relationship Diagram:
>     DIM_DATE (date PK, day/month/weekday, cyclical sin/cos)
>       → has → ECONOMIC_INDICATOR, MARKET_INDEX_PRICE, FOREX_PAIR_PRICE
>       → feeds → ML_DATASET (date PK, direction_target, dataset_type)
>
>   Bottom note: 2014-01-01 to 2024-12-31 · ~3,254 trading days

**Speaker notes (Manim):
  "We collected data from three categories: macro indicators from FRED and the ONS API,
  and market data from yfinance — 13 forex pairs and 9 equity indices.
  The pipeline has two stages. Fetch scripts pull from APIs and save raw CSVs, keeping the
  publication date so we never leak future information. Process scripts clean each
  indicator into a daily panel and can run fully offline. The final merged dataset has
  2,868 rows and 111 columns. This ER diagram shows how the source tables — dated
  economic indicators, market index prices, and forex pair prices — all join on date
  into the single ML-ready dataset."**

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
  had 12 months of history to compute a year-on-year figure."**

---

### SLIDE 7 — Model Design & Walk-Forward CV (Lee, ~45 sec)

> Content:
>   Diagram of expanding-window walk-forward cross-validation:
>     Fold 1: Train 2014-2018 / Test 2019
>     Fold 2: Train 2014-2019 / Test 2020
>     Fold 3: Train 2014-2020 / Test 2021
>     Fold 4: Train 2014-2021 / Test 2022
>     Fold 5: Train 2014-2022 / Test 2023
>     Final:  Train 2014-2023 / Test 2024  (held out — never touched until final evaluation)
>   Explain WHY: time series → no random split → no data leakage

**Speaker notes (Lee):
  "Because GBP/USD is a time series, a random train/test split would let the model see
  future data during training — that is data leakage. Instead we use expanding-window
  walk-forward cross-validation: the training window grows by one year at a time, and we
  always test on the year immediately after. The 2024 data is a true held-out set, never
  touched until the final evaluation."**

---

### SLIDE 8 — Model Training & Fine-Tuning (Lee, ~55 sec) — NEW SLIDE

> Content:
>   Training workflow (confirms every model was actually fine-tuned, not left on defaults):
>     Bayesian search (Optuna/TPE, 50 trials, inner folds 1-4)
>       → Inner validation (fold 5, before touching final test)
>       → best_params.json (saved per model)
>       → Refit on all 6 folds (train.py loads best_params automatically)
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
>   Bias-variance tradeoff — read from the real fold numbers:
>     High variance (overfit): LR & Bagging_LR — both ~73.7% mean CV accuracy (highest of
>       all 12) but final 2024 accuracy drops to 65.5% / 67.4% (−8.2pp / −6.3pp).
>     Low variance (well-generalized): XGB & CatBoost — lowest fold-to-fold swings
>       (σ≈0.03). XGB's CV→Final gap is only +1.0pp; CatBoost's final (63.2%) is actually
>       higher than its CV mean (58.7%) — no overfitting signal.
>     High bias (underfit): DT — Optuna capped max_depth at 3, too shallow to separate
>       classes. Final accuracy 47.5%, below the 50% coin-flip baseline.

**Speaker notes (Lee):
  "Every one of the 12 trained models went through the same pipeline: a 50-trial
  Bayesian search on the first four folds, validated on a fifth inner fold, then
  refit with the best hyperparameters across all six walk-forward folds. Only LR and
  HGB carry a classic textbook L1/L2 penalty; the tree ensembles control complexity
  structurally, through depth and leaf limits instead.
  Looking at the real numbers: LR and Bagging_LR scored the highest cross-validation
  accuracy of all 12 models, around 73.7%, but that's a red flag — their accuracy drops
  6 to 8 points on the true 2024 test, which is classic overfitting. XGBoost and
  CatBoost barely move between CV and the final test — CatBoost's final score is
  actually higher than its CV average. And the Decision Tree alone underfits: Optuna
  itself capped it at depth 3, and it ends up below a coin flip on 2024."**

---

### SLIDE 9 — Models & Results (Lee, ~75 sec)

> Content:
>   Pipeline architecture:
>     InfinityToNaNTransformer → SimpleImputer(median) → [RobustScaler, conditional] → Model
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
>   Model status:
>     Trained & fine-tuned (12): LR, RF, XGB, LGBM, MLP, KNN, DT, ET, HGB, CatBoost,
>       Bagging_DT, Bagging_LR — full walk-forward CV (6 folds) + Bayesian search
>       (50 trials each).
>     Planned next, time allowing: GB, Bagging_KNN, SVM_linear/rbf/sigmoid/poly,
>       Bagging_SVM_* — already defined in the model registry; kernel SVMs are notably
>       slower to fit at 2,868 rows × 111 features, so deprioritized behind the
>       presentation deadline. Adding them later is a config change to train.py, not new
>       engineering (registry pattern in src/models/model_registry.py).
>
>   Three charts (real 2024 held-out results):
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
>   Which model is most effective? — depends on the metric:
>     Accuracy: Bagging_LR — 67.4% (but CV score 73.7% was inflated 6.3pp above this)
>     Risk-adjusted (Sharpe proxy): XGB — 1.28 · HGB — 1.24 (mid-table accuracy, 61-62%,
>       but only models with strongly positive Sharpe)
>     Most stable across CV folds: XGB · CatBoost (lowest year-to-year variance)
>     Worst: DT — 47.5% (below the 50% coin-flip baseline)
>     Recommendation: XGB or HGB for a live/practical setting — the only models where
>     the accuracy story and the Sharpe story agree.
>
>   Open issues & next steps:
>     Issues: accuracy leader ≠ profit leader (Bagging_LR best accuracy, worst Sharpe);
>       LR/Bagging_LR generalize worse than CV suggests; Sharpe proxy has no transaction
>       costs/slippage yet; final test is a single year (~260 days, one regime, noisy);
>       SVM/Bagging_KNN/GB defined but not trained yet.
>     Next steps: investigate LR/Bagging_LR overfitting; build
>       src/evaluation/backtest.py with realistic transaction costs; try an ensemble of
>       top-Sharpe models (XGB + HGB); build Dataset 2 (90-day lookback) and Dataset 3
>       (technical indicators) — not yet built; train remaining registry models as time
>       allows.
>
>   Extra material (collapsed, expand if time/questions permit) — Bayesian hyperparameter
>   search:
>     Method: Optuna, Tree-structured Parzen Estimator (TPE) sampler.
>     Goal: for each of the 12 trained models, maximize F1-macro on an inner
>       train/validation split, before the model sees the 6 walk-forward CV folds.
>     Budget: 50 trials per model, single-stage (no staged feature selection).
>     Why F1-macro not accuracy: balances both classes; defensible default even though
>       UP/DOWN are already near-balanced (49.1%/50.9%).
>     Output: best params saved to models/search_results/*_best_params.json, reused to
>       fit the final walk-forward pipelines.
>     What the results actually showed: inner-validation F1 did NOT predict which model
>       generalized best. Bagging_LR scored the highest inner F1 of all 12 models
>       (0.756) yet had the worst Sharpe on the true 2024 test. XGB scored a much lower
>       inner F1 (0.617) but generalized the most consistently — the search optimizes a
>       proxy metric on a single inner split, not a substitute for walk-forward
>       validation on genuinely held-out time.
>     Why Bayesian over Grid/Random: Grid Search cost explodes combinatorially and
>       wastes trials on obviously bad regions. Random Search covers high-dimensional
>       spaces better but has no memory — trial 50 is as blind as trial 1. Bayesian
>       (Optuna/TPE) builds a probabilistic model of hyperparameters→score from every
>       prior trial and samples the next candidate from promising regions — fewer
>       trials needed for the same quality, relevant since some models (Bagging_LR, MLP)
>       take minutes per fit.

**Speaker notes (Lee):
  "The pipeline has three stages before the model: an infinity-to-NaN cleanup step —
  needed because our UK CPI log transform produces negative infinity during deflation
  periods — then median imputation, then a conditional RobustScaler that only applies
  to scale-sensitive models like LR, MLP, and KNN, since tree models split on raw
  thresholds and don't need it.
  We trained and fully fine-tuned 12 of the models in our registry; a few kernel SVMs
  and some remaining ensembles are defined but were deprioritized behind today's
  deadline — adding them later is just a config change, not new engineering.
  On the real 2024 held-out results: Bagging_LR and LGBM top the accuracy leaderboard,
  at 67 and 66 percent. But accuracy alone is misleading here — if you actually traded
  on these predictions, Bagging_LR has the worst simulated Sharpe of all twelve models,
  while XGBoost and HGB, sitting mid-table on accuracy, have the only strongly positive
  Sharpe ratios. So our recommendation for a live setting is XGBoost or HGB — they're
  the only models where the accuracy story and the profit story agree. The open issues
  slide is here mainly for questions: our Sharpe proxy doesn't yet model transaction
  costs, and 2024 is a single test year, so it's one market regime and a noisy
  estimate."**

---

### SLIDE 10 — Streamlit App — Goal 4 (Lee, ~40 sec)

> Content:
>   App data flow:
>     User input (macro/forex/equity values for a day)
>       → Model selector (pick from the 12 trained models)
>       → Pipeline.predict() (loaded from models/trained/*.joblib)
>       → Direction + confidence (up/down + probability)
>     No live training in the app — all 12 models × 6 walk-forward folds are pre-fit and
>     loaded from disk, so predictions render instantly.
>
>   Three feature cards:
>     Feature input form — manual entry of macro/forex/equity feature values for a day
>     Prediction output — direction (up/down) + confidence, from a pre-trained model of choice
>     Feature importance chart — all 12 models × 6 folds pre-loaded, instant load
>
>   Status:
>     src/app/app.py — Built, 169 lines, verified running via streamlit run
>     Trained models available to load — 12 models × 6 walk-forward folds
>     (models/trained/*.joblib)

**Speaker notes (Lee):
  "This app doesn't train anything live — all 12 models times 6 folds were already
  trained and saved to disk by train.py. The app just lets you pick one and instantly
  see how it performed: direction and confidence for a chosen day, and — for tree-based
  models — which features it relied on most. We've verified it actually runs end to end
  with streamlit run, at 169 lines of code."**

> Presentation talking points (extra material, use as needed):
>   - Architecture point: **train once, demo many times** — decouples the expensive
>     training step from the interactive demo, which is why the UI is instant.
>   - If asked "why 12 models and not more" — mention the registry pattern makes adding
>     the remaining SVM/GB/Bagging_KNN variants a config change, not new engineering; they
>     were deprioritized purely on time, not because they don't fit the pipeline.

---

### SLIDE 11 — Conclusion & Takeaways (Lee, ~25 sec)

> Content:
>   Three cards:
>     01. Reproduced research methodology — adapted a published EUR/USD paper's
>         methodology to a new currency pair, GBP/USD
>     02. Built a full ML pipeline — multi-source data → feature engineering →
>         walk-forward CV → Bayesian tuning
>     03. Delivered a live app — packaged into an interactive Streamlit application

**Speaker notes (Lee):
  "To summarize: we replicated and adapted published research, built a complete end-to-end
  ML pipeline for a real financial prediction problem, and delivered it as an interactive
  application. Questions welcome."**

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
  Slide 7      (Lee, walk-forward CV)                  :  0 min 45 sec
  Slide 8      (Lee, training & fine-tuning)           :  0 min 55 sec
  Slide 9      (Lee, models & results)                 :  1 min 15 sec
  Slide 10     (Lee, Streamlit)                        :  0 min 40 sec
  Slide 11     (Lee, conclusion)                       :  0 min 25 sec
  Slide 12     (References, displayed)                 :  0 min 15 sec
  Buffer / transitions                                :  0 min 05 sec
  TOTAL                                                : 10 min 00 sec

Note: adding the new "Model Training & Fine-Tuning" slide pushed the deck from 10 to 12
slides. Timing above is tight — if running long in rehearsal, trim slide 8's model table
narration to 2-3 named examples (LR/HGB regularization contrast, DT underfit) instead of
walking all 12 rows.

---

## Key Numbers to Know

  - Data window: 2014-01-01 to 2024-12-31 (11 years, ~3,254 trading days)
  - Final dataset: 2,868 rows × 111 columns (52 forex, 28 equity, 20 macro, 10 date, 1 target)
  - Dropped: CPI levels (non-stationary) + 5 of 9 equity indices (multicollinearity r > 0.87)
  - Kept equity: SP500, NASDAQ100, RUSSELL2000, FTSE100
  - Models trained & fine-tuned: 12 (LR, RF, XGB, LGBM, MLP, KNN, DT, ET, HGB, CatBoost,
    Bagging_DT, Bagging_LR); 8 more (GB, Bagging_KNN, SVM variants) defined but not yet
    trained — deprioritized behind the deadline
  - CV folds: 6 (5 development folds + 1 held-out final test on 2024)
  - Class balance: 49.1% UP / 50.9% DOWN (ratio 1.04x — balanced)
  - Best 2024 accuracy: Bagging_LR 67.4%, LGBM 66.7% — but Bagging_LR has the worst
    Sharpe proxy (−0.87) of all 12 models
  - Best 2024 Sharpe proxy: XGB 1.28, HGB 1.24 (mid-table accuracy, 61-62%)
  - Most stable across folds: XGB & CatBoost (σ≈0.03); CatBoost's final (63.2%) exceeds
    its CV mean (58.7%) — no overfitting
  - Overfit models: LR & Bagging_LR — highest CV accuracy (~73.7%) but drop 6-8pp on
    the 2024 held-out test
  - Underfit model: DT — Optuna capped depth at 3, final accuracy 47.5% (below coin-flip)
  - Paper baseline: ~53-56% accuracy on EUR/USD (Guyard & Deriaz 2024)

---

## Charts Available (reports/figures/)

  cv_vs_final_accuracy.png   — CV vs Final 2024 accuracy per model  (slide 9)
  accuracy_per_fold.png      — Accuracy per year 2019-2023 per model (slide 9)
  sharpe_by_model.png        — Sharpe proxy per model                (slide 9)
  auc_by_model.png           — AUC-ROC per model                     (reference / backup)
  EDA macro / forex / equity charts embedded directly in slide 5

  Regenerate all: python scripts/plot_model_comparison.py --open
