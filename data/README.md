# data/

- `raw/` — raw data, downloaded as-is, never edited by hand. Three subfolders by source:
  - `forex/` — GBP/USD OHLCV and correlated FX pairs (Dukascopy)
  - `macro/` — UK/US macro indicators (FRED, ONS)
  - `equity/` — equity indices: FTSE100, FTSE250, S&P500, Nasdaq100, DJI, DAX, VIX (yfinance)
- `interim/` — data merged across multiple sources by date, not yet feature-engineered; used for debugging the intermediate pipeline.
- `processed/` — the final 3 dataset variants used for train/validate/test:
  - Dataset 1 — Basic Daily
  - Dataset 2 — 90-Day Lookback
  - Dataset 3 — Technical Indicators (SMA, WMA, RSI, MACD, Stochastic, Momentum, CCI, ROC, Williams %R, A/D, Disparity, OSCP)

Downloading data into `raw/` must happen outside Cowork (personal machine/Colab/Kaggle) since the sandbox has no network — see the project root README.
