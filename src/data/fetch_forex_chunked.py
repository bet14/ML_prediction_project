"""
fetch_forex_chunked.py -- Resumable chunked forex OHLCV downloader.

Vấn đề của fetch_forex_wip.py: một run duy nhất cho toàn bộ 13 pairs × 11 năm
→ dukascopy cần ~800k–900k requests → nhiều giờ → bị interrupt là mất hết tiến độ.

Giải pháp: chia thành (pair × year) chunks, mỗi chunk độc lập:
  - Chunk file:   data/raw/forex_chunks/{PAIR}/{PAIR}_{YEAR}_{source}.csv
  - Manifest:     data/raw/forex_chunks/manifest.jsonl  (append-only, 1 dòng/attempt)
  - Final merge:  data/raw/forex/{filename}.csv  (dùng --merge sau khi tất cả chunk xong)

Tổng chunk: 13 pairs × 11 năm = 143 chunks
Chạy lại an toàn: chunk đã "ok" + file tồn tại → tự động skip.

Usage
-----
    # Xem trạng thái tất cả chunk (dukascopy)
    python fetch_forex_chunked.py --status

    # Xem trạng thái cho yfinance
    python fetch_forex_chunked.py --status --source yfinance

    # Download 1 pair toàn bộ 11 năm (skip chunk đã xong)
    python fetch_forex_chunked.py --pair GBPUSD --source dukascopy --append

    # Download tất cả pairs cho năm 2024
    python fetch_forex_chunked.py --year 2024 --source dukascopy --append

    # Download 1 chunk cụ thể (pair + year)
    python fetch_forex_chunked.py --pair GBPUSD --year 2020 --source dukascopy --append

    # Download tất cả 143 chunks (skip đã xong), nguồn yfinance
    python fetch_forex_chunked.py --source yfinance --append

    # Chỉ retry chunk bị lỗi (bỏ qua chunk chưa chạy)
    python fetch_forex_chunked.py --retry-failed --source dukascopy --append

    # Gộp tất cả chunk đã ok thành file cuối cùng vào data/raw/forex/
    python fetch_forex_chunked.py --merge --source dukascopy

    # Dry-run: xem sẽ download gì mà không thực sự fetch
    python fetch_forex_chunked.py --pair GBPUSD --source dukascopy
"""

import argparse
import json
import lzma
import struct
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pipeline_log_common import append_run_log  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CHUNK_DIR = PROJECT_ROOT / "data" / "raw" / "forex_chunks"
FINAL_DIR = PROJECT_ROOT / "data" / "raw" / "forex"
MANIFEST_PATH = CHUNK_DIR / "manifest.jsonl"

YEARS = list(range(2014, 2025))  # 2014..2024 inclusive (end_dt = year+1 để exclusive)

# name -> (dukascopy_symbol, yfinance_ticker, final_csv_filename, point_value)
PAIRS = {
    "AUDUSD": ("AUDUSD", "AUDUSD=X", "AUD_USD.csv",  100_000),
    "EURUSD": ("EURUSD", "EURUSD=X", "EUR_USD.csv",  100_000),
    "EURGBP": ("EURGBP", "EURGBP=X", "EUR_GBP.csv",  100_000),
    "GBPAUD": ("GBPAUD", "GBPAUD=X", "GBP_AUD.csv",  100_000),
    "GBPCAD": ("GBPCAD", "GBPCAD=X", "GBP_CAD.csv",  100_000),
    "GBPCHF": ("GBPCHF", "GBPCHF=X", "GBP_CHF.csv",  100_000),
    "GBPJPY": ("GBPJPY", "GBPJPY=X", "GBP_JPY.csv",    1_000),
    "GBPNZD": ("GBPNZD", "GBPNZD=X", "GBP_NZD.csv",  100_000),
    "GBPUSD": ("GBPUSD", "GBPUSD=X", "GBP_USD.csv",  100_000),  # target pair
    "NZDUSD": ("NZDUSD", "NZDUSD=X", "NZD_USD.csv",  100_000),
    "USDCAD": ("USDCAD", "USDCAD=X", "USD_CAD.csv",  100_000),
    "USDCHF": ("USDCHF", "USDCHF=X", "USD_CHF.csv",  100_000),
    "USDJPY": ("USDJPY", "USDJPY=X", "USD_JPY.csv",    1_000),
}

