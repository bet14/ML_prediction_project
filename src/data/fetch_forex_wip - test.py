"""
WIP -- Forex OHLCV (13 pairs), daily, with a deliberate choice between TWO sources
controlled by --source. Read this docstring before picking one; the spec recommends
Dukascopy but the trade-off against yfinance is real and project-specific.

Why two sources
----------------
The data spec (References/GBPUSD_ML_data_requirements_spec.md, section 7) names
dukascopy.com as the suggested forex source. Dukascopy is a real ECN/liquidity
provider, so its tick volume is genuine traded volume -- unlike Yahoo Finance, whose
FX "Volume" field is widely reported (by yfinance users, in GitHub issues and forums)
to be unreliable or flatly zero for most currency pairs, because spot FX is
decentralized and Yahoo has no consolidated tape to source volume from. Since the
spec's per-pair OHLCV explicitly includes a volume column, this is a real data-quality
concern, not a hypothetical one.

The cost of following the spec's recommendation: Dukascopy's free historical access
(see "source: dukascopy" below) is at TICK level, one compressed file per pair PER
HOUR (https://datafeed.dukascopy.com/datafeed/{PAIR}/{YYYY}/{MM}/{DD}/{HH}h_ticks.bi5).
Building 2014-2024 daily OHLCV for 13 pairs this way means downloading, decompressing,
and aggregating roughly 13 pairs x 11 years x 365 days x 24 hours ~= 1.25 million hourly
files (fewer in practice -- weekends/holidays have no ticks -- but still on the order
of 800k-900k requests). This is exactly the kind of "tick-vs-bar, light-vs-heavy" choice
flagged as a transferable lesson in References/CLAUDE.md: implement BOTH paths and let
whoever runs this script decide based on whether genuine volume is worth the bandwidth
and runtime, rather than silently picking one.

    --source dukascopy (default, matches the spec)  -- heavy, genuine tick-derived volume
    --source yfinance  (=X tickers, e.g. EURUSD=X)   -- light, same mechanism as
                                                          fetch_equity_wip.py, but volume
                                                          column will likely be unreliable/zero

STATUS as of 2026-06-19
------------------------
Neither path has been run end-to-end in this session (no outbound network in the
Cowork sandbox). What IS verified:
  - Dukascopy URL pattern is LIVE: a GET against
    https://datafeed.dukascopy.com/datafeed/EURUSD/2024/00/15/10h_ticks.bi5 returned a
    real application/octet-stream binary body (not a 404/HTML error page) during this
    session's research pass.
  - The 20-byte tick record layout used by _decode_bi5() below (big-endian uint32
    time-delta-ms-since-hour-start, uint32 ask, uint32 bid, float32 ask-volume, float32
    bid-volume, raw price needing division by a per-pair point value) is corroborated by
    multiple independent community tools/write-ups found via WebSearch this session
    (dukascopy-node, assorted tick-data-downloader projects) -- it has NOT been decoded
    against one real downloaded .bi5 file inside this sandbox (no network to fetch one).
    _decode_bi5() does have an internal round-trip self-test (see test_decode_bi5_roundtrip()
    near the bottom) that LZMA-compresses a synthetic record with known values and confirms
    the decoder recovers them exactly -- this proves the decode *logic* is internally
    consistent, not that it matches Dukascopy's real byte layout. Treat the layout as
    "verified by convergent secondary sources", same epistemic status already used for the
    Dukascopy month-zero-indexing convention and the ^FTAS Yahoo ticker in fetch_equity_wip.py
    -- spot-check against one real day's data before trusting a full run.
  - Month is 0-indexed in the URL (Jan = "00") per the same convergent sources above; not
    decoded-and-cross-checked against a known calendar date in this session.
  - yfinance `=X` tickers for all 13 pairs follow the standard, long-stable Yahoo FX
    convention (BASEQUOTE=X) -- high confidence on the ticker names themselves; the
    volume-reliability concern above is the real risk for this path, not the symbol.

Implementation notes
---------------------
- Dukascopy path needs only the standard library (requests for HTTP, lzma + struct for
  decode -- no extra pip package, unlike the investing.com scraper's BeautifulSoup dep).
- Daily aggregation from ticks: open = first mid-price tick of the UTC day, high = max
  mid, low = min mid, close = last mid, volume = sum(ask_volume + bid_volume) over the
  day's ticks. "Mid price" = (ask + bid) / 2 after dividing by point_value.
- Weekends/holidays: Dukascopy serves a near-empty body for hours with zero ticks
  (LZMA stream that decompresses to 0 bytes). _decode_bi5() returns an empty list for
  these rather than raising -- treat as "no ticks that hour", not an error.
- Per-pair point_value: 1000 for JPY-quoted pairs (3 decimal places), 100000 for every
  other pair here (5 decimal places) -- standard Dukascopy/MT4-style convention.
- Resume safety: both paths are resume-safe. Dukascopy streams each completed day to
  disk immediately (never holds the full run in RAM then bulk-writes); if interrupted,
  the file contains all fully-completed days and the next run resumes from the day after
  the last date already in the file. yfinance reads the existing file, computes the
  missing date range, fetches only that, then merges+deduplicates before writing back.
  Neither path truncates or overwrites the existing file until a safe atomic rename.
- This script does not batch/parallelize the hourly downloads -- given the scale above,
  whoever runs --source dukascopy for a full 2014-2024/13-pair backfill should expect a
  long runtime and budget for resumability (the --append merge-on-date logic means a
  partial/interrupted run can simply be re-invoked with the same date range).
- Progress reporting (added 2026-06-19, after a real run looked hung with no output): by
  default every fetch prints what it is doing, where it is, and what it is waiting on --
  for --source dukascopy that means a continuously-updating line (interactive console) or
  one line per simulated day (redirected output) showing the pair, the UTC hour currently
  being requested, position/percent through the date range, ticks decoded so far, elapsed
  time, and an ETA extrapolated from the average time-per-request so far. A failed request
  is reported inline (pair, hour, exception) and that hour is skipped rather than crashing
  the whole run. Pass --quiet to suppress all of this (e.g. for automated/cron-style runs).

Usage
-----
    python fetch_forex_wip.py --verify-only                          # print URL/ticker mapping
    python fetch_forex_wip.py --self-test                            # run the bi5 decode round-trip test, no network
    python fetch_forex_wip.py --pair GBPUSD --source yfinance --start 2014-01-01 --end 2024-12-31 --append
    python fetch_forex_wip.py --pair GBPUSD --source dukascopy --start 2024-01-15 --end 2024-01-16
    python fetch_forex_wip.py --source dukascopy --append --quiet  # suppress progress output
"""

