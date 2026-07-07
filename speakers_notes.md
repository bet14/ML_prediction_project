# Speaker Notes — GBP/USD Direction Prediction
Source of truth: presentation_outline.md (keep this file in sync with it)

---

## SLIDE 1 — Title, Problem Statement & Project Overview — Manim

- Our project predicts whether GBP/USD goes up or not the next trading day — a
  binary classification problem.
- We adapted methodology from a 2024 EUR/USD paper and applied it to GBP/USD
  using 11 years of data, from 2014 to 2024.
- The project follows four course goals: I cover data collection, Somitha covers
  analysis, target definition, and feature engineering, and Linh covers model
  design, training, results, and the Streamlit interface.

---

## SLIDE 2 — Data — Manim

- We collected data from three categories: Macro indicators — GDP, CPI, central
  bank rates, and current account for both the US and UK — come from the FRED
  and ONS APIs, while Forex OHLCV for 13 pairs and Equity OHLCV for 9 indices
  both come from yfinance.
- The pipeline runs in two stages: fetch scripts pull one raw CSV per indicator
  or instrument and keep the publication date so we never leak future
  information, then process scripts turn those raw files into clean,
  business-day-aligned daily panels.
- build_dataset.py merges all six panels into Dataset 1, which has 2,868 rows
  and 111 columns.
- Two more build scripts fork off that same Dataset 1: Dataset 2 adds a 90-day
  lookback of lagged features, and Dataset 3 adds technical indicators across
  all 17 instruments — Linh will cover how those two perform later.
- This ER diagram is our plan for how the collected data flows and joins
  together: all three domains key on date and merge into one ML_DATASET entity
  that in practice materializes as these three separate files.
- We investigated two features and had to exclude them: Composite PMI has no
  free 10-year history, and FX trading volume is either broker-only or absent
  in yfinance entirely.

---

## SLIDE 3 — Target Variable Definition — Somitha

- Our target is the next-day direction of GBP/USD close price — it's 1 if the
  price goes up, 0 otherwise.
- The class balance is 49.1% up versus 50.9% down, a ratio of 1.04, so the
  dataset is essentially balanced.
- The rolling chart confirms there's no persistent directional drift over the
  decade.

---

## SLIDE 4 — EDA: Macro, Forex, and Equity — Somitha

- For macro, the correlation heatmap shows the Fed and BoE rates move almost in
  lockstep at r≈0.94, and USA and UK CPI sit at r≈0.98.
- That's why we engineered rate_differential as its own feature, and why we use
  year-on-year CPI/GDP figures instead of the non-stationary levels.
- Missingness gaps concentrate in early 2014, and USA CPI YoY is the worst at
  10.5% missing.
- For forex, across GBP/USD and the other 13 pairs, the returns distribution
  shows GBP/USD skew of −0.91 and kurtosis of 14.4, with USD/CHF spiking as high
  as 230.
- That's why we use RobustScaler and clip outliers at 5 standard deviations.
- The correlation matrix shows GBP crosses cluster together and USD crosses
  cluster together, and rolling 30-day volatility spikes hardest around Brexit
  on July 22, 2016, peaking near 2,843% annualised.
- For equity, across our 9 indices, US indices rose 300 to 400% over the decade
  while UK's FTSE100 stayed flat.
- Correlation analysis found 5 of the 9 indices were redundant, so we dropped
  them and kept SP500, NASDAQ100, RUSSELL2000, and FTSE100.
- Volume skew drops from 1.66 to 0.76 after a square-root transform, and
  equity-versus-GBP/USD correlation shows UK indices are small positive/risk-on
  while US indices are weak and slightly negative, both under 0.3 in magnitude.

---

## SLIDE 5 — Pre-processing & Feature Engineering — Somitha

- CPI price levels trend upward monotonically, so they're non-stationary, and
  we use year-on-year inflation instead.
- We also dropped five equity indices that were near-identical to ones we kept.
- We added log returns for equity, the rate differential the EDA flagged as a
  key driver, and two date encodings — integers for tree models and
  sine-cosine pairs for linear models so December wraps around to January
  correctly.
- Imputation and scaling aren't part of this dataset-build step, because those
  are per-fold transforms that live inside the model pipeline Linh covers next.
