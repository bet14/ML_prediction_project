# Presentation Outline — GBP/USD Direction Prediction
# Duration: 10 minutes | Date: July 8, 2026

---

## Speaker Assignment

- Manim   : Goal 1 — Data Collection & Harmonization (slides 3-4)
- Somitha : Goal 2 — Target Definition & EDA (slides 5-6)
- Lee     : Introduction + Goal 3 — Model + Goal 4 — Streamlit + Conclusion (slides 1-2, 7-10)
- Slide 11 (References & AI Disclosure) — displayed on screen, no speaker notes needed

---

## Slide-by-Slide Script

### SLIDE 1 — Title & Problem Statement (Lee, ~45 sec)

Content:
  Title: "Predicting GBP/USD Daily Direction Using Machine Learning"
  Subtitle: Adapted from Guyard & Deriaz (2024), EUR/USD → GBP/USD
  Names + course name

Speaker notes (Lee):
  "Our project predicts whether the GBP/USD exchange rate will go up or down the next
  trading day — a binary classification problem. We adapted methodology from a 2024 paper
  on EUR/USD and applied it to GBP/USD using 11 years of data, from 2014 to 2024."

---

### SLIDE 2 — Project Architecture Overview (Lee, ~30 sec)

Content:
  4-block flow diagram: Data Collection → EDA → Model Pipeline → Streamlit UI
  Each block labeled with the course goal number (Goal 1 / 2 / 3 / 4)

Speaker notes (Lee):
  "The project follows four course goals. Manim will cover how we collected the data,
  Somitha will explain our analysis and how we defined the prediction target,
  and I will walk through the model and the interface."

---

### SLIDE 3 — Data Sources & Collection Pipeline (Manim, ~75 sec)

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
      → data/interim/  (4 panels, daily business-day index, 2014–2024)
      → build_dataset.py
      → data/processed/dataset_basic_daily.csv  (2,868 rows × 110 cols)

  Bottom note: 2014-01-01 to 2024-12-31 · ~3,254 trading days

Speaker notes (Manim):
  "We collected data from three categories: macro indicators from FRED and the ONS API,
  and market data from yfinance — 13 forex pairs and 9 equity indices.
  The pipeline is split into two stages. Fetch scripts pull data from APIs and save raw
  CSVs. Process scripts then clean each indicator into a daily panel. These process scripts
  can run offline — useful when we work without network access. The final merged dataset
  has 2,868 rows and 110 columns."

---

### SLIDE 4 — Data Limitations & Panel Harmonization (Manim, ~70 sec)

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

    Transforms applied:
      Central bank rates → sqrt  (stabilises variance)
      UK CPI YoY → log           (normalises right skew)
      CPI level columns dropped  (ADF test: non-stationary I(1))

Speaker notes (Manim):
  "Two data sources had to be excluded. Composite PMI has no free 10-year history —
  investing.com only keeps the last few releases. FX trading volume is either broker-only
  or simply absent in yfinance — not reliable enough to use.
  For the remaining data, the key challenge is time alignment. GDP releases quarterly
  and gets revised months later. We use each value's actual publication date so the model
  never sees a revision before it was officially released. The days_since_update column
  tells the model how stale any given reading is on each trading day."

---

### SLIDE 5 — Target Variable Definition (Somitha, ~40 sec)

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

### SLIDE 6 — EDA: Macro, Forex, and Equity (Somitha, ~60 sec)

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
    - UK FTSE100 positively correlated with GBP/USD; US indices weakly negative

Speaker notes (Somitha):
  "Three key findings. First, the rate differential between the Fed and BoE is one of
  the clearest macro drivers of GBP/USD — we added it as an explicit engineered feature.
  Second, GBP/USD daily returns show extreme fat tails — kurtosis of 14 — which is why
  we use RobustScaler rather than StandardScaler in the model pipeline. Third, we started
  with 9 equity indices and dropped 5 due to high multicollinearity, keeping only 4."

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
  "Because GBP/USD is a time series, we cannot use a random train/test split — that would
  let the model see future data during training. Instead we use expanding-window walk-forward
  cross-validation: the training window grows by one year at a time, and we always test on
  the year immediately after. The 2024 data is a true held-out set, never touched until
  the final evaluation."

---

### SLIDE 8 — Models & Results (Lee, ~60 sec)

Content:
  Model pipeline architecture:
    InfinityToNaNTransformer → SimpleImputer(median) → [RobustScaler] → model
  Model comparison table (top 5 models, dataset_basic_daily, mean across folds):
    Show: model name, accuracy, F1-macro, AUC-ROC
  Note: 22 models total (12 fast, 3 medium, 7 slow); Bayesian search via Optuna
  Reference paper baseline: ~53-56% accuracy on EUR/USD (Guyard & Deriaz 2024)

Speaker notes (Lee):
  "We trained 22 model variants. On the basic daily dataset with default parameters,
  tree-based models like HGB and CatBoost showed 55 to 65%, consistent with the
  paper's baseline of 53 to 56% on EUR/USD. Logistic Regression showed unusually high
  numbers — 65 to 79% — flagged for further investigation. Hyperparameter tuning with
  Optuna is running across all folds to close the gap."

---

### SLIDE 9 — Streamlit Interface (Lee, ~30 sec)

Content:
  Screenshot of the Streamlit app
  Show: feature input form, prediction output (up/down + confidence), feature importance chart

Speaker notes (Lee):
  "We built a Streamlit interface where you can input macro indicators and market data
  for a given day and get a predicted direction for the next day, along with a
  confidence score and the top features driving the prediction."

---

### SLIDE 10 — Conclusion & Takeaways (Lee, ~30 sec)

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

### SLIDE 11 — References & AI Disclosure (display only)

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

  Slide 1-2  (Lee intro)            :  1 min 15 sec
  Slides 3-4 (Manim, Goal 1)        :  2 min 25 sec
  Slides 5-6 (Somitha, Goal 2)      :  1 min 40 sec
  Slides 7-9 (Lee, Goals 3-4)       :  2 min 30 sec
  Slide 10   (Lee conclusion)        :  0 min 30 sec
  Slide 11   (References, displayed) :  0 min 15 sec
  Buffer / transitions               :  1 min 05 sec
  TOTAL                              : 10 min 00 sec

---

## Key Numbers to Know

  - Data window: 2014-01-01 to 2024-12-31 (11 years, ~3,254 trading days)
  - Final dataset: 2,868 rows × 110 columns
  - Features: macro (GDP, CPI, rates, current account × 2 countries) + 13 FX pairs + 4 equity indices (kept after multicollinearity)
  - Models trained: 22 total (12 fast, 3 medium, 7 slow)
  - CV folds: 6 (5 development folds + 1 held-out final test on 2024)
  - Class balance: 49.1% UP / 50.9% DOWN (ratio 1.04x — balanced)
  - Paper baseline: ~53-56% accuracy on EUR/USD (Guyard & Deriaz 2024)