import argparse
import csv
import lzma
import struct
import sys
import time
from datetime import datetime, date, timedelta, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pipeline_log_common import append_run_log, make_run_record  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RAW_DIR = PROJECT_ROOT / "data" / "raw" / "forex"

# name -> (dukascopy symbol, yfinance ticker, output filename, point_value)
PAIRS = {
    "AUDUSD": ("AUDUSD", "AUDUSD=X", "AUD_USD.csv", 100000),
    "EURUSD": ("EURUSD", "EURUSD=X", "EUR_USD.csv", 100000),
    "EURGBP": ("EURGBP", "EURGBP=X", "EUR_GBP.csv", 100000),
    "GBPAUD": ("GBPAUD", "GBPAUD=X", "GBP_AUD.csv", 100000),
    "GBPCAD": ("GBPCAD", "GBPCAD=X", "GBP_CAD.csv", 100000),
    "GBPCHF": ("GBPCHF", "GBPCHF=X", "GBP_CHF.csv", 100000),
    "GBPJPY": ("GBPJPY", "GBPJPY=X", "GBP_JPY.csv", 1000),
    "GBPNZD": ("GBPNZD", "GBPNZD=X", "GBP_NZD.csv", 100000),
    "GBPUSD": ("GBPUSD", "GBPUSD=X", "GBP_USD.csv", 100000),  # the project's target pair
    "NZDUSD": ("NZDUSD", "NZDUSD=X", "NZD_USD.csv", 100000),
    "USDCAD": ("USDCAD", "USDCAD=X", "USD_CAD.csv", 100000),
    "USDCHF": ("USDCHF", "USDCHF=X", "USD_CHF.csv", 100000),
    "USDJPY": ("USDJPY", "USDJPY=X", "USD_JPY.csv", 1000),
}

DUKASCOPY_URL = "https://datafeed.dukascopy.com/datafeed/{symbol}/{y:04d}/{m:02d}/{d:02d}/{h:02d}h_ticks.bi5"
_TICK_STRUCT = struct.Struct(">IIIff")  # time_delta_ms, ask_raw, bid_raw, ask_vol, bid_vol