DUKASCOPY_URL = (
    "https://datafeed.dukascopy.com/datafeed/"
    "{symbol}/{y:04d}/{m:02d}/{d:02d}/{h:02d}h_ticks.bi5"
)
_TICK_STRUCT = struct.Struct(">IIIff")  # time_delta_ms, ask_raw, bid_raw, ask_vol, bid_vol


# ---------------------------------------------------------------------------
# Dukascopy helpers (identical logic to fetch_forex_wip.py)
# ---------------------------------------------------------------------------

def _dukascopy_url(symbol: str, hour_start: datetime) -> str:
    """Month is 0-indexed in Dukascopy URLs (Jan = 00)."""
    return DUKASCOPY_URL.format(
        symbol=symbol, y=hour_start.year, m=hour_start.month - 1,
        d=hour_start.day, h=hour_start.hour,
    )


def _decode_bi5(raw_bytes: bytes, point_value: int, hour_start: datetime) -> list[dict]:
    """Decompress one hourly .bi5 file → list of tick dicts. Returns [] for empty hours."""
    if not raw_bytes:
        return []
    try:
        decompressed = lzma.decompress(raw_bytes)
    except lzma.LZMAError:
        return []
    n = len(decompressed) // _TICK_STRUCT.size
    ticks = []
    for i in range(n):
        chunk = decompressed[i * _TICK_STRUCT.size:(i + 1) * _TICK_STRUCT.size]
        delta_ms, ask_raw, bid_raw, ask_vol, bid_vol = _TICK_STRUCT.unpack(chunk)
        ticks.append({
            "time":     hour_start + timedelta(milliseconds=delta_ms),
            "ask":      ask_raw / point_value,
            "bid":      bid_raw / point_value,
            "ask_vol":  ask_vol,
            "bid_vol":  bid_vol,
        })
    return ticks


# ---------------------------------------------------------------------------
# Manifest helpers
# ---------------------------------------------------------------------------

def load_manifest() -> dict:
    """Load manifest.jsonl → {(pair, year, source): last_record}.
    Dùng record CUỐI cho mỗi key để retry ghi đè attempt trước."""
    if not MANIFEST_PATH.exists():
        return {}
    result: dict = {}
    with MANIFEST_PATH.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                key = (rec["pair"], rec["year"], rec["source"])
                result[key] = rec
            except (json.JSONDecodeError, KeyError):
                pass
    return result


def write_manifest_entry(entry: dict) -> None:
    """Append one attempt record to manifest.jsonl."""
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with MANIFEST_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _chunk_is_done(pair: str, year: int, source: str, manifest: dict) -> bool:
    """True nếu chunk đã ok VÀ file vẫn còn tồn tại trên disk."""
    rec = manifest.get((pair, year, source))
    if not rec or rec.get("status") != "ok":
        return False
    f = rec.get("file", "")
    return bool(f) and Path(f).exists()


# ---------------------------------------------------------------------------
# Download: Dukascopy – 1 chunk = 1 pair × 1 year
# ---------------------------------------------------------------------------

