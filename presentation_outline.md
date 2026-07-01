# Presentation Outline — GBP/USD Direction Prediction
# Duration: 10 minutes | Date: July 8, 2026

---

## Speaker Assignment

- Manim   : Goal 1 — Data Collection (slides 3-5)
- Somitha : Goal 2 — Exploratory Data Analysis & Target Definition (slides 6-8)
- Lee     : Introduction + Goal 3 — Model Pipeline + Goal 4 — Streamlit UI + Conclusion (slides 1-2, 9-12)

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

### SLIDE 3 — Data Sources Overview (Manim, ~40 sec)

Content:
  Three data categories:
    1. Macro indicators — GDP, CPI, central bank rates, current account (USA + UK)
       Sources: FRED API, ONS UK API
    2. Forex OHLCV — 13 currency pairs (GBP/USD is both feature and target)
       Source: yfinance / Dukascopy
    3. Equity indices — 9 indices (5 US, 4 UK)
       Source: yfinance

Speaker notes (Manim):
  "We collected data from three categories. For macro indicators, we used the FRED API
  for US data and the ONS API for UK-specific series. For market data we used yfinance
  to get daily OHLCV for 13 forex pairs and 9 equity indices."

---

### SLIDE 4 — Data Collection Pipeline (Manim, ~50 sec)

Content:
  Show pipeline: fetch scripts → data/raw/ → process scripts → data/interim/
  Highlight: fetch_*.py (needs network) vs process_*.py (runs offline)
  Show the 4 interim panels: gdp_panel, cpi_panel, central_bank_rate_panel, current_account_panel
  Mention: 2014-01-01 to 2024-12-31, ~3,254 trading days

Speaker notes (Manim):
  "Data collection is split into two stages. Fetch scripts pull data from APIs and save
  raw CSVs. Process scripts then clean and standardize each indicator into a daily-indexed
  panel with forward-filling and no look-ahead bias — meaning each day only sees data that
  was publicly available at that date, using the realtime_start column from FRED."

---

### SLIDE 5 — Data Challenges & Solutions (Manim, ~50 sec)

Content:
  Three challenges (present as brief problem + solution pairs):
    1. UK GDP: FRED series discontinued in 2020 → replaced with ONS direct API
    2. Composite PMI: not on FRED for either country → investing.com scraper (recent only)
       → limitation: no historical backfill possible
    3. Dukascopy forex: 800k+ hourly files for full history → used yfinance instead

Speaker notes (Manim):
  "We ran into several data gaps. The UK GDP series on FRED was discontinued, so we
  switched to the ONS API directly. Composite PMI was unavailable on FRED entirely — we
  wrote a scraper but discovered the source only keeps the last 3-4 releases, so full
  history is not available for free. These limitations shaped our feature set."

---

### SLIDE 6 — Target Variable Definition (Somitha, ~40 sec)

Content:
  Formula:
    Direction(t) = 1  if close(t+1) > close(t)
    Direction(t) = 0  if close(t+1) <= close(t)
  Show class balance chart (roughly 50/50 split expected)
  Emphasize: this is a BINARY classification, not regression

Speaker notes (Somitha):
  "We defined the target variable as the next-day direction of GBP/USD. A value of 1
  means the closing price tomorrow is higher than today, and 0 otherwise. This turns
  the problem into binary classification. The class balance is important to check —
  an imbalanced target would require adjusted metrics."

---

### SLIDE 7 — EDA: Macro Indicators (Somitha, ~50 sec)

Content:
  2-3 key charts from notebook 01_eda_macro.ipynb:
    - GDP growth trend comparison UK vs US (2014-2024, highlight COVID dip)
    - CPI / inflation comparison, highlight 2022 UK spike
    - Central bank rate divergence 2022-2023
  Key finding: macro indicators show regime changes (Brexit 2016, COVID 2020, rate hike cycle 2022)

