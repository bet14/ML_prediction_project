# Task Division — GBP/USD Presentation, July 8 2026

---

## Deadlines

  July 3  : All content finalized. Slides fully drafted. No content gaps.
  July 5-6: Group rehearsal. Time each section. Fix wording and slide design.
  July 8  : Presentation day.

---

## Manim — Goal 1: Data Collection and Harmonization

Slides to own: 2, 3
Talking time : approximately 2 min 20 sec

Content to prepare:

  Slide 2 — Data Sources & Collection Pipeline:
    The three data categories (macro / forex / equity) and their API sources.
    Pipeline flow: fetch_*.py -> data/raw/ -> process_*.py -> data/interim/ -> build_dataset.py
    Emphasize: fetch_*.py requires network; process_*.py runs offline.
    Final dataset: 2,868 rows x 110 columns.

  Slide 3 — Data Limitations & Panel Harmonization:
    Two features investigated and excluded:
      Composite PMI: not on FRED; investing.com only keeps 3-4 recent releases (no 10-year history);
      no free alternative source found -> excluded.
      FX trading volume: Dukascopy gives broker-only volume (not global); 10 years of tick data
      would take ~5 days to download and aggregate; yfinance has no FX volume -> excluded.
    Panel harmonization — no look-ahead bias:
      The realtime_start column: each macro value carries the actual publication date.
      build_known_as_of(): for each trading day, look backward and attach the latest value
      whose realtime_start is on or before that day -> never sees data before it was published.
      days_since_update column: how stale each reading is -> used as an explicit model feature.
    Transforms applied in process_*.py:
      sqrt on central bank rates, log on UK CPI YoY, CPI level columns dropped (ADF: I(1)).

Files to read for preparation:
  - PROJECT_GUIDE.md (Folder Structure, Running the Main Pipelines)
  - src/features/panel_common.py (build_known_as_of function — read the docstring)
  - src/features/process_cpi.py, process_central_bank_rate.py (transforms applied)
  - reports/macro_data_status.html (open in browser)

Visuals to include in slides:
  Slide 2: Flow diagram (API -> fetch -> data/raw/ -> process -> data/interim/ -> build_dataset.py)
           Table of macro indicators: name, source, frequency, status
  Slide 3: Diagram of build_known_as_of logic (realtime_start vs period date, forward fill)

---

## Somitha — Goal 2: Target Definition, EDA, and Feature Engineering

Slides to own: 4, 5, 6
Talking time : approximately 2 min 35 sec

Content to prepare:

  Slide 4 — Target Variable Definition:
    Formula: Direction(t) = 1 if close(t+1) > close(t), else 0.
    Class balance: UP 1,408 days (49.1%) / DOWN 1,461 days (50.9%), ratio 1.04x.
    Conclusion: dataset is balanced — no SMOTE or class_weight correction needed.
    Rolling 1-year UP% chart: oscillates around 50% throughout the decade.

  Slide 5 — EDA: Macro, Forex, and Equity:
    Macro (notebook 01):
      CPI YoY comparison USA vs UK (highlight 2022 spike to ~10%).
      Rate differential (Fed minus BoE): negative 2014-2016, compressed 2017-2021,
      turns positive 2022-2023 as Fed hiked faster -> motivation for rate_differential feature.
      ADF stationarity: GDP and CPI level are I(1) -> only YoY forms used.
    GBP/USD and forex (notebook 02):
      Daily return stats: mean -0.008%/day, std 0.57%, skew -0.91, kurtosis 14.4 (fat tails).
      Worst single day: -7.6% on 2016-06-24 (Brexit referendum).
      Fat tails -> RobustScaler used in pipeline, not StandardScaler.
      EUR_GBP kurtosis 109, GBP_CHF kurtosis 173 -> clip at +-5 sigma before training.
    Equity (notebook 02):
      9 indices collected; 5 dropped via multicollinearity analysis:
        DJI (r=0.95 with SP500), NASDAQ_COMPOSITE (r=0.99 with NASDAQ100),
        FTSE250/FTSE350/FTSE_ALL_SHARE (r > 0.87 with FTSE100).
      4 kept: SP500, NASDAQ100, RUSSELL2000, FTSE100.
      UK FTSE100 positively correlated with GBP/USD returns; US indices weakly negative.

  Slide 6 — Feature Engineering & Building the Model Dataset:
    (Directly motivated by EDA findings from slide 5.)

    What was DROPPED (justified by slide 5 analysis):
      CPI level columns (USA_cpi_value, UK_cpi_value):
        ADF: non-stationary I(1), monotonically trended 100->130 over 11 years -> misleads linear models.
        Replaced by CPI Year-on-Year % (stationary).
      5 of 9 equity indices (multicollinearity confirmed in notebook 03):
        DJI (r=0.954 with SP500), NASDAQ_COMPOSITE (r=0.992 with NASDAQ100),
        FTSE_ALL_SHARE (r=0.993 with FTSE100), FTSE350 (r=0.974), FTSE250 (r=0.872).
        Kept: SP500, NASDAQ100, RUSSELL2000, FTSE100.

    What was ADDED / ENCODED:
      Equity log returns: {INDEX}_ret = log(close_t / close_{t-1}) -> stationary, suitable for ML.
      Engineered macro feature: rate_differential = USA_central_bank_rate - UK_central_bank_rate
        (EDA showed this is a key GBP/USD driver -> made explicit as a feature).
      Date encoding:
        Tree models (RF, XGB, CatBoost): day (int), month (int), weekday (int).
        Linear models & MLP: day_sin, day_cos, month_sin, month_cos, weekday_sin, weekday_cos.
        Cyclical encoding ensures December and January are treated as adjacent.
    Final result: dataset_basic_daily.csv -- 2,868 rows x 110 columns.