_CSV_COLUMNS = ["date", "open", "high", "low", "close", "volume"]


# ---------------------------------------------------------------------------
# Helpers: resume-safe file I/O
# ---------------------------------------------------------------------------

def _read_existing_dates(path: Path) -> set:
    """Return the set of date strings already present in an existing CSV, or empty set."""
    if not path.exists():
        return set()
    try:
        df = pd.read_csv(path, usecols=["date"])
        return set(df["date"].astype(str).str[:10].tolist())
    except Exception:
        return set()


def _last_date_in_file(path: Path) -> date | None:
    """Return the latest date already written to path, or None if file absent/empty."""
    if not path.exists():
        return None
    try:
        df = pd.read_csv(path, usecols=["date"])
        if df.empty:
            return None
        return pd.to_datetime(df["date"]).max().date()
    except Exception:
        return None


def _append_day_to_csv(path: Path, row: dict) -> None:
    """Append a single completed day row to the CSV file.
    Creates the file with header if it does not yet exist; appends without header
    if it already exists. This is the core of the Dukascopy resume-safety: each day
    is flushed to disk as soon as it is complete, so an interrupted run never loses
    already-processed days."""
    write_header = not path.exists() or path.stat().st_size == 0
    with path.open("a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=_CSV_COLUMNS)
        if write_header:
            writer.writeheader()
        writer.writerow({k: row[k] for k in _CSV_COLUMNS})


def _safe_write_csv(path: Path, df: pd.DataFrame) -> None:
    """Write df to path atomically via a .tmp sibling, so the existing file is never
    left in a truncated state if the process is killed mid-write."""
    tmp = path.with_suffix(".tmp.csv")
    df[_CSV_COLUMNS].to_csv(tmp, index=False)
    tmp.replace(path)  # atomic on POSIX; near-atomic on Windows (os.replace semantics)


# ---------------------------------------------------------------------------
# Dukascopy decode
# ---------------------------------------------------------------------------

def _dukascopy_url(symbol: str, hour_start: datetime) -> str:
    """hour_start is a UTC datetime truncated to the hour. Month in the URL is
    0-indexed (Jan="00") per convergent community sources -- see STATUS in the
    module docstring re: not yet decoded-and-cross-checked in this sandbox."""
    return DUKASCOPY_URL.format(
        symbol=symbol, y=hour_start.year, m=hour_start.month - 1,
        d=hour_start.day, h=hour_start.hour,
    )


def _decode_bi5(raw_bytes: bytes, point_value: int, hour_start: datetime) -> list[dict]:
    """Decompress one Dukascopy .bi5 hourly file and return a list of tick dicts with
    keys time (UTC datetime), ask, bid, ask_volume, bid_volume. Returns [] for an
    empty/near-empty hour (weekend, holiday) rather than raising."""
    if len(raw_bytes) == 0:
        return []
    try:
        decompressed = lzma.decompress(raw_bytes)
    except lzma.LZMAError:
        return []  # some "empty hour" responses aren't valid LZMA at all
    n_records = len(decompressed) // _TICK_STRUCT.size
    ticks = []
    for i in range(n_records):
        chunk = decompressed[i * _TICK_STRUCT.size:(i + 1) * _TICK_STRUCT.size]
        delta_ms, ask_raw, bid_raw, ask_vol, bid_vol = _TICK_STRUCT.unpack(chunk)
        ticks.append({
            "time": hour_start + timedelta(milliseconds=delta_ms),
            "ask": ask_raw / point_value,
            "bid": bid_raw / point_value,
            "ask_volume": ask_vol,
            "bid_volume": bid_vol,
        })
    return ticks


def test_decode_bi5_roundtrip() -> None:
    """No-network self-test: build one synthetic tick record, LZMA-compress it the
    same way Dukascopy would, and confirm _decode_bi5() recovers the exact values.
    Proves the decode logic is internally consistent -- does NOT prove it matches
    Dukascopy's real byte layout (no network in this sandbox to fetch a real file)."""
    point_value = 100000
    hour_start = datetime(2024, 1, 15, 10, tzinfo=timezone.utc)
    known = {"delta_ms": 1234, "ask_raw": 108550, "bid_raw": 108547, "ask_vol": 1.5, "bid_vol": 2.25}
    raw_record = _TICK_STRUCT.pack(
        known["delta_ms"], known["ask_raw"], known["bid_raw"], known["ask_vol"], known["bid_vol"]
    )
    compressed = lzma.compress(raw_record)
    ticks = _decode_bi5(compressed, point_value, hour_start)
    assert len(ticks) == 1, f"expected 1 tick, got {len(ticks)}"
    t = ticks[0]
    assert t["time"] == hour_start + timedelta(milliseconds=known["delta_ms"])
    assert abs(t["ask"] - known["ask_raw"] / point_value) < 1e-9
    assert abs(t["bid"] - known["bid_raw"] / point_value) < 1e-9
    assert abs(t["ask_volume"] - known["ask_vol"]) < 1e-6
    assert abs(t["bid_volume"] - known["bid_vol"]) < 1e-6
    # empty-hour case
    assert _decode_bi5(b"", point_value, hour_start) == []
    print("test_decode_bi5_roundtrip: PASS -- decode logic is internally consistent")


# ---------------------------------------------------------------------------
# Fetch functions
# ---------------------------------------------------------------------------

def fetch_via_dukascopy(
    name: str,
    start: str,
    end: str,
    verbose: bool = True,
    out_path: Path | None = None,
) -> pd.DataFrame:
    """Download every hourly .bi5 file for `name` in [start, end), decode ticks, and
    aggregate to daily OHLCV.

    Resume safety
    -------------
    When out_path is given and the file already exists, the function reads the last
    date already present and advances start_dt to the day after that date, skipping
    all already-downloaded data. Each completed day is written (appended) to out_path
    immediately -- if the process is killed mid-run, the file retains every day that
    was fully processed before the interruption. Re-running with the same arguments
    resumes from where it stopped.

    When out_path is None (dry-run / --no-append), all data is accumulated in RAM and
    returned as a DataFrame at the end (original behaviour, no resume possible).
    """
    import requests

    symbol, _, _, point_value = PAIRS[name]
    start_dt = datetime.strptime(start, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    end_dt   = datetime.strptime(end,   "%Y-%m-%d").replace(tzinfo=timezone.utc)

    # --- resume: skip dates already on disk ---
    if out_path is not None:
        last_done = _last_date_in_file(out_path)
        if last_done is not None:
            resume_from = datetime(last_done.year, last_done.month, last_done.day,
                                   tzinfo=timezone.utc) + timedelta(days=1)
            if resume_from >= end_dt:
                if verbose:
                    print(f"[{name}] dukascopy: file da co du lieu den {last_done}, khong can download them")
                return pd.read_csv(out_path)
            if verbose:
                print(f"[{name}] dukascopy: tiep tuc tu {resume_from.date()} (da co du lieu den {last_done})")
            start_dt = resume_from

    total_hours = max(int((end_dt - start_dt).total_seconds() // 3600), 1)
    is_tty = sys.stdout.isatty()
    print_every = 1 if is_tty else 24  # interactive: every request; redirected: ~once/day

    # current_day accumulates ticks for the day being processed
    current_day: date | None = None
    day_prices: list[float] = []
    day_volume: float = 0.0

    # in-RAM accumulator used only when out_path is None (dry-run)
    ram_rows: list[dict] = []

    def _flush_day() -> None:
        """Write the completed current_day to disk (or RAM) and reset accumulators."""
        nonlocal current_day, day_prices, day_volume
        if current_day is None or not day_prices:
            current_day = None
            day_prices = []
            day_volume = 0.0
            return
        row = {
            "date":   str(current_day),
            "open":   day_prices[0],
            "high":   max(day_prices),
            "low":    min(day_prices),
            "close":  day_prices[-1],
            "volume": day_volume,
        }
        if out_path is not None:
            _append_day_to_csv(out_path, row)
        else:
            ram_rows.append(row)
        current_day = None
        day_prices = []
        day_volume = 0.0

    hour = start_dt
    n = 0
    n_ticks_total = 0
    n_failed = 0
    t0 = time.time()

    while hour < end_dt:
        n += 1
        if verbose and (n % print_every == 0 or hour + timedelta(hours=1) >= end_dt):
            elapsed = time.time() - t0
            pct = n / total_hours * 100
            eta_s = (elapsed / n) * (total_hours - n)
            line = (
                f"[{name}] dukascopy: dang tai {hour:%Y-%m-%d %Hh}Z "
                f"({n}/{total_hours}, {pct:4.1f}%) ticks={n_ticks_total} loi={n_failed} "
                f"elapsed={elapsed / 60:.1f}p ETA={eta_s / 60:.1f}p"
            )
            if is_tty:
                sys.stdout.write("\r" + line + "    ")
            else:
                print(line)
            sys.stdout.flush()

        url = _dukascopy_url(symbol, hour)
        try:
            resp = requests.get(url, timeout=30)
        except requests.exceptions.RequestException as exc:
            n_failed += 1
            if verbose:
                print(f"\n[{name}] WARN request loi tai {hour:%Y-%m-%d %Hh}Z: {exc} -- bo qua gio nay")
            hour += timedelta(hours=1)
            continue

        if resp.status_code == 200:
            for tick in _decode_bi5(resp.content, point_value, hour):
                tick_day = tick["time"].date()
                # crossed into a new calendar day -> flush the previous day to disk
                if tick_day != current_day:
                    _flush_day()
                    current_day = tick_day
                mid = (tick["ask"] + tick["bid"]) / 2
                day_prices.append(mid)
                day_volume += tick["ask_volume"] + tick["bid_volume"]
                n_ticks_total += 1

        # flush at end of each UTC hour boundary crossing a day boundary
        # (handles the case where the last tick of a day is in an earlier hour
        #  and the next hour belongs to a new day with zero ticks)
        next_hour = hour + timedelta(hours=1)
        if current_day is not None and next_hour.date() != hour.date():
            _flush_day()

        hour = next_hour

    # flush whatever is left in the buffer (last partial day)
    _flush_day()

    if verbose and is_tty:
        print()  # move off the in-place progress line

    if out_path is not None:
        # return the full file (existing + newly downloaded) as a DataFrame
        if not out_path.exists():
            raise ValueError(f"[{name}] no data written to {out_path}")
        df = pd.read_csv(out_path)
        # safety dedup in case of any edge-case double-write
        df = df.drop_duplicates(subset=["date"]).sort_values("date").reset_index(drop=True)
        _safe_write_csv(out_path, df)
        return df

    if not ram_rows:
        raise ValueError(f"[{name}] no ticks decoded for {start}..{end} via Dukascopy")
    return pd.DataFrame(ram_rows)


def fetch_via_yfinance(
    name: str,
    start: str,
    end: str,
    verbose: bool = True,
    out_path: Path | None = None,
) -> pd.DataFrame:
    """Same mechanism as fetch_equity_wip.py's fetch_index() -- yfinance handles
    Yahoo's cookie/crumb negotiation internally. Volume column is expected to be
    unreliable/zero for FX -- see module docstring.

    Resume safety
    -------------
    When out_path is given and the file already exists, the function reads the last
    date already present and fetches only the missing tail (last_date+1 .. end).
    The new rows are merged with the existing data, deduplicated on date, and written
    back atomically via a .tmp sibling file so the original is never left truncated.
    """
    import yfinance as yf

    _, ticker, _, _ = PAIRS[name]

    effective_start = start
    existing_df: pd.DataFrame | None = None

    # --- resume: compute the missing tail ---
    if out_path is not None and out_path.exists():
        try:
            existing_df = pd.read_csv(out_path)
            if not existing_df.empty:
                last_done = pd.to_datetime(existing_df["date"]).max().date()
                fetch_from = last_done + timedelta(days=1)
                fetch_from_str = fetch_from.strftime("%Y-%m-%d")
                if fetch_from_str >= end:
                    if verbose:
                        print(f"[{name}] yfinance: file da co du lieu den {last_done}, khong can download them")
                    return existing_df
                if verbose:
                    print(f"[{name}] yfinance: tiep tuc tu {fetch_from_str} (da co du lieu den {last_done})")
                effective_start = fetch_from_str
        except Exception:
            existing_df = None  # corrupted file -- re-fetch everything

    if verbose:
        print(
            f"[{name}] yfinance: dang goi yf.Ticker('{ticker}').history("
            f"start={effective_start}, end={end}) ...",
            flush=True,
        )
    t0 = time.time()
    hist = yf.Ticker(ticker).history(start=effective_start, end=end, auto_adjust=False)
    if verbose:
        print(f"[{name}] yfinance: phan hoi sau {time.time() - t0:.1f}s, {len(hist)} dong tho", flush=True)

    if hist.empty and existing_df is None:
        raise ValueError(f"[{name}] yfinance returned 0 rows for ticker {ticker!r}")

    new_df: pd.DataFrame | None = None
    if not hist.empty:
        out = hist.reset_index()[["Date", "Open", "High", "Low", "Close", "Volume"]]
        out.columns = _CSV_COLUMNS
        out["date"] = pd.to_datetime(out["date"]).dt.tz_localize(None).dt.strftime("%Y-%m-%d")
        new_df = out.sort_values("date").reset_index(drop=True)

    # merge existing + new, dedup
    parts = [p for p in [existing_df, new_df] if p is not None and not p.empty]
    if not parts:
        raise ValueError(f"[{name}] yfinance: nessun dato disponibile per {ticker!r}")
    merged = pd.concat(parts, ignore_index=True)
    merged["date"] = pd.to_datetime(merged["date"]).dt.strftime("%Y-%m-%d")
    merged = merged.drop_duplicates(subset=["date"]).sort_values("date").reset_index(drop=True)

    if out_path is not None:
        _safe_write_csv(out_path, merged)

    return merged


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", default=str(DEFAULT_RAW_DIR))
    parser.add_argument("--start", default="2014-01-01")
    parser.add_argument("--end", default="2024-12-31")
    parser.add_argument("--pair", default=None, help="fetch only this pair (see PAIRS keys); default: all 13")
    parser.add_argument("--source", choices=["dukascopy", "yfinance"], default="dukascopy")
    parser.add_argument("--verify-only", action="store_true", help="print URL/ticker mapping, fetch nothing")
    parser.add_argument("--self-test", action="store_true", help="run the no-network bi5 decode round-trip test")
    parser.add_argument("--append", action="store_true", help="write CSVs to --out-dir (default: print only)")
    parser.add_argument("--quiet", action="store_true", help="suppress progress reporting (e.g. for cron-style runs)")
    args = parser.parse_args()

    if args.self_test:
        test_decode_bi5_roundtrip()
        return

    names = [args.pair] if args.pair else list(PAIRS)
    verbose = not args.quiet

    if args.verify_only:
        for name in names:
            symbol, ticker, filename, point_value = PAIRS[name]
            sample_url = _dukascopy_url(symbol, datetime(2024, 1, 15, 10, tzinfo=timezone.utc))
            print(f"{name:8s} dukascopy={symbol:8s} ({sample_url})  yfinance={ticker:10s}  point_value={point_value}  -> {filename}")
        return

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    fetch_fn = fetch_via_dukascopy if args.source == "dukascopy" else fetch_via_yfinance

    if verbose:
        print(f"=== fetch_forex_wip: {len(names)} pair(s), source={args.source}, {args.start}..{args.end} ===")
        if args.source == "dukascopy":
            print("(dukascopy = 1 request/gio cho moi pair; xem docstring de biet uoc tinh tong so request)")

    run_t0 = time.time()
    steps = []
    for i, name in enumerate(names, start=1):
        _, _, filename, _ = PAIRS[name]
        out_path = (out_dir / filename) if args.append else None
        if verbose:
            print(f"--- [{i}/{len(names)}] {name} ({args.source}) ---")
        step_t0 = time.time()
        try:
            df = fetch_fn(name, args.start, args.end, verbose=verbose, out_path=out_path)
        except Exception as exc:  # noqa: BLE001 -- record and continue with other pairs
            elapsed = time.time() - step_t0
            print(f"[{name}] FAILED ({args.source}) sau {elapsed:.1f}s -- {exc}")
            steps.append({"pair": name, "source": args.source, "ok": False, "error": str(exc), "elapsed_seconds": round(elapsed, 1)})
            continue

        elapsed = time.time() - step_t0
        if args.append:
            print(f"[{name}] {args.source} -> {out_path} ({len(df)} rows, {elapsed:.1f}s)")
        else:
            print(f"[{name}] {args.source}: {len(df)} rows, not saved (pass --append to write) ({elapsed:.1f}s)")
        steps.append({"pair": name, "source": args.source, "ok": True, "rows": len(df), "elapsed_seconds": round(elapsed, 1)})

    total_elapsed = time.time() - run_t0
    if verbose:
        ok = sum(1 for s in steps if s.get("ok"))
        print(f"=== Hoan tat: {ok}/{len(names)} pair thanh cong, tong {total_elapsed / 60:.1f} phut ===")

    append_run_log(make_run_record(
        pipeline="forex",
        mode=f"{args.source}/{'append' if args.append else 'dry-run'}",
        steps=steps,
        start_arg=args.start,
        end_arg=args.end,
        total_elapsed_seconds=round(total_elapsed, 1),
    ))


if __name__ == "__main__":
    main()