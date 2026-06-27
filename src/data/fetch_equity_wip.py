"""
WIP -- Equity indices (9 total: 5 USA + 4 UK), daily OHLCV, via yfinance.

Per the data spec (References/GBPUSD_ML_data_requirements_spec.md, section 2.2 +
section 7), the suggested source for all 9 indices is Yahoo Finance / yfinance --
unlike forex (see fetch_forex_wip.py), there is no source-choice ambiguity here.

STATUS as of 2026-06-19: code complete, NOT yet run (no outbound network in the
Cowork sandbox -- must run on a personal machine/Colab, see README "Important note").
Ticker symbols below were checked via public web search, not via a live yfinance call
in this sandbox -- confidence varies per ticker, see INDICES comments. Two direct
verification attempts against Yahoo Finance both failed in this sandbox:
  1. GET https://finance.yahoo.com/quote/%5EFTAS/         -> empty body (JS-rendered
     SPA; raw HTML fetch cannot see content that loads via client-side JS).
  2. GET https://query1.finance.yahoo.com/v8/finance/chart/%5EFTAS?range=5d&interval=1d
     -> also empty body. This is consistent with Yahoo's chart/quote JSON endpoints
     now requiring a session cookie + "crumb" token for unauthenticated callers (a
     change Yahoo rolled out progressively; community yfinance issue trackers describe
     exactly this), which a bare GET without that handshake will not satisfy. This is
     NOT evidence the ticker is wrong -- it is evidence that hand-rolled requests
     against Yahoo's raw endpoints are the wrong tool. The `yfinance` package (already
     in requirements.txt) handles the cookie/crumb negotiation internally, which is
     exactly why this project depends on that package instead of requests+BeautifulSoup
     here (contrast with fetch_composite_pmi_wip.py, where investing.com's calendar
     pages ARE plain server-rendered HTML and requests+BeautifulSoup is the right tool).

Ticker confidence
-----------------
USA (high confidence -- standard, long-stable Yahoo tickers):
    ^DJI (Dow Jones Industrial Average), ^GSPC (S&P 500), ^IXIC (Nasdaq Composite),
    ^NDX (Nasdaq-100), ^RUT (Russell 2000).
UK (checked via web search 2026-06-19, same "dot becomes caret" family pattern Yahoo
   uses across the FTSE index family -- but NOT live-confirmed against a real yfinance
   call in this sandbox):
    ^FTSE (FTSE 100 -- high confidence, long-stable), ^FTMC (FTSE 250 -- moderate
    confidence, search-corroborated), ^FTLC (FTSE 350 -- moderate confidence,
    search-corroborated), ^FTAS (FTSE All-Share -- LOWEST confidence: inferred from the
    same naming family as the other three FTSE tickers and from Reuters RIC convention
    ".FTAS", but the live double-check above failed for sandbox-environment reasons,
    not because the ticker was refuted. Spot-check this one first when running on a
    personal machine -- `yf.Ticker("^FTAS").history(period="5d")` should return non-empty
    rows; if it returns empty, search "FTSE All-Share yahoo finance ticker" again for a
    corrected symbol before trusting the rest of the run.

Implementation notes
---------------------
- Uses `yfinance` (already in requirements.txt). One `yf.Ticker(ticker).history(...)`
  call per index -- no batching, since each index has an independent first-trade date
  and silent partial failures are easier to diagnose one at a time (same
  per-instrument-coverage caution as the macro indicators -- see References/CLAUDE.md
  "Kinh nghiem ... khong gia dinh do sau lich su dong nhat").
- Output columns: date, open, high, low, close, volume (volume is genuine share-volume
  for equity indices -- unlike FX, this is NOT the unreliable-volume case; that concern
  is specific to forex, see fetch_forex_wip.py).
- `--raw-dump` prints the first 5 raw rows yfinance returns for one ticker, before any
  reshaping -- same raw-dump-first discipline used for the ONS/investing.com scripts.

Progress reporting (added 2026-06-19, same motivation as fetch_forex_wip.py: a real
run looked hung with no output): by default each index prints a before/after message
with elapsed time -- yfinance's `.history()` is one blocking call per index, not a
loop, so there is no live percent/ETA line here, just "doing X now" / "X took Ns,
got N rows". `main()` also prints an overall banner and a per-index "[i/9]" header so
it is always visible which index is in flight. Pass --quiet to suppress all of this.

Usage
-----
    python fetch_equity_wip.py --verify-only            # list tickers, fetch nothing
    python fetch_equity_wip.py --raw-dump --index FTAS  # print raw yfinance output for one index
    python fetch_equity_wip.py --start 2014-01-01 --end 2024-12-31           # fetch all 9, print only
    python fetch_equity_wip.py --start 2014-01-01 --end 2024-12-31 --append # fetch all 9, write CSVs
    python fetch_equity_wip.py --append --quiet         # fetch all 9, suppress progress output
"""

import argparse
import time
from pathlib import Path

import pandas as pd

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pipeline_log_common import append_run_log, make_run_record  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RAW_DIR = PROJECT_ROOT / "data" / "raw" / "equity"