Files to read for preparation:
  - notebooks/01_eda_macro.ipynb (sections 3, 4, 5, 7)
  - notebooks/02_eda_forex_equity.ipynb (sections 2, 3, 6, 7, 9, 11)
  - notebooks/03_feature_analysis.ipynb (multicollinearity section)
  - src/features/build_dataset.py (REDUNDANT_INDICES list, encoding logic, comments)
  - References/GOAL3_PLAN.md (step-by-step pipeline and reasoning)
  - PROJECT_GUIDE.md (Specific ML Objective for the target formula)

Visuals to include in slides:
  Slide 4: Bar chart of class balance (UP/DOWN) + rolling 1-year UP% line chart
  Slide 5: Rate differential fill chart (notebook 01),
           GBP/USD daily returns bar chart with Brexit annotated,
           Equity normalised price chart (US divergence vs UK FTSE100 flatness)
  Slide 6: Two-column layout:
           Left column:  DROPPED (CPI levels + 5 equity indices, with r values)
           Right column: ADDED (log returns, rate_differential, date encoding int vs sin/cos)
           Footer: "Result: dataset_basic_daily.csv -- 2,868 rows x 110 columns"

---

## Lee — Introduction + Goal 3: Model + Goal 4: Streamlit + Conclusion

Slides to own: 1, 7, 8, 9 (slide 10 References is displayed on screen — no speaker notes)
Talking time : approximately 3 min 15 sec

Content to prepare:

  Slide 1 — Title, Problem Statement & Project Overview:
    Title, names, one-sentence problem statement.
    4-block architecture flow diagram (Goal 1 -> Goal 2 -> Goal 3 -> Goal 4).
    Brief intro of who presents what.

  Slide 7 — Model Design & Walk-Forward CV:
    Walk-forward CV diagram with fold dates:
      Fold 1: Train 2014-2018 / Test 2019
      Fold 2: Train 2014-2019 / Test 2020
      Fold 3: Train 2014-2020 / Test 2021
      Fold 4: Train 2014-2021 / Test 2022
      Fold 5: Train 2014-2022 / Test 2023
      Final : Train 2014-2023 / Test 2024 (held-out, never touched until final evaluation)
    Why not random split? -> time series -> data leakage.

  Slide 8 — Models, Results & Streamlit Interface:
    Pipeline: InfinityToNaNTransformer -> SimpleImputer(median) -> [RobustScaler] -> model
    22 models trained. Bayesian hyperparameter search via Optuna.
    Three charts (see reports/figures/):
      cv_vs_final_accuracy.png -- CV mean vs Final 2024 per model, yellow = flagged LR anomaly
      accuracy_per_fold.png   -- accuracy per test year 2019-2023, shows consistency
      sharpe_by_model.png     -- financial usefulness (did the strategy make money?)
    Streamlit screenshot: input form, prediction (up/down + confidence), feature importance chart.

  Slide 9 — Conclusion & Takeaways:
    Three bullets:
      1. Adapted published research methodology to a new currency pair (GBP/USD)
      2. Built full ML pipeline: multi-source data -> feature engineering -> walk-forward CV -> Bayesian tuning
      3. Packaged into a live Streamlit app

Files to read for preparation:
  - PROJECT_GUIDE.md (Cross-Validation & Train/Test Strategy, Glossary sections)
  - src/models/model_registry.py (list of all 22 models and their tags)
  - src/models/train.py (pipeline architecture)
  - src/evaluation/walk_forward_cv.py (fold logic)
  - reports/tables/model_comparison.csv (key numbers: CatBoost 63.2%, LR flagged)
  - reports/figures/ (the 4 charts -- use cv_vs_final, accuracy_per_fold, sharpe for slide 8)
  - References/GOAL3_PLAN.md (full goal 3 plan)
  - src/app/app.py (Streamlit interface)

---

## Coordination Notes

  All slides go into one shared deck (Google Slides or PowerPoint).
  Slide numbering matches presentation_outline.md (slides 1-10).
  By July 3: each person uploads their draft slides to the shared deck.
  July 5-6 rehearsal: run the full 10 minutes in order. Time each section.
  If a section runs over, cut detail — do not cut the conclusion.

  Branch: branch_lee (do not push experimental files before July 8).
  All slide content must be in English.

---

## Time Summary

  Slide 1     Lee     intro + architecture                :  1 min 15 sec
  Slides 2-3  Manim   data collection + harmonization     :  2 min 20 sec
  Slides 4-6  Somitha target + EDA + feature engineering  :  2 min 35 sec
  Slide 7     Lee     walk-forward CV                     :  1 min 00 sec
  Slide 8     Lee     models + Streamlit                  :  1 min 30 sec
  Slide 9     Lee     conclusion                          :  0 min 30 sec
  Slide 10    (display only — no speaker)                 :  0 min 15 sec
  Buffer / transitions                                    :  0 min 35 sec
  TOTAL                                                   : 10 min 00 sec
