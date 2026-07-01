# Task Division — GBP/USD Presentation, July 8 2026

---

## Deadlines

  July 3  : All content finalized. Slides fully drafted. No content gaps.
  July 5-6: Group rehearsal. Time each section. Fix wording and slide design.
  July 8  : Presentation day.

---

## Manim — Goal 1: Data Collection

Slides to own: 3, 4, 5

Content to prepare:
  - Explain the three data categories (macro / forex / equity) and their sources
  - Show the pipeline: fetch scripts -> raw CSVs -> process scripts -> interim panels
  - Explain forward-filling and no-look-ahead-bias (realtime_start column)
  - Present the three data challenges and how each was handled
      UK GDP: FRED series discontinued -> ONS API replacement
      Composite PMI: no free historical source -> scraper limitation documented
      Forex: Dukascopy too heavy -> yfinance used instead

Files to read for preparation:
  - PROJECT_GUIDE.md (sections: Folder Structure, Running the Main Pipelines)
  - README.md (sections: data/raw/macro, data/raw/forex, data/raw/equity)
  - reports/macro_data_status.html (open in browser — live data inventory)
  - reports/forex_data_status.html
  - reports/equity_data_status.html

Visuals to include in slides:
  - Simple flow diagram: API -> fetch_*.py -> data/raw/ -> process_*.py -> data/interim/
  - Table of macro indicators: name, source, frequency, status (OK / stale / missing)
  - One chart showing the data gap problem (e.g., UK GDP stopping at 2020)

Talking time: approximately 2 minutes 20 seconds

---

## Somitha — Goal 2: EDA and Target Definition

Slides to own: 6, 7, 8

Content to prepare:
  - Clearly define the binary target variable (formula + chart of class balance)
  - Present key EDA findings from macro indicators: GDP, CPI, central bank rate divergence
  - Present GBP/USD price history with key events annotated (Brexit, COVID, rate hikes)
  - Show correlation heatmap or top-N most correlated features with the target
  - Summarize missing value handling

Files to read for preparation:
  - notebooks/01_eda_macro.ipynb (macro EDA)
  - notebooks/02_eda_forex_equity.ipynb (forex/equity EDA, target definition)
  - notebooks/03_feature_analysis.ipynb (feature importance, correlation)
  - PROJECT_GUIDE.md (section: Specific ML Objective, for the target formula)
  - reports/eda_summary.html (open in browser — aggregated EDA report)

Visuals to include in slides:
  - Bar chart or pie chart: class balance (% of days Direction=1 vs Direction=0)
  - Line chart: GBP/USD close price 2014-2024 with Brexit/COVID/2022 rate hike annotated
  - Correlation heatmap or bar chart of top 10 features
  - Optional: stationarity test results table (ADF test on key series)

Talking time: approximately 2 minutes 20 seconds

---

## Lee — Introduction + Goal 3: Model + Goal 4: Streamlit + Conclusion

Slides to own: 1, 2, 9, 10, 11, 12

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
