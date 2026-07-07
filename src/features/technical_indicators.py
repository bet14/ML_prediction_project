"""
Compute technical indicators for a single instrument (one forex pair or one
equity index), using the `ta` library.

Implements 12 of the 16 indicator families from spec section 2.4
(`References/GBPUSD_ML_data_requirements_spec.md`). 4 families have no
direct equivalent in `ta` and are skipped entirely (no hand-written
substitute) per the decision in `References/DATASET_2_3_PLAN.md`
("QUYET DINH DA CHOT - 2026-07-04", Q4):
    - #5  Momentum N-day
    - #10 A/D Oscillator (ta.volume.acc_dist_index is a different formula --
          Chaikin's A/D Line, not the paper's Williams A/D Oscillator)
    - #13 Disparity N-day
    - #14 OSCP N/M-day

Column count per instrument (see compute_technical_indicators docstring):
    - Forex (no volume):   60 cols
    - Equity (has volume): 72 cols (60 + 12 volume MA/WMA cols)

Note: some `ta` functions use different smoothing conventions than the paper
(e.g. Wilder's smoothing for RSI/CCI vs. the spec's plain rolling mean) --
an accepted, documented deviation, not a bug.
"""

import pandas as pd
import ta.momentum as momentum
import ta.trend as trend

# N-day windows per family, from spec section 2.4.
N_LIST = [3, 7, 14, 30, 60, 90]              # families 1, 2, 3, 4
N_LIST_WIDE = [1, 2, 3, 7, 14, 30, 60, 90]   # families 6, 7, 9, 12
N_LIST_NARROW = [7, 14, 30, 60, 90]          # families 8, 11
MACD_PAIRS = [(7, 21), (12, 26), (20, 34)]                     # family 15 (fast, slow)
MACD_SIGNAL_TRIPLES = [(7, 21, 4), (12, 26, 9), (20, 34, 17)]  # family 16 (fast, slow, sign)


def compute_technical_indicators(df: pd.DataFrame, has_volume: bool) -> pd.DataFrame:
    """
    Compute the 12 available technical-indicator families for one instrument.

    Parameters
    ----------
    df : DataFrame indexed by date, with unprefixed columns
         open, high, low, close (+ volume if has_volume=True).
    has_volume : True for equity indices, False for forex pairs.

    Returns
    -------
    DataFrame of indicator columns (unprefixed), same index as df.
    60 columns if has_volume=False, 72 columns if has_volume=True.
    """
    high, low, close = df["high"], df["low"], df["close"]
    out = {}

    # Family 1: Simple N-day MA (close)
    for n in N_LIST:
        out[f"sma_close_{n}"] = trend.sma_indicator(close, window=n)

    # Family 2: Weighted N-day MA (close)
    for n in N_LIST:
        out[f"wma_close_{n}"] = trend.wma_indicator(close, window=n)

    # Families 3-4: Simple/Weighted N-day MA (volume) -- equity only
    if has_volume:
        volume = df["volume"]
        for n in N_LIST:
            out[f"sma_volume_{n}"] = trend.sma_indicator(volume, window=n)
        for n in N_LIST:
            out[f"wma_volume_{n}"] = trend.wma_indicator(volume, window=n)

    # Families 6-7: Stochastic %K / %D
    # %D(N) = N-day mean of %K(N) per spec -- same N drives both window and smooth_window.
    for n in N_LIST_WIDE:
        out[f"stoch_k_{n}"] = momentum.stoch(high, low, close, window=n)
        out[f"stoch_d_{n}"] = momentum.stoch_signal(high, low, close, window=n, smooth_window=n)

    # Family 8: RSI
    for n in N_LIST_NARROW:
        out[f"rsi_{n}"] = momentum.rsi(close, window=n)

    # Family 9: Larry Williams %R
    for n in N_LIST_WIDE:
        out[f"williams_r_{n}"] = momentum.williams_r(high, low, close, lbp=n)

    # Family 11: CCI
    for n in N_LIST_NARROW:
        out[f"cci_{n}"] = trend.cci(high, low, close, window=n)

    # Family 12: ROC (close)
    for n in N_LIST_WIDE:
        out[f"roc_{n}"] = momentum.roc(close, window=n)

    # Family 15: MACD
    for fast, slow in MACD_PAIRS:
        out[f"macd_{fast}_{slow}"] = trend.macd(close, window_fast=fast, window_slow=slow)

    # Family 16: MACD signal
    for fast, slow, sign in MACD_SIGNAL_TRIPLES:
        out[f"macd_signal_{fast}_{slow}_{sign}"] = trend.macd_signal(
            close, window_fast=fast, window_slow=slow, window_sign=sign
        )

    return pd.DataFrame(out, index=df.index)