- From this base dataset we branch into two more: a 90-day lookback with 9,111
  columns, and a technical-indicators version with about 1,178 columns across 17
  instruments, and Linh will show how those two actually perform.

---

## SLIDE 6 — Model Pipeline & Walk-Forward Folds — Linh

- Because GBP/USD is a time series, we use walk-forward cross-validation to
  avoid data leakage.
- The training window grows by one year each time, we always test on the year
  right after, and 2024 is held out completely until the final check.
- Every model uses the same 4-step pipeline: it cleans infinite values, fills
  missing data using only the training fold's median, rescales if the model
  needs it, and then fits.
- We repeat this six times, once per fold, so nothing leaks between folds.
- We trained and tuned 12 models across four families: two linear models, four
  tree-based models, four gradient boosting models, and two others — KNN and a
  small neural net.
- Eight more models are already coded in the registry but not trained yet,
  purely because of a time trade-off.

---

## SLIDE 7 — Hyperparameter & Model Training — Linh

- Every model goes through the same tuning steps: a Bayesian search of 50
  trials tunes hyperparameters on folds 1 through 4, then checks them on fold 5.
- Once we pick the best settings, we freeze them, and then we refit the model
  six times, once per fold, without searching again.
- Two results are worth flagging now because they explain the next slide:
  Bagging_LR's search landed on very weak regularization at C=5.50, and the
  Decision Tree got capped at depth 3.
- The tuning score doesn't reliably predict how well a model generalizes —
  Bagging_LR had the best tuning score of all 12 models, but one of the worst
  real results.
- That's exactly why we validate on genuinely held-out years next.

---

## SLIDE 8 — Evaluation & Results — Linh

- We check two numbers: accuracy, and Profit, which uses the same long/short
  formula as the reference paper to ask whether you'd actually make money in
  2024.
- Everything here uses the true 2024 test year, which was never touched during
  tuning.
- On Dataset 1, Bagging_LR wins on accuracy but is one of the worst models on
  Profit, while XGB and HGB are mid-table on accuracy but top the Profit
  ranking.
- On Dataset 3, almost every tree and boosting model reaches 70 to 83%
  accuracy, but 10 of those 12 models still lose money, so higher accuracy
  didn't mean higher profit.
- The bias-variance charts show this visually: on Dataset 1, CatBoost gives up
  a little accuracy for much better stability than the accuracy leader; on
  Dataset 2, every model sits near the coin-flip line regardless of stability,
  because the signal just isn't there; and on Dataset 3, almost every tree and
  boosting model lands in the best corner of high accuracy and low variance,
  except the Decision Tree, which is both the least stable and the only one
  below a coin flip.
- Zooming out, Dataset 2 is a clear negative result, and Dataset 3 wins on
  accuracy but that win doesn't carry over to risk-adjusted returns.
- Which model is "best" depends on what you're measuring: Bagging_LR wins on
  raw accuracy, but we recommend XGB and HGB, because they're the only two
  models where accuracy and Sharpe ratio agree.

---

## SLIDE 9 — Streamlit App — Linh

- The Streamlit app lets a user pick a dataset, pick one of the 12 trained
  models, and get an instant prediction — up or down — with a confidence score.
- Everything is pre-trained and loaded from disk, so nothing trains live.
- This session we added the dataset selector, so the app now works across all 3
  datasets.
- We also tested it in a real browser and confirmed switching datasets
  correctly reloads the right models instead of showing old results.

---

## SLIDE 10 — Conclusion & Takeaways — Linh

- We completed all four course goals: we collected data through a
  look-ahead-safe pipeline, ran EDA-driven feature engineering, trained and
  validated 12 models with proper walk-forward cross-validation across all 3
  datasets, and built a working Streamlit app on top.
- If you remember one thing, remember this: there is no single best model — it
  depends on whether you care about raw accuracy or whether the strategy
  actually makes money.
- We recommend XGB and HGB, because they're the only models where those two
  stories agree.
- Next steps are to train the remaining registry models, extend our backtest to
  Dataset 3, and dig into why more data didn't automatically mean better
  trading results.

---

## SLIDE 11 — References & AI Disclosure — (screen only)

(No speaker notes — shown on screen while transitioning to Q&A.)