Speaker notes (Somitha):
  "Looking at the macro indicators, we can identify major market events: Brexit uncertainty
  in 2016, the COVID crash in 2020, and the aggressive rate hike cycle from 2022 to 2023
  where the Bank of England and the Fed moved at different speeds. These regime changes are
  exactly the kind of structure we want the model to learn from."

---

### SLIDE 8 — EDA: Forex & Feature Correlation (Somitha, ~50 sec)

Content:
  - GBP/USD OHLCV chart 2014-2024 with key events annotated
  - Correlation heatmap: which features correlate most with the target
  - Missing value summary across all features

Speaker notes (Somitha):
  "The GBP/USD series itself shows the impact of those macro events clearly. Our
  correlation analysis shows which indicators have the strongest linear relationship
  with next-day direction — though as we will see, the model captures non-linear
  patterns too. We also identified and documented which features had missing data
  and how they were handled in the pipeline."

---

### SLIDE 9 — Model Design & Walk-Forward CV (Lee, ~60 sec)

Content:
  Diagram of expanding-window walk-forward cross-validation:
    Fold 1: Train 2014-2018 / Test 2019
    Fold 2: Train 2014-2019 / Test 2020
    ...
    Final:  Train 2014-2023 / Test 2024 (held out)
  Explain WHY this matters for time series: no data leakage

Speaker notes (Lee):
  "Because GBP/USD is a time series, we cannot use random train/test splits — that would
  let the model see future data during training. Instead we use expanding-window walk-forward
  cross-validation: the training window grows by one year at a time, and we always test on
  the year immediately after. The 2024 data is a true held-out set, never touched until
  the final evaluation."

---

### SLIDE 10 — Models & Results (Lee, ~60 sec)

Content:
  Model comparison table (top 5 models, dataset_basic_daily):
    Show: model name, accuracy (mean across folds), F1-macro, AUC-ROC
  Highlight best performer
  Note: 12 fast models trained, 3 medium, 7 slow (Bayesian search for tuning)
  Reference paper baseline: ~53-56% accuracy for EUR/USD

Speaker notes (Lee):
  "We trained 22 model variants. On the basic daily dataset with default parameters,
  Logistic Regression and Bagging-LR showed unusually high accuracy — 65 to 79% —
  which we flagged for investigation, possibly due to feature scaling effects.
  Tree-based models like HGB and CatBoost showed 55 to 65%, consistent with the
  paper's baseline of 53 to 56% on EUR/USD. Hyperparameter tuning with Optuna is
  underway to close the gap."

---

### SLIDE 11 — Streamlit Interface (Lee, ~30 sec)

Content:
  Screenshot of the Streamlit app
  Show: feature input form, prediction output (up/down + confidence), feature importance chart

Speaker notes (Lee):
  "We built a Streamlit interface where you can input macro indicators and market data
  for a given day and get a predicted direction for the next day, along with a
  confidence score and the top features driving the prediction."

---

### SLIDE 12 — Conclusion & Takeaways (Lee, ~30 sec)

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

## Time Budget

  Slide 1-2   (Lee intro)      :  1 min 15 sec
  Slides 3-5  (Manim, Goal 1)  :  2 min 20 sec
  Slides 6-8  (Somitha, Goal 2):  2 min 20 sec
  Slides 9-11 (Lee, Goals 3-4) :  2 min 30 sec
  Slide 12    (Lee conclusion)  :  0 min 30 sec
  Buffer / Q&A transition       :  1 min 05 sec
  TOTAL                         : 10 min 00 sec

---

## Key Numbers to Know

  - Data window: 2014-01-01 to 2024-12-31 (11 years, ~3,254 trading days)
  - Features: macro (GDP, CPI, rates, current account x2 countries) + 13 FX pairs + 9 equity indices
  - Models trained: 22 total (12 fast, 3 medium, 7 slow)
  - CV folds: 6 (5 development folds + 1 held-out final test on 2024)
  - Paper baseline: ~53-56% accuracy on EUR/USD (Guyard & Deriaz 2024)
