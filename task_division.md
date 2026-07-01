# Task Division — GBP/USD Presentation, July 8 2026

---

## Deadlines

  July 3  : All content finalized. Slides fully drafted. No content gaps.
  July 5-6: Group rehearsal. Time each section. Fix wording and slide design.
  July 8  : Presentation day.

---

## Manim — Goal 1: Data Collection and Harmonization

Slides to own: 3, 4

Content to prepare:

  Slide 3 — Data sources:
    The three data categories (macro / forex / equity) and their API sources.

  Slide 4 — Pipeline:
    fetch scripts -> data/raw/ -> process scripts -> data/interim/
    Emphasize: fetch_*.py requires network; process_*.py runs offline.

  Slide 5 — Two features excluded with clear reasons:
    Composite PMI: not on FRED; investing.com only keeps 3-4 recent releases (no 10-year history);
    no free alternative source found -> excluded.
    FX trading volume: Dukascopy gives broker-only volume (not global); 10 years of tick data
    would take ~5 days to download and aggregate; yfinance has no FX volume -> excluded.

  Slide 6 — Panel harmonization:
    The realtime_start column: each macro value carries the date it was actually published.
    build_known_as_of(): for each trading day, look backward and attach the latest value
    whose realtime_start is on or before that day -> no look-ahead bias.
    days_since_update column: how stale each reading is -> used as a model feature.
    Transforms: sqrt on central bank rates, log on UK CPI YoY, CPI level columns dropped (I(1)).
    Result: 4 daily-indexed interim panel CSVs.

Files to read for preparation:
  - PROJECT_GUIDE.md (Folder Structure, Running the Main Pipelines)
  - README.md (sections: data/raw/macro, data/raw/forex, data/raw/equity)
  - src/features/panel_common.py (build_known_as_of function — read the docstring)
  - src/features/process_cpi.py, process_central_bank_rate.py (transforms applied)
  - reports/macro_data_status.html (open in browser)

Visuals to include in slides:
  - Flow diagram: API -> fetch_*.py -> data/raw/ -> process_*.py -> data/interim/
  - Table of macro indicators: name, source, frequency, status
  - Diagram of build_known_as_of logic (realtime_start vs period date, showing forward fill)

Talking time: approximately 2 minutes 40 seconds

---

## Somitha — Goal 2: Target Definition and EDA

Slides to own: 5, 6

Content to prepare:

  Slide 7 — Target variable:
    Formula: Direction(t) = 1 if close(t+1) > close(t), else 0.
    Key numbers from notebook 02: UP 1,408 days (49.1%) / DOWN 1,461 days (50.9%), ratio 1.04x.
    Conclusion: dataset is balanced — no SMOTE or class_weight correction needed.
    Rolling 1-year UP% chart: oscillates around 50% throughout the decade.

  Slide 8 — EDA findings (three groups):
    Macro (notebook 01):
      CPI YoY comparison USA vs UK (highlight 2022 spike to ~10%).
      Rate differential Fed minus BoE chart: negative 2014-2016, compressed 2017-2021,
      turns positive 2022-2023 as Fed hiked faster -> added as engineered feature rate_differential.
      ADF stationarity: GDP and CPI level are I(1); only YoY / first-difference used.

    GBP/USD and forex (notebook 02):
      Daily return stats: mean -0.008%/day, std 0.57%, skew -0.91, kurtosis 14.4.
      Worst single day: -7.6% on 2016-06-24 (Brexit referendum).
      Fat tails -> RobustScaler used in pipeline, not StandardScaler.
      EUR_GBP kurtosis 109 and GBP_CHF kurtosis 173 -> clip at 5-sigma before training.

    Equity (notebook 02):
      9 indices started, 5 dropped via multicollinearity analysis:
        DJI (r=0.95 with SP500), NASDAQ_COMPOSITE (r=0.99 with NASDAQ100),
        FTSE250/FTSE350/FTSE_ALL_SHARE (r > 0.87 with FTSE100).
      4 kept: SP500, NASDAQ100, RUSSELL2000, FTSE100.
      UK FTSE100 positively correlated with GBP/USD returns; US indices weakly negative.

Files to read for preparation:
  - notebooks/01_eda_macro.ipynb (sections 3, 4, 5, 7)
  - notebooks/02_eda_forex_equity.ipynb (sections 2, 3, 6, 7, 9, 11)
  - src/features/build_dataset.py (REDUNDANT_INDICES list and comments — exact correlation values)
  - PROJECT_GUIDE.md (Specific ML Objective for the target formula)
  - reports/eda_summary.html (open in browser)

Visuals to include in slides:
  - Slide 7: bar chart of class balance + rolling 1-year UP% line chart
  - Slide 8: rate differential fill chart (from notebook 01 cell for cbr),
             GBP/USD daily returns bar chart with Brexit annotated,
             equity normalised price chart (US vs UK divergence 2014-2024)

Talking time: approximately 1 minute 40 seconds

---

## Lee — Introduction + Goal 3: Model + Goal 4: Streamlit + Conclusion

Slides to own: 1, 2, 7, 8, 9, 10 (slide 11 references is displayed, no speaker notes)

Content to prepare:
  Intro (slides 1-2):
    - Title, names, one-sentence problem statement
    - 4-block architecture flow diagram (Goal 1 -> Goal 2 -> Goal 3 -> Goal 4)

  Goal 3 — Model (slides 9-10):
    - Walk-forward CV diagram with fold dates
    - Why expanding window, not random split (data leakage argument)
    - Model comparison table: top 5 models, accuracy / F1 / AUC across folds
    - Note on the LR anomaly (unusually high accuracy, under investigation)
    - Hyperparameter tuning with Optuna (Bayesian search)

  Goal 4 — Streamlit (slide 11):
    - Screenshot of the app
    - Brief walkthrough: input -> prediction -> confidence + feature importance

  Conclusion (slide 12):
    - Three-bullet summary of what was built and learned

Files to read for preparation:
  - PROJECT_GUIDE.md (sections: Cross-Validation & Train/Test Strategy, 3 Final Datasets)
  - src/models/model_registry.py (list of all 22 models and their tags)
  - src/models/train.py (pipeline architecture)
  - src/evaluation/walk_forward_cv.py (fold logic)
  - reports/tables/model_comparison.csv (results to put in the table)
  - References/GOAL3_PLAN.md (full goal 3 plan)
  - src/app/app.py (Streamlit interface)

Talking time: approximately 4 minutes 25 seconds

---

## Coordination Notes

  All slides go into one shared deck (Google Slides or PowerPoint).
  Naming convention for slides: use the slide numbers from presentation_outline.md.
  By July 3: each person uploads their draft slides to the shared deck.
  July 5-6 rehearsal: run the full 10 minutes in order. Timer each section.
  If a section runs over, cut detail — do not cut the conclusion.

  Branch: branch_lee (do not push experimental files before July 8).
  All slide content should be in English.