def fetch_chunk_dukascopy(pair: str, year: int, verbose: bool = True) -> tuple[pd.DataFrame, int, int]:
    """Download (pair, year) từ Dukascopy. Trả về (DataFrame, n_ticks, n_failed_requests)."""
    import requests

    symbol, _, _, point_value = PAIRS[pair]
    start_dt = datetime(year, 1, 1, tzinfo=timezone.utc)
    end_dt   = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    total_hours = int((end_dt - start_dt).total_seconds() // 3600)
    is_tty = sys.stdout.isatty()
    print_every = 1 if is_tty else 24  # interactive: mỗi giờ; redirect: ~1 lần/ngày

    daily_ticks: dict = {}  # date -> {prices: [], vol: float}
    hour = start_dt
    n = n_ticks = n_failed = 0
    t0 = time.time()

    while hour < end_dt:
        n += 1
        if verbose and (n % print_every == 0 or hour + timedelta(hours=1) >= end_dt):
            elapsed = time.time() - t0
            pct = n / total_hours * 100
            eta_s = (elapsed / n) * (total_hours - n)
            line = (
                f"[{pair}][{year}] dukascopy: {hour:%Y-%m-%d %Hh}Z "
                f"({n}/{total_hours}, {pct:4.1f}%) ticks={n_ticks} loi={n_failed} "
                f"elapsed={elapsed/60:.1f}p ETA={eta_s/60:.1f}p"
            )
            if is_tty:
                sys.stdout.write("\r" + line + "    ")
            else:
                print(line)
            sys.stdout.flush()

        url = _dukascopy_url(symbol, hour)
        try:
            resp = requests.get(url, timeout=30)
            if resp.status_code == 200:
                for t in _decode_bi5(resp.content, point_value, hour):
                    day = t["time"].date()
                    mid = (t["ask"] + t["bid"]) / 2
                    vol = t["ask_vol"] + t["bid_vol"]
                    bucket = daily_ticks.setdefault(day, {"prices": [], "vol": 0.0})
                    bucket["prices"].append(mid)
                    bucket["vol"] += vol
                    n_ticks += 1
        except Exception as exc:  # noqa: BLE001 -- log and continue
            n_failed += 1
            if verbose:
                print(f"\n[{pair}][{year}] WARN: loi tai {hour:%Y-%m-%d %Hh}Z: {exc}")

        hour += timedelta(hours=1)

    if verbose and is_tty:
        print()  # xuống dòng sau progress line

    if not daily_ticks:
        raise ValueError(
            f"[{pair}][{year}] dukascopy: 0 ticks decoded -- "
            "kiem tra ket noi mang hoac symbol"
        )

    rows = []
    for day, b in sorted(daily_ticks.items()):
        p = b["prices"]
        rows.append({
            "date":   day,
            "open":   p[0],
            "high":   max(p),
            "low":    min(p),
            "close":  p[-1],
            "volume": b["vol"],
        })
    return pd.DataFrame(rows), n_ticks, n_failed


# ---------------------------------------------------------------------------
# Download: yfinance – 1 chunk = 1 pair × 1 year
# ---------------------------------------------------------------------------

def fetch_chunk_yfinance(pair: str, year: int, verbose: bool = True) -> tuple[pd.DataFrame, int]:
    """Download (pair, year) từ yfinance. Một API call duy nhất.
    Volume có thể không đáng tin cho FX -- xem fetch_forex_wip.py docstring."""
    import yfinance as yf

    _, ticker, _, _ = PAIRS[pair]
    start = f"{year}-01-01"
    end   = f"{year + 1}-01-01"
    if verbose:
        print(f"[{pair}][{year}] yfinance: goi Ticker('{ticker}').history({start}..{end}) ...", flush=True)
    t0 = time.time()
    hist = yf.Ticker(ticker).history(start=start, end=end, auto_adjust=False)
    elapsed = time.time() - t0
    if verbose:
        print(f"[{pair}][{year}] yfinance: {len(hist)} rows sau {elapsed:.1f}s", flush=True)
    if hist.empty:
        raise ValueError(f"[{pair}][{year}] yfinance returned 0 rows cho ticker '{ticker}'")
    out = hist.reset_index()[["Date", "Open", "High", "Low", "Close", "Volume"]]
    out.columns = ["date", "open", "high", "low", "close", "volume"]
    out["date"] = pd.to_datetime(out["date"]).dt.tz_localize(None)
    return out.sort_values("date").reset_index(drop=True), len(out)


# ---------------------------------------------------------------------------
# Process one chunk: check manifest → download → save → log
# ---------------------------------------------------------------------------

def process_chunk(
    pair: str, year: int, source: str,
    manifest: dict, do_save: bool, verbose: bool,
) -> str:
    """Returns: 'skipped' | 'dry-run' | 'ok' | 'error'"""
    if _chunk_is_done(pair, year, source, manifest):
        rec = manifest[(pair, year, source)]
        if verbose:
            rows = rec.get("rows", "?")
            elapsed = rec.get("elapsed_s", "?")
            fname = Path(rec.get("file", "")).name
            print(f"[{pair}][{year}][{source}] SKIP: da co ({rows} rows, {elapsed}s) -- {fname}")
        return "skipped"

    if not do_save:
        prev = manifest.get((pair, year, source))
        status_note = f" (prev: {prev['status']})" if prev else " (chua chay)"
        print(f"[{pair}][{year}][{source}] WOULD download{status_note} (them --append de thuc hien)")
        return "dry-run"

    # --- Thực sự download ---
    chunk_subdir = CHUNK_DIR / pair
    chunk_subdir.mkdir(parents=True, exist_ok=True)
    out_file = chunk_subdir / f"{pair}_{year}_{source}.csv"

    started_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    t0 = time.time()

    try:
        if source == "dukascopy":
            df, n_ticks, n_failed = fetch_chunk_dukascopy(pair, year, verbose=verbose)
            extra = {"n_ticks": n_ticks, "n_failed_requests": n_failed}
        else:
            df, _ = fetch_chunk_yfinance(pair, year, verbose=verbose)
            extra = {}
    except Exception as exc:  # noqa: BLE001
        elapsed = round(time.time() - t0, 1)
        entry = {
            "pair": pair, "year": year, "source": source,
            "status": "error",
            "error": str(exc),
            "started_at": started_at,
            "finished_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "elapsed_s": elapsed,
        }
        write_manifest_entry(entry)
        manifest[(pair, year, source)] = entry
        print(f"[{pair}][{year}][{source}] ERROR sau {elapsed:.0f}s: {exc}")
        return "error"

    elapsed = round(time.time() - t0, 1)
    df.to_csv(out_file, index=False)

    entry: dict = {
        "pair": pair, "year": year, "source": source,
        "status": "ok",
        "rows": len(df),
        "started_at": started_at,
        "finished_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "elapsed_s": elapsed,
        "file": str(out_file),
    }
    entry.update(extra)
    write_manifest_entry(entry)
    manifest[(pair, year, source)] = entry
    print(f"[{pair}][{year}][{source}] OK: {len(df)} rows, {elapsed:.0f}s -> {out_file.name}")
    return "ok"


# ---------------------------------------------------------------------------
# Status grid
# ---------------------------------------------------------------------------

def show_status(source: str) -> None:
    """In grid: pair × year với ok/ERR/---- per cell."""
    manifest = load_manifest()
    year_header = "  ".join(f"{y}" for y in YEARS)
    sep = "-" * (12 + len(YEARS) * 7 + 14)

    print(f"\n=== Chunk status: {source} ===")
    print(f"{'PAIR':12}  {year_header}   DONE/TOT")
    print(sep)

    total_ok = total_err = total_pending = 0
    for pair in PAIRS:
        cells = []
        done = 0
        for year in YEARS:
            rec = manifest.get((pair, year, source))
            if rec is None:
                cells.append("----")
                total_pending += 1
            elif rec.get("status") == "ok":
                f = rec.get("file", "")
                cells.append("ok  " if (f and Path(f).exists()) else "ok? ")
                done += 1
                total_ok += 1
            else:
                cells.append("ERR ")
                total_err += 1
        row = "  ".join(cells)
        print(f"{pair:12}  {row}   {done}/{len(YEARS)}")

    print(sep)
    total = len(PAIRS) * len(YEARS)
    print(f"Tong: {total_ok} ok, {total_err} loi, {total_pending} chua chay / {total} chunks")
    print(f"Manifest: {MANIFEST_PATH}")

    # chi tiet loi
    errors = [
        rec for rec in manifest.values()
        if rec.get("source") == source and rec.get("status") == "error"
    ]
    if errors:
        print(f"\nChunk bi loi ({len(errors)}):")
        for rec in errors:
            print(f"  {rec['pair']:8} {rec['year']}  {rec.get('elapsed_s','?')}s  {rec.get('error','')[:80]}")


# ---------------------------------------------------------------------------
# Merge chunks → final per-pair CSV
# ---------------------------------------------------------------------------

def merge_chunks(pairs: list, source: str, verbose: bool = True) -> None:
    """Gộp tất cả chunk CSV thành file cuối cùng vào data/raw/forex/."""
    manifest = load_manifest()
    FINAL_DIR.mkdir(parents=True, exist_ok=True)

    for pair in pairs:
        _, _, final_filename, _ = PAIRS[pair]
        yearly_files = []
        missing_years = []

        for year in YEARS:
            if _chunk_is_done(pair, year, source, manifest):
                yearly_files.append(Path(manifest[(pair, year, source)]["file"]))
            else:
                missing_years.append(year)

        if missing_years and verbose:
            print(f"[{pair}] WARN: thieu {len(missing_years)} chunk: {missing_years}")
        if not yearly_files:
            print(f"[{pair}] SKIP: chua co chunk nao de merge")
            continue

        dfs = [pd.read_csv(f, parse_dates=["date"]) for f in sorted(yearly_files)]
        merged = (
            pd.concat(dfs, ignore_index=True)
            .drop_duplicates(subset=["date"])
            .sort_values("date")
            .reset_index(drop=True)
        )
        out_path = FINAL_DIR / final_filename
        merged.to_csv(out_path, index=False)
        if verbose:
            print(
                f"[{pair}] merge: {len(yearly_files)}/{len(YEARS)} nam, "
                f"{len(merged)} rows -> {out_path.name}"
            )


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--pair",   default=None, choices=list(PAIRS),
                        help="chi download pair nay (default: tat ca 13 pairs)")
    parser.add_argument("--year",   default=None, type=int, choices=YEARS,
                        help="chi download nam nay (default: tat ca 2014-2024)")
    parser.add_argument("--source", default="dukascopy", choices=["dukascopy", "yfinance"],
                        help="nguon du lieu (default: dukascopy)")
    parser.add_argument("--append", action="store_true",
                        help="ghi CSV ra disk; khong co flag nay = dry-run")
    parser.add_argument("--status", action="store_true",
                        help="hien thi grid trang thai chunk, roi thoat")
    parser.add_argument("--retry-failed", action="store_true",
                        help="chi retry chunk co status=error (bo qua chua chay va da ok)")
    parser.add_argument("--merge",  action="store_true",
                        help="gop chunk da ok thanh file cuoi vao data/raw/forex/")
    parser.add_argument("--quiet",  action="store_true",
                        help="tat progress output")
    args = parser.parse_args()
    verbose = not args.quiet

    # --- --status ---
    if args.status:
        show_status(args.source)
        return

    pairs = [args.pair] if args.pair else list(PAIRS)
    years = [args.year] if args.year else YEARS

    # --- --merge ---
    if args.merge:
        print(f"=== Merging {args.source} chunks -> {FINAL_DIR} ===")
        merge_chunks(pairs, args.source, verbose=verbose)
        return

    manifest = load_manifest()

    # Xác định danh sách chunk cần xử lý
    if args.retry_failed:
        work = [
            (p, y) for p in pairs for y in years
            if manifest.get((p, y, args.source), {}).get("status") == "error"
        ]
        if not work:
            print("Khong co chunk nao bi loi. Dung --status de xem trang thai.")
            return
        print(f"=== Retry {len(work)} chunk loi ({args.source}) ===")
    else:
        work = [(p, y) for p in pairs for y in years]
        n_done = sum(1 for p, y in work if _chunk_is_done(p, y, args.source, manifest))
        print(
            f"=== fetch_forex_chunked: {len(work)} chunks, source={args.source}, "
            f"{n_done} da xong (se skip), {len(work) - n_done} con lai ==="
        )
        if not args.append:
            print("(dry-run -- them --append de thuc su download va ghi file)")

    run_t0 = time.time()
    counts = {"ok": 0, "error": 0, "skipped": 0, "dry-run": 0}

    for i, (pair, year) in enumerate(work, 1):
        if verbose:
            print(f"\n--- [{i}/{len(work)}] {pair} {year} ({args.source}) ---")
        result = process_chunk(pair, year, args.source, manifest, args.append, verbose)
        counts[result] = counts.get(result, 0) + 1

    total_elapsed = time.time() - run_t0
    print(
        f"\n=== Hoan tat: {counts['ok']} ok, {counts['error']} loi, "
        f"{counts['skipped']} skip, {counts.get('dry-run',0)} dry-run "
        f"-- tong {total_elapsed / 60:.1f} phut ==="
    )
    if counts["error"]:
        print(
            f"  Retry loi:  python fetch_forex_chunked.py "
            f"--retry-failed --source {args.source} --append"
        )
    if counts["ok"] and args.append:
        print(
            f"  Gop file:   python fetch_forex_chunked.py "
            f"--merge --source {args.source}"
        )

    append_run_log({
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "pipeline": "forex_chunked",
        "source": args.source,
        "mode": "append" if args.append else "dry-run",
        "pairs": pairs,
        "years": years,
        "counts": counts,
        "total_elapsed_s": round(total_elapsed, 1),
    })


if __name__ == "__main__":
    main()
