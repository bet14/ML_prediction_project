# GBP/USD Direction Prediction — Data Requirements & Processing Specification

Adapted from: Guyard, K. C. & Deriaz, M. (2024). *Predicting Foreign Exchange EURUSD direction using machine learning*. MLMI 2024.

This document re-applies the paper's methodology to the GBP/USD pair, substituting the United Kingdom (UK) for the European Area (EA) as the second economic block (alongside the United States, USA).

## 1. Objective

Predict the next-day directional movement of GBP/USD:

```
Direction(t) = 1  if close_price(t+1) > close_price(t)
Direction(t) = 0  if close_price(t+1) <= close_price(t)
```

One row = one trading day. Days immediately preceding a market closure are excluded (no price movement to predict).

## 2. Data requirements

### 2.1 Economic indicators (USA and UK)

Six indicators per block, each forward-filled between releases plus a companion "days since last update" column (same rationale as the paper: traders react to the last known release, not the true continuous value, and releases themselves trigger volatility).

| Indicator | Frequency | USA source | UK source |
|---|---|---|---|
| GDP | Quarterly | FRED, BEA | ONS |
| Composite PMI | Monthly | S&P Global/ISM, investing.com | S&P Global/CIPS, investing.com |
| CPI | Monthly | BLS, FRED | ONS |
| CPI YoY (inflation rate) | Monthly | BLS, FRED | ONS |
| Central bank interest rate | Irregular | Federal Reserve (Fed Funds Rate) | Bank of England (Bank Rate) |
| Current Account Balance | Monthly | BEA, FRED | ONS |

Column count: 6 indicators × 2 blocks × (value + days-since-update) = 24 columns.

### 2.2 Market indices

US leg (unchanged from the paper): DJI, NASDAQ Composite, NASDAQ100, RUSSELL2000, S&P500.

UK leg (replaces CAC40 / DAX / STOXX50 / STOXX600): FTSE100 (large-cap, mirrors CAC40/DAX), FTSE250 (mid-cap), FTSE350 (100+250 combined, mirrors STOXX50's broader blue-chip role), FTSE All-Share (broadest UK benchmark, mirrors STOXX600's broad-coverage role).

9 indices total. Each contributes open, close, low, high, volume → 45 columns.

### 2.3 Forex pairs

The paper includes every major pair touching either target currency (EUR or USD). Mirrored for GBP/USD:

AUD/USD, EUR/USD, EUR/GBP, GBP/AUD, GBP/CAD, GBP/CHF, GBP/JPY, GBP/NZD, GBP/USD, NZD/USD, USD/CAD, USD/CHF, USD/JPY — 13 pairs.

Each contributes open, close, low, high → 52 columns. (Volume excluded — yfinance FX volume = 0; spot FX has no consolidated tape.)

### 2.4 Technical indicators (dataset 3 only)

Same indicator families as Table 1 of the paper, computed independently per instrument from that instrument's own OHLC(V) series. Rows 3–4 (volume MAs) apply to equity indices only — forex volume is excluded (see section 2.3). C/H/L(t) are close/high/low at day t; HH/LL(i,j) are the highest/lowest price between days i and j; Up/Dw(t) are the day's upward/downward price change; M(t)=(H(t)+L(t)+C(t))/3; SM(t) = N-day mean of M; D(t) = N-day mean of (M − SM); EMA = exponential moving average.

