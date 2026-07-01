# Presentation Outline — GBP/USD Direction Prediction
# Duration: 10 minutes | Date: July 8, 2026

---

## Speaker Assignment

- Manim   : Goal 1 — Data Collection & Harmonization (slides 2-3)
- Somitha : Goal 2 — Target, EDA & Feature Engineering (slides 4-6)
- Lee     : Introduction + Goal 3 — Model + Goal 4 — Streamlit + Conclusion (slides 1, 7-9)
- Slide 10 (References & AI Disclosure) — displayed on screen, no speaker notes needed

---

## Slide-by-Slide Script

### SLIDE 1 — Title, Problem Statement & Project Overview (Lee, ~75 sec)

Content:
  Top half:
    Title: "Predicting GBP/USD Daily Direction Using Machine Learning"
    Subtitle: Adapted from Guyard & Deriaz (2024), EUR/USD → GBP/USD
    Names + course name

  Bottom half:
    4-block flow diagram: Data Collection → EDA → Model Pipeline → Streamlit UI
    Each block labeled with the course goal number (Goal 1 / 2 / 3 / 4)

Speaker notes (Lee):
  "Our project predicts whether the GBP/USD exchange rate will go up or down the next
  trading day — a binary classification problem. We adapted methodology from a 2024 paper
  on EUR/USD and applied it to GBP/USD using 11 years of data, from 2014 to 2024.
  The project follows four course goals. Manim will cover how we collected the data,
  Somitha will explain our analysis, target definition, and feature engineering,
  and I will walk through the model and the interface."

---

### SLIDE 2 — Data Sources & Collection Pipeline (Manim, ~70 sec)

Content:
  Left half — Three data categories:
    1. Macro indicators — GDP, CPI, central bank rates, current account (USA + UK)
       Sources: FRED API, ONS UK API
    2. Forex OHLCV — 13 currency pairs (GBP/USD is both feature and target)
       Source: yfinance
    3. Equity indices — 9 indices (5 US, 4 UK)
       Source: yfinance

  Right half — Pipeline flow:
    fetch_*.py (needs network)
      → data/raw/   (raw CSVs: date, realtime_start, value)
      → process_*.py (runs offline, pure pandas)
      → data/interim/  (6 daily-indexed panels, 2014–2024)
      → build_dataset.py
      → data/processed/dataset_basic_daily.csv  (2,868 rows × 110 cols)

  Bottom note: 2014-01-01 to 2024-12-31 · ~3,254 trading days

Speaker notes (Manim):
  "We collected data from three categories: macro indicators from FRED and the ONS API,
  and market data from yfinance — 13 forex pairs and 9 equity indices.
  The pipeline has two stages. Fetch scripts pull from APIs and save raw CSVs.
  Process scripts clean each indicator into a daily panel and can run offline.
  The final merged dataset has 2,868 rows and 110 columns."

---

### SLIDE 3 — Data Limitations & Panel Harmonization (Manim, ~70 sec)

Content:
  Top half — Two features investigated and excluded:

    Composite PMI (USA and UK):
      Not published on FRED. investing.com only retains the last 3-4 releases — not 10 years.
      No free full-history source found → excluded from feature set.

    FX trading volume:
      Dukascopy provides only broker-network volume, not global market volume.
      10 years of tick data = ~5 days of download time, then hourly aggregation.
      yfinance carries no FX volume at all.
      → excluded from model.

  Bottom half — How data is time-aligned without look-ahead bias:

    Problem: macro indicators release monthly or quarterly and get revised later.
    A naive join on the period date would use data before it was published.

    Solution (build_known_as_of):
      Each raw CSV has a realtime_start column — the actual publication date.
      For every trading day: look backward and attach the latest value whose
      realtime_start is on or before that day.
      → each row only sees what was genuinely public on that date.

    days_since_update: how stale each reading is → fed as an explicit model feature.

    Transforms applied in process_*.py:
      Central bank rates → sqrt  (stabilises variance)
      UK CPI YoY → log           (normalises right skew)
      CPI level columns dropped  (ADF test: non-stationary I(1))