# name -> (yfinance ticker, output filename, block)
INDICES = {
    "DJI":              ("^DJI",  "USA_DJI.csv",               "USA"),
    "NASDAQ_COMPOSITE":  ("^IXIC", "USA_NASDAQ_COMPOSITE.csv",  "USA"),
    "NASDAQ100":         ("^NDX",  "USA_NASDAQ100.csv",         "USA"),
    "RUSSELL2000":       ("^RUT",  "USA_RUSSELL2000.csv",       "USA"),
    "SP500":             ("^GSPC", "USA_SP500.csv",             "USA"),
    "FTSE100":           ("^FTSE", "UK_FTSE100.csv",            "UK"),
    "FTSE250":           ("^FTMC", "UK_FTSE250.csv",            "UK"),
    "FTSE350":           ("^FTLC", "UK_FTSE350.csv",            "UK"),
    "FTAS":              ("^FTAS", "UK_FTSE_ALL_SHARE.csv",     "UK"),  # lowest confidence, see docstring
}


def fetch_index(name: str, start: str, end: str | None, verbose: bool = True) -> pd.DataFrame:
    """Fetch one index via yfinance and reshape to date, open, high, low, close, volume.
    With verbose (default), prints what is being requested before the blocking call and
    how long it took / how many rows came back after -- see module docstring."""
    import yfinance as yf  # imported lazily -- not installed in the Cowork sandbox

    ticker, _, _ = INDICES[name]
    if verbose:
        print(f"[{name}] dang goi yf.Ticker('{ticker}').history(start={start}, end={end}) ...", flush=True)
    t0 = time.time()
    hist = yf.Ticker(ticker).history(start=start, end=end, auto_adjust=False)
    if verbose:
        print(f"[{name}] phan hoi sau {time.time() - t0:.1f}s, {len(hist)} dong tho", flush=True)
    if hist.empty:
        raise ValueError(
            f"[{name}] yfinance returned 0 rows for ticker {ticker!r} -- check the "
            "ticker symbol is still correct (see docstring confidence notes) before "
            "assuming this is a transient network issue."
        )
    out = hist.reset_index()[["Date", "Open", "High", "Low", "Close", "Volume"]]
    out.columns = ["date", "open", "high", "low", "close", "volume"]
    out["date"] = pd.to_datetime(out["date"]).dt.tz_localize(None)
    return out.sort_values("date").reset_index(drop=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", default=str(DEFAULT_RAW_DIR))
    parser.add_argument("--start", default="2014-01-01")
    parser.add_argument("--end", default="2024-12-31")
    parser.add_argument("--index", default=None, help="fetch only this index name (see INDICES keys)")
    parser.add_argument("--verify-only", action="store_true", help="list tickers, fetch nothing")
    parser.add_argument("--raw-dump", action="store_true", help="print first 5 raw yfinance rows for one index, no reshaping")
    parser.add_argument("--append", action="store_true", help="write CSVs to --out-dir (default: print only)")
    parser.add_argument("--quiet", action="store_true", help="suppress progress reporting (e.g. for cron-style runs)")
    args = parser.parse_args()

    names = [args.index] if args.index else list(INDICES)
    verbose = not args.quiet

    if args.verify_only:
        for name in names:
            ticker, filename, block = INDICES[name]
            print(f"[{block}] {name:16s} ticker={ticker:8s} -> {filename}")
        return

    if args.raw_dump:
        import yfinance as yf

        name = args.index or "FTAS"
        ticker = INDICES[name][0]
        hist = yf.Ticker(ticker).history(start=args.start, end=args.end, auto_adjust=False)
        print(f"[{name}] raw yfinance columns: {list(hist.columns)}")
        print(hist.head().to_string())
        return

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if verbose:
        print(f"=== fetch_equity_wip: {len(names)} index(es), {args.start}..{args.end} ===")

    run_t0 = time.time()
    steps = []
    for i, name in enumerate(names, start=1):
        ticker, filename, block = INDICES[name]
        if verbose:
            print(f"--- [{i}/{len(names)}] [{block}] {name} ---")
        step_t0 = time.time()
        try:
            df = fetch_index(name, args.start, args.end, verbose=verbose)
        except Exception as exc:  # noqa: BLE001 -- record and continue with other indices
            elapsed = time.time() - step_t0
            print(f"[{block}] {name} FAILED sau {elapsed:.1f}s -- {exc}")
            steps.append({"index": name, "ticker": ticker, "ok": False, "error": str(exc), "elapsed_seconds": round(elapsed, 1)})
            continue

        elapsed = time.time() - step_t0
        if args.append:
            out_path = out_dir / filename
            df.to_csv(out_path, index=False)
            print(f"[{block}] {name} -> {out_path} ({len(df)} rows, {elapsed:.1f}s)")
        else:
            print(f"[{block}] {name} ({ticker}): {len(df)} rows, not saved (pass --append to write) ({elapsed:.1f}s)")
        steps.append({"index": name, "ticker": ticker, "ok": True, "rows": len(df), "elapsed_seconds": round(elapsed, 1)})

    total_elapsed = time.time() - run_t0
    if verbose:
        ok = sum(1 for s in steps if s.get("ok"))
        print(f"=== Hoan tat: {ok}/{len(names)} index thanh cong, tong {total_elapsed:.1f}s ===")

    append_run_log(make_run_record(
        pipeline="equity",
        mode="append" if args.append else "dry-run",
        steps=steps,
        start_arg=args.start,
        end_arg=args.end,
        total_elapsed_seconds=round(total_elapsed, 1),
    ))


if __name__ == "__main__":
    main()