| # | Name | Formula (informal) | Parameter range | Applies to |
|---|---|---|---|---|
| 1 | Simple N-day MA (close) | mean of C(t)..C(t-N+1) | N ∈ {3,7,14,30,60,90} | all |
| 2 | Weighted N-day MA (close) | weighted mean of C(t-i), weight (N-i) | N ∈ {3,7,14,30,60,90} | all |
| 3 | Simple N-day MA (volume) | mean of V(t)..V(t-N+1) | N ∈ {3,7,14,30,60,90} | equity only |
| 4 | Weighted N-day MA (volume) | weighted mean of V(t-i), weight (N-i) | N ∈ {3,7,14,30,60,90} | equity only |
| 5 | Momentum N-day | C(t) − C(t-N) | N ∈ {1,2,3,7,14,30,60,90} |
| 6 | Stochastic K% N-day | 100·(C(t)−LL)/(HH−LL) over window N | N ∈ {1,2,3,7,14,30,60,90} |
| 7 | Stochastic D% N-day | N-day mean of Stochastic K% | N ∈ {1,2,3,7,14,30,60,90} |
| 8 | RSI N-day | 100 − 100/(1 + avg_up/avg_down) over window N | N ∈ {7,14,30,60,90} |
| 9 | Larry Williams %R N-day | 100·(H(t-N)−C(t))/(H(t-N)−L(t-N)) | N ∈ {1,2,3,7,14,30,60,90} |
| 10 | A/D Oscillator | (H(t)−C(t-1))/(H(t)−L(t)) | none |
| 11 | CCI N-day | (M(t)−SM(t))/(0.015·D(t)) | N ∈ {7,14,30,60,90} |
| 12 | ROC close N-day | 100·C(t)/C(t-N) | N ∈ {1,2,3,7,14,30,60,90} |
| 13 | Disparity N-day | 100·C(t)/[N-day mean of C] | N ∈ {3,7,14,30,60,90} |
| 14 | OSCP N/M-day | (sumN(C)−sumM(C))/sumN(C) | (N,M) ∈ {(3,7),(7,14),(14,30),(30,60),(60,90)} |
| 15 | MACD N-fast/M-slow | EMA_N(t) − EMA_M(t) | (N,M) ∈ {(7,21),(12,26),(20,34)} |
| 16 | MACD N/M/P-signal | EMA_P of MACD_N,M(t) | (N,M,P) ∈ {(7,21,4),(12,26,9),(20,34,17)} |

Per-instrument column count ≈ 92 for equity (all families); ≈ 80 for forex (rows 3–4 excluded). Across 9 indices (×92) + 13 pairs (×80) = 828 + 1,040, dataset 3 adds roughly **1,870 columns** — by far the largest feature block. This is why the paper relies on Bayesian-search feature selection rather than feeding all of them at once; plan the same trimming step here.

## 3. Processing pipeline

**Join key:** calendar date. Economic indicators are forward-filled (each day carries the most recent released value).