Speaker notes (Manim):
  "Two data sources had to be excluded. Composite PMI has no free 10-year history and
  FX trading volume is either broker-only or absent in yfinance.
  For the remaining data, the key challenge is time alignment. We use each value's actual
  publication date so the model never sees a revision before it was officially released.
  The days_since_update column tells the model how stale any given reading is."

---

### SLIDE 4 — Target Variable Definition (Somitha, ~40 sec)

Content:
  Formula:
    Direction(t) = 1  if close(t+1) > close(t)
    Direction(t) = 0  if close(t+1) <= close(t)
  Bar chart: class balance
    UP (1):   1,408 days — 49.1%
    DOWN (0): 1,461 days — 50.9%
    Ratio: 1.04x → near-perfectly balanced
  Rolling 1-year UP% chart: oscillates around 50% throughout 2014-2024

Speaker notes (Somitha):
  "Our target is the next-day direction of GBP/USD close price — 1 if it goes up, 0
  otherwise. Checking the class balance is the first thing we do: 49.1% up versus 50.9%
  down, ratio 1.04. The dataset is essentially balanced, which means we do not need
  SMOTE, oversampling, or class-weight correction. The rolling chart confirms no
  persistent directional drift over the decade."

---

### SLIDE 5 — EDA: Macro, Forex, and Equity (Somitha, ~60 sec)

Content:
  Three finding groups, one chart each:

  Macro (notebook 01):
    - CPI YoY comparison USA vs UK: both spike to ~10% in 2022, then converge back
    - Rate differential (Fed minus BoE): negative 2014-2016, compressed 2017-2021,
      positive 2022-2023 as Fed hiked faster than BoE → added as engineered feature
    - ADF stationarity: GDP and CPI level are I(1) → only YoY forms used as features

  GBP/USD and forex (notebook 02):
    - Daily returns: mean −0.008%/day, std 0.57%, skew −0.91, kurtosis 14.4
      → fat tails → RobustScaler used, not StandardScaler
    - Largest single-day drop: −7.6% on 2016-06-24 (Brexit referendum result)
    - EUR_GBP kurtosis = 109, GBP_CHF kurtosis = 173 → clip at ±5σ before training

  Equity (notebook 02):
    - US indices (NASDAQ100, SP500) +300-400% from 2014-2024; UK FTSE100 largely flat
    - Multicollinearity: 5 of 9 indices dropped
      (DJI r=0.95 with SP500, NASDAQ_COMPOSITE r=0.99 with NASDAQ100,
       FTSE350 r=0.97 with FTSE100, FTSE250 and FTSE_ALL_SHARE similar)
      → 4 kept: SP500, NASDAQ100, RUSSELL2000, FTSE100
    - UK FTSE100 positively correlated with GBP/USD returns; US indices weakly negative

Speaker notes (Somitha):
  "Three key findings. First, the rate differential between the Fed and BoE is one of
  the clearest macro drivers of GBP/USD — we will add it as an explicit feature.
  Second, GBP/USD daily returns show extreme fat tails — kurtosis of 14 — which is why
  we use RobustScaler rather than StandardScaler in the model pipeline. Third, we started
  with 9 equity indices but correlation analysis shows 5 are near-duplicates of the
  others, so we drop them and keep 4."

---

### SLIDE 6 — Feature Engineering & Building the Model Dataset (Somitha, ~55 sec)

Content:
  Left half — What was DROPPED (decisions justified by EDA):

    CPI level columns (USA_cpi_value, UK_cpi_value):
      ADF test: non-stationary I(1) — trended monotonically 100→130 over 11 years.
      → replaced by CPI Year-on-Year % (stationary, mean-reverting).

    5 of 9 equity indices — multicollinearity confirmed in notebook 03:
      DJI             r = 0.954 with SP500       → dropped
      NASDAQ_COMPOSITE  r = 0.992 with NASDAQ100  → dropped
      FTSE_ALL_SHARE  r = 0.993 with FTSE100     → dropped
      FTSE350         r = 0.974 with FTSE100     → dropped
      FTSE250         r = 0.872 with FTSE_ALL_SHARE → dropped
      Kept: SP500, NASDAQ100, RUSSELL2000, FTSE100

  Right half — What was ADDED / ENCODED:

    Equity log returns:
      {INDEX}_ret = log(close_t / close_{t-1})
      Log-return is stationary and compressible — suitable for ML.

    Engineered macro feature:
      rate_differential = USA_central_bank_rate − UK_central_bank_rate
      Captures the interest rate spread that directly drives GBP/USD capital flows.

    Date encoding — two versions for different model families:
      Tree models (RF, XGB, CatBoost):
        day (int), month (int), weekday (int, 0 = Monday)
      Linear models & MLP:
        day_sin, day_cos, month_sin, month_cos, weekday_sin, weekday_cos
        Cyclical encoding — so December and January are treated as adjacent.

  Final result: dataset_basic_daily.csv — 2,868 rows × 110 columns

Speaker notes (Somitha):
  "After the EDA we knew exactly what to keep and what to remove. CPI price levels
  trend upward monotonically over 11 years — that is non-stationary, which misleads
  linear models. We use year-on-year inflation instead. We dropped five equity indices
  because they were near-identical to ones we kept — correlations above 0.87.
  What we added: log returns to make equity stationary, a rate differential capturing
  the Fed-versus-BoE spread which the EDA showed was a key driver, and date encodings
  in two forms — integers for tree models and sine-cosine pairs for linear models so
  that the calendar wraps around correctly, with December connecting back to January."

---

### SLIDE 7 — Model Design & Walk-Forward CV (Lee, ~60 sec)

Content:
  Diagram of expanding-window walk-forward cross-validation:
    Fold 1: Train 2014-2018 / Test 2019
    Fold 2: Train 2014-2019 / Test 2020
    Fold 3: Train 2014-2020 / Test 2021
    Fold 4: Train 2014-2021 / Test 2022
    Fold 5: Train 2014-2022 / Test 2023
    Final:  Train 2014-2023 / Test 2024  (held out — never touched until final evaluation)
  Explain WHY: time series → no random split → no data leakage

Speaker notes (Lee):
  "Because GBP/USD is a time series, a random train/test split would let the model see
  future data during training — that is data leakage. Instead we use expanding-window
  walk-forward cross-validation: the training window grows by one year at a time, and we
  always test on the year immediately after. The 2024 data is a true held-out set, never
  touched until the final evaluation."

---

### SLIDE 8 — Models, Results & Streamlit Interface (Lee, ~90 sec)

Content:
  Top section — Pipeline architecture (one line):
    InfinityToNaNTransformer → SimpleImputer(median) → [RobustScaler] → model
    22 models total · Bayesian hyperparameter search via Optuna

  Middle section — Three charts side by side:
    Chart 1 (cv_vs_final_accuracy.png):
      CV accuracy vs Final 2024 accuracy per model.
      Yellow outline = LR and Bagging_LR — anomalously high, flagged.
      CatBoost 63% on Final 2024 is the most reliable result.
      Paper baseline ~54.5% shown as red dashed line.

    Chart 2 (accuracy_per_fold.png):
      Accuracy per test year (2019–2023) per model — shows consistency over time.
      Tree-based models (HGB, CatBoost) are more stable year to year.
      LR spikes in 2020 (79%) but drops in other years — inconsistent, suspicious.

    Chart 3 (sharpe_by_model.png):
      If you bet money following each model, did the strategy make money?
      Mean Sharpe proxy across CV folds.
      High accuracy does not guarantee positive Sharpe.

  Bottom section — Streamlit Interface:
    Screenshot of the app.
    Feature input form · prediction output (up/down + confidence) · feature importance chart.

Speaker notes (Lee):
  "Looking at the first chart: CatBoost and HGB land around 60-63% on the true 2024 test
  — above the paper baseline of 54%. Logistic Regression shows 74% in CV, which is
  suspicious for financial time series where the literature reports 55-65%. Its AUC is
  0.85, far above the literature upper bound of 0.62 — we flagged it for investigation.
  The second chart shows whether results hold across different market regimes: 2020 was
  COVID, 2022 was the rate hike cycle. Models that stay consistent across years are more
  trustworthy than ones that spike in one year and drop in another.
  The third chart answers the practical question: if you actually traded on these
  predictions, did you make money? High accuracy alone does not guarantee profit.
  This app doesn't train anything live — all 12 models × 6 folds were already trained
  and saved to disk by train.py. The app just lets you pick one and instantly see how
  it performed: accuracy/F1/AUC/Sharpe for that fold, a chart of its day-by-day predicted
  vs actual direction, and — for tree-based models — which features it relied on most."

Presentation talking points (extra material, use as needed):
  - Architecture point: **train once, demo many times** — decouples the expensive
    training step from the interactive demo, which is why the UI is instant.
  - Pick one interesting fold to show live (e.g. LR, fold 2 or 4 — see
    model_comparison.csv, these had the highest AUC) and narrate what "predicted vs
    actual" means: every point where the two lines diverge is a wrong-direction day.
  - Point out the Sharpe proxy vs accuracy trade-off — a model can look accurate but
    still lose money (negative Sharpe); this is why both numbers are shown side by side.
  - If asked "why so many models" — mention the Bagging_DT vs RF distinction (row
    resampling only vs row+feature resampling) as a concrete example of the kind of
    comparison this app was built to make easy.

Bayesian search — how ours differs from the original paper (extra material, trim as needed):
  Guyard & Deriaz (2024) also used Bayesian hyperparameter optimization (confirmed in
  References/eurusd-forex-prediction.html, section "Bayesian Hyperparameter Optimization")
  — so this is not a technique Claude invented on its own; it follows the paper's method.
  However, the original is more elaborate than our version:

    Paper (EUR/USD):
      - THREE sequential Bayesian searches, each stage initialised from the previous
        stage's result:
          Search 1: tune hyperparameters on the full feature set
          Search 2: tune hyperparameters + coarse feature selection (drop weak features)
          Search 3: tune hyperparameters + fine feature selection -> final model
      - Rationale given in the paper: cascading stages converge faster because each
        stage starts from a good point instead of exploring the full space cold each time.
      - Optimization criterion: accuracy (the paper notes this only imperfectly
        correlates with actual trading profit).

    Ours (GBP/USD):
      - ONE single-stage Bayesian search per model (no feature selection stage —
        all 110 columns of dataset_basic_daily.csv are used as-is).
      - Optimization criterion: F1-macro instead of accuracy (chosen because it
        balances both classes; matters less here since classes are already
        near-balanced 49/51, but is the more defensible default).
      - Simplification is intentional: our scope is comparing 22 models broadly
        rather than deeply optimizing one model's feature subset — a 3-stage
        cascading search per model would multiply runtime substantially for
        limited marginal benefit at this project's scope.

    Say explicitly in the talk: "we used the same Bayesian optimization technique as
    the original paper, but simplified to a single stage without automatic feature
    selection, since our goal was breadth across models rather than depth on one model."
    Don't let the audience assume we replicated the paper's tuning pipeline exactly.

  Why Bayesian search instead of Grid Search or Random Search:
    - Grid Search: tries every combination on a fixed grid. Cost explodes
      combinatorially with the number of hyperparameters (e.g. 5 values x 5 values x
      5 values = 125 combinations per model, all evaluated even in obviously bad
      regions of the space). Wasteful, and grid resolution has to be guessed in advance.
    - Random Search: samples combinations uniformly at random. Better than grid at
      covering high-dimensional spaces with a fixed budget, but has no memory — trial 50
      is chosen exactly as blindly as trial 1, even if trials 1-49 already showed which
      regions are hopeless.
    - Bayesian search (Optuna, what we use): builds a probabilistic model of
      "hyperparameters -> score" from every trial run so far, then samples the next
      candidate from regions predicted to score well (with some exploration to avoid
      getting stuck). In practice this means good hyperparameters are found in far
      fewer trials than grid or random search would need for the same result quality —
      relevant here because each trial means fitting the model on 4 folds, and some
      models (Bagging_LR, MLP) already take minutes per single fit.
    - This is also why the paper's own justification for cascading 3 searches
      ("accelerates convergence... starting points matter enormously") is the same
      underlying argument: Bayesian methods are only worth using because they exploit
      information from prior trials, and a good starting point compounds that benefit.

---

### SLIDE 9 — Conclusion & Takeaways (Lee, ~30 sec)

Content:
  Three bullets:
    1. Reproduced a research paper methodology, adapted to a new currency pair
    2. Built a full ML pipeline: multi-source data → feature engineering → walk-forward CV → Bayesian tuning
    3. Packaged into a live Streamlit app

Speaker notes (Lee):
  "To summarize: we replicated and adapted published research, built a complete end-to-end
  ML pipeline for a real financial prediction problem, and delivered it as an interactive
  application. Questions welcome."

---

### SLIDE 10 — References & AI Disclosure (display only)

Content:
  Primary reference:
    Guyard, T. & Deriaz, M. (2024). Predicting EUR/USD Direction Using Machine Learning.
    University of Geneva. [Reference 10 in project folder]

  Data sources:
    FRED API — Federal Reserve Bank of St. Louis (fred.stlouisfed.org)
    ONS UK API v1 beta — Office for National Statistics (api.ons.gov.uk)
    yfinance — Yahoo Finance market data (pypi.org/project/yfinance)

  Additional papers consulted (References folder, 11 papers):
    FX direction prediction, LSTM volatility forecasting, deep networks for FX,
    wavelets and neural networks for FX, ML for FX forecasting review

  AI Disclosure — Claude Code (Anthropic) assisted with:
    - Data pipeline architecture and all fetch / process scripts
    - Panel harmonization logic (no-look-ahead bias via realtime_start)
    - Model registry pattern, training pipeline, and Bayesian search integration
    - Evaluation framework (walk-forward CV, metrics, backtest scaffolding)
    - EDA notebook structure and analysis
    - Debugging (e.g., InfinityToNaNTransformer for UK CPI YoY log during deflation)
    All code was reviewed, tested, and validated by the project team.

---

## Time Budget

  Slide 1     (Lee intro + overview)              :  1 min 15 sec
  Slides 2-3  (Manim, Goal 1)                     :  2 min 20 sec
  Slides 4-6  (Somitha, Goal 2 + feature eng.)    :  2 min 35 sec
  Slide 7     (Lee, walk-forward CV)              :  1 min 00 sec
  Slide 8     (Lee, models + Streamlit)           :  1 min 30 sec
  Slide 9     (Lee, conclusion)                   :  0 min 30 sec
  Slide 10    (References, displayed)             :  0 min 15 sec
  Buffer / transitions                            :  0 min 35 sec
  TOTAL                                           : 10 min 00 sec

---

## Key Numbers to Know

  - Data window: 2014-01-01 to 2024-12-31 (11 years, ~3,254 trading days)
  - Final dataset: 2,868 rows × 110 columns
  - Dropped: CPI levels (non-stationary) + 5 of 9 equity indices (multicollinearity r > 0.87)
  - Kept equity: SP500, NASDAQ100, RUSSELL2000, FTSE100
  - Models trained: 22 total (12 fast, 3 medium, 7 slow)
  - CV folds: 6 (5 development folds + 1 held-out final test on 2024)
  - Class balance: 49.1% UP / 50.9% DOWN (ratio 1.04x — balanced)
  - Best Final 2024 result: CatBoost 63.2% accuracy
  - Paper baseline: ~53-56% accuracy on EUR/USD (Guyard & Deriaz 2024)

---

## Charts Available (reports/figures/)

  cv_vs_final_accuracy.png   — CV vs Final 2024 accuracy per model  (slide 8)
  accuracy_per_fold.png      — Accuracy per year 2019-2023 per model (slide 8)
  sharpe_by_model.png        — Sharpe proxy per model                (slide 8)
  auc_by_model.png           — AUC-ROC per model                     (reference / backup)

  Regenerate all: python scripts/plot_model_comparison.py --open