**Transforms:**
- log transform → UK CPI YoY (mirrors the paper's EA CPI YoY log transform; same right-skew rationale)
- sqrt transform → both central bank rates (Bank Rate, Fed Funds Rate) and every equity index volume column (forex volume excluded — see section 2.3)

**Date encoding:**
- Tree-based models: day (int), month (int), weekday (int) — ordinal, no one-hot
- Other models: sin/cos pair for day, month, and weekday separately

**Three dataset variants:**
- Dataset 1: daily features only (sections 2.1–2.3)
- Dataset 2: dataset 1 + each feature's value for the preceding 90 days (lag stack)
- Dataset 3: dataset 1 + technical indicators (section 2.4)

## 4. Target

`Direction(t)` ∈ {0,1}, from GBP/USD close price only — see section 1.

## 5. Worked example — 2024-03-15 (synthetic, illustrative only, not real historical data)

### 5.1 Raw source rows

Economic indicators (last release as of 2024-03-15):

| Indicator | Block | Value | Last release | Days since update |
|---|---|---|---|---|
| GDP QoQ | UK | 0.6% | 2024-02-15 | 29 |
| Composite PMI | UK | 52.9 | 2024-03-01 | 14 |
| CPI YoY | UK | 3.4% | 2024-02-14 | 30 |
| Bank Rate | UK | 5.25% | 2023-08-03 | 225 |
| Current Account Balance | UK | -£21.2bn | 2023-12-29 | 77 |
| GDP QoQ (annualized) | USA | 3.2% | 2024-02-28 | 16 |
| Composite PMI | USA | 52.5 | 2024-03-01 | 14 |
| CPI YoY | USA | 3.2% | 2024-02-13 | 31 |
| Fed Funds Rate | USA | 5.50% | 2023-07-27 | 232 |
| Current Account Balance | USA | -$195.7bn | 2023-12-21 | 85 |

Market index OHLCV (2024-03-15), two of nine shown:

| Index | Open | Close | Low | High | Volume |
|---|---|---|---|---|---|
| FTSE100 | 7738 | 7722 | 7705 | 7745 | 750,000 |
| S&P500 | 5170 | 5117 | 5104 | 5176 | 3,200,000 |

Forex pair OHLC (2024-03-15), three of thirteen shown (volume excluded):

| Pair | Open | Close | Low | High |
|---|---|---|---|---|
| GBP/USD | 1.2750 | 1.2730 | 1.2705 | 1.2765 |
| EUR/USD | 1.0890 | 1.0880 | 1.0855 | 1.0900 |
| GBP/JPY | 192.40 | 191.80 | 191.50 | 192.80 |

### 5.2 After transform

| Feature | Raw | Transform | Result |
|---|---|---|---|
| UK CPI YoY | 3.4 | ln(x) | 1.2238 |
| UK Bank Rate | 5.25 | sqrt(x) | 2.2913 |
| US Fed Funds Rate | 5.50 | sqrt(x) | 2.3452 |
| FTSE100 volume | 750,000 | sqrt(x) | 866.03 |

### 5.3 Date encoding (2024-03-15, Friday, day-of-year 75 in a leap year)

- Tree-based: day=15, month=3, weekday=4 (Friday, 0=Monday)
- Cyclical: day_sin = sin(2π·75/366) ≈ 0.9601, day_cos = cos(2π·75/366) ≈ 0.2795 (month and weekday get their own sin/cos pairs the same way, with period 12 and 7 respectively)

### 5.4 Dataset-3 technical indicator example

Synthetic GBP/USD close-price history:

| Date | Close |
|---|---|
| 2024-03-12 | 1.2790 |
| 2024-03-13 | 1.2765 |
| 2024-03-14 | 1.2742 |
| 2024-03-15 | 1.2730 |

- Simple 3-day MA (close) at t=2024-03-15: (1.2730+1.2742+1.2765)/3 = **1.2746**
- Momentum 1-day at t=2024-03-15: 1.2730 − 1.2742 = **−0.0012**

Every other (indicator × N) combination, for every one of the 22 instruments, is computed the same way, producing the ~2,000-column block from section 2.4.

### 5.5 Target label

GBP/USD close(2024-03-15) = 1.2730. If the next trading day's close (2024-03-18; 16th/17th are weekend) is, say, 1.2758, then Direction(2024-03-15) = **1** (up).

## 6. Open decisions to confirm before building the pipeline

- UK index basket (FTSE100/250/350/All-Share) is one reasonable mirror of CAC40/DAX/STOXX50/STOXX600 — could be trimmed to just FTSE100 + FTSE250 instead.
- Whether to keep EA data (CAC40, DAX, EUR-area indicators) as an auxiliary signal, since EUR/USD and GBP/USD are correlated.
- History start/end date for data collection (the paper used 2013-04-30 to 2022-12-31).
- Which subset of the ~2,000 dataset-3 columns to keep — the paper's answer was Bayesian-search feature selection rather than a fixed manual subset.
- Per-source vendor/API choice (ONS and BoE both publish free CSV/API downloads, similar in spirit to FRED).

## 7. Suggested data sources

- US economic indicators: fred.stlouisfed.org, data.bls.gov, data.oecd.org, investing.com, macrovar.com
- UK economic indicators: ons.gov.uk, bankofengland.co.uk/statistics, data.oecd.org, investing.com, macrovar.com
- Market data (all 9 indices): finance.yahoo.com
- Forex data (all 13 pairs): dukascopy.com
