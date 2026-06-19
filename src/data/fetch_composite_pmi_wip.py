"""
WIP -- Composite PMI (Purchasing Managers' Index), USA + UK, scraped from investing.com.

Why this is hard
-----------------
Composite PMI (manufacturing + services blend, published by S&P Global / CIPS) is
proprietary and is not on FRED. This is a DIFFERENT, broader index than ISM
Manufacturing PMI (manufacturing only, USA only, published by the Institute for Supply
Management): ISM Manufacturing PMI *was* on FRED -- series NAPM and the rest of the
"ISM Report on Business" family (NAPMPI, NAPMEI, NAPMNOI, NAPMSDI, NAPMII, NAPMPRI -- 22
series total) -- until ISM had the entire family removed from FRED in June 2016 at its
own request. No free historical-data API has been found since, for either ISM
Manufacturing PMI or S&P Global Composite PMI, on either side of the Atlantic.

STATUS as of 2026-06-19: a real scraper is implemented below (fetch_recent_releases()),
not a stub -- it was tested against the live HTML of both target pages and confirmed
working. BUT a hard limitation was discovered in the process that changes what this
script can actually be used for:

    investing.com's economic-calendar event pages
    (https://www.investing.com/economic-calendar/s-p-global-composite-pmi-1492 for USA,
    https://www.investing.com/economic-calendar/composite-pmi-1934 for UK) only render
    the **last ~3-4 releases** (a couple of past prints plus the next 1-2 scheduled
    dates) in the server-rendered "Release date / Time / Actual / Forecast / Previous"
    table -- there is no full back-history on this page, by design, not by anti-bot
    blocking. This was independently confirmed twice:
      1. Live fetch of both pages on 2026-06-19 returned exactly 3-4 rows each.
      2. A comment thread visible on the USA page itself, from another user, complains
         about exactly this: "is it possible to keep past months inputs up like yall
         used to or at least more than just two updates" -- i.e. investing.com itself
         cut this table down at some point; it is not a scraping artifact.
    No CSV/historical-data export control was found on this page type either (unlike
    investing.com's per-instrument "historical-data" pages for stocks/indices/FX, which
    do have a real multi-year table -- PMI is an "economic calendar event", a different
    page template, and does not get that treatment).

    Net effect: this scraper CANNOT backfill 2014-2024 history. It is only useful to
    keep a PMI file fresh GOING FORWARD, one release at a time, once a historical base
    has been established some other way (see "Manual fallback" below). Treat it as an
    incremental updater, not a backfill tool -- this is exactly why it stays a WIP
    script and is not wired into run_fred_pipeline.py.

Implementation notes
---------------------
- Built with `requests` + `BeautifulSoup` (added to requirements.txt: beautifulsoup4).
  Needs network -- run on a personal machine, not in the Cowork sandbox.
- The parser locates the data table by its header text ("Release date", "Actual", ...)
  rather than by CSS class/id, since investing.com's class names churn across redesigns
  but the user-facing header labels are far more stable -- a deliberate robustness
  choice given this project can't re-verify the page structure on every run.
- Row date label looks like "Jun 03, 2026 (May)": the date before the parenthesis is
  the publication/release date (-> realtime_start); the month abbreviation inside the
  parenthesis is the month the *value* actually describes (-> date, the observation
  period). Year for the parenthesised month is inferred from the release date, rolling
  back one year for a Dec-release-in-January edge case.
- Rows with no "Actual" value yet (future scheduled releases) are dropped.
- investing.com does not publish an ALFRED-style revision history for this page type,
  so there is exactly one (date, realtime_start, value) row per monthly release, same
  approximation already used in fetch_current_account_uk_wip.py.
- Anti-bot risk is real (investing.com is Cloudflare-protected) even though this
  specific page type happened to return plain server-rendered HTML on every attempt
  made during this investigation with a normal browser-like User-Agent and no other
  special headers. If a future run gets blocked (HTTP 403, a CAPTCHA page, or an empty
  table where rows are expected), fall back to the manual export below rather than
  trying to defeat the block -- that is a deliberate scope boundary for this project,
  not a missing feature.

Manual fallback (only known way to get full 2014-2024 history today)
-----------------------------------------------------------------------
1. Find a source with real multi-year Composite PMI history (investing.com's own
   per-event page does not have one -- see STATUS above). Candidates not yet checked:
   a paid S&P Global Market Intelligence subscription (authoritative but not free), or
   manually transcribing the monthly print from S&P Global's own press releases
   (pmi.spglobal.com) one month at a time, which is slow but free and authoritative.
2. Reshape whatever is collected to columns date, realtime_start, value
   (realtime_start = date is fine for a single-vintage source).
3. Save as data/raw/macro/USA_composite_pmi.csv / UK_composite_pmi.csv.
4. From then on, fetch_recent_releases() in this script can append each new monthly
   release as it comes out, instead of re-doing step 1 by hand every month.

Usage
-----
    python fetch_composite_pmi_wip.py --verify-only   # print page status, parse nothing
    python fetch_composite_pmi_wip.py                 # print parsed recent releases
    python fetch_composite_pmi_wip.py --append         # merge into the raw CSV (dedup on date)
"""

import argparse
import re
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RAW_DIR = PROJECT_ROOT / "data" / "raw" / "macro"

SOURCES = {
    "USA": "https://www.investing.com/economic-calendar/s-p-global-composite-pmi-1492",
    "UK": "https://www.investing.com/economic-calendar/composite-pmi-1934",
}

HEADERS = {
    # A plain desktop-browser User-Agent -- no other special headers were needed against
    # this specific page type as of 2026-06-19. See module docstring re: anti-bot risk.
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}

_MONTH_NUM = {
    m: i + 1
    for i, m in enumerate(
        ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    )
}

_ROW_DATE_RE = re.compile(
    r"(?P<rel_mon>[A-Za-z]{3})\s+(?P<rel_day>\d{1,2}),\s*(?P<rel_year>\d{4})\s*"
    r"\((?P<obs_mon>[A-Za-z]{3})\)"
)


def _parse_row_date(label: str):
    """'Jun 03, 2026 (May)' -> (release_date, observation_period_start). Returns
    (None, None) if the label doesn't match the expected shape."""
    m = _ROW_DATE_RE.search(label)
    if not m:
        return None, None
    rel_mon, rel_day, rel_year = m["rel_mon"], int(m["rel_day"]), int(m["rel_year"])
    obs_mon = m["obs_mon"]
    if rel_mon not in _MONTH_NUM or obs_mon not in _MONTH_NUM:
        return None, None
    release_date = datetime(rel_year, _MONTH_NUM[rel_mon], rel_day)
    obs_year = rel_year
    # December release-month data published in January belongs to the prior year.
    if _MONTH_NUM[obs_mon] == 12 and _MONTH_NUM[rel_mon] == 1:
        obs_year -= 1
    observation_start = datetime(obs_year, _MONTH_NUM[obs_mon], 1)
    return release_date, observation_start


def fetch_recent_releases(block: str) -> pd.DataFrame:
    """Scrape the last ~3-4 releases visible on investing.com's economic-calendar page
    for `block` ('USA' or 'UK'). Returns columns date, realtime_start, value -- see
    module docstring for why this cannot backfill full history."""
    if block not in SOURCES:
        raise ValueError(f"Unknown block {block!r}; expected one of {list(SOURCES)}")

    resp = requests.get(SOURCES[block], headers=HEADERS, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    target_table = None
    for table in soup.find_all("table"):
        header_text = " ".join(th.get_text(strip=True) for th in table.find_all("th"))
        if "Release date" in header_text and "Actual" in header_text:
            target_table = table
            break
    if target_table is None:
        raise ValueError(
            f"[{block}] Could not find the release-history table on {SOURCES[block]} -- "
            "the page structure may have changed, or the request may have been blocked "
            "(check for a CAPTCHA/HTTP 403). Fall back to the manual workflow in the "
            "module docstring rather than patching this selector blindly."
        )

    rows = []
    for tr in target_table.find_all("tr"):
        cells = [td.get_text(strip=True) for td in tr.find_all("td")]
        if len(cells) < 3:
            continue  # header row or malformed row
        release_date, observation_start = _parse_row_date(cells[0])
        if release_date is None:
            continue
        actual_str = cells[2]
        if not actual_str:
            continue  # future scheduled release, no value yet
        try:
            value = float(actual_str)
        except ValueError:
            continue
        rows.append(
            {"date": observation_start, "realtime_start": release_date, "value": value}
        )

    if not rows:
        raise ValueError(
            f"[{block}] Found the table on {SOURCES[block]} but parsed zero usable rows "
            "-- inspect the page manually; the row shape may have changed."
        )
    return pd.DataFrame(rows).sort_values("date").reset_index(drop=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", default=str(DEFAULT_RAW_DIR))
    parser.add_argument(
        "--verify-only", action="store_true",
        help="just print the target URLs and an HTTP status check, parse nothing",
    )
    parser.add_argument(
        "--append", action="store_true",
        help="merge newly scraped rows into data/raw/macro/<BLOCK>_composite_pmi.csv, "
             "deduplicated on date (keeps the new row on conflict)",
    )
    args = parser.parse_args()

    if args.verify_only:
        for block, url in SOURCES.items():
            try:
                resp = requests.get(url, headers=HEADERS, timeout=15)
                print(f"[{block}] {url} -> HTTP {resp.status_code}")
            except requests.RequestException as exc:
                print(f"[{block}] {url} -> request failed: {exc}")
        return

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    for block in SOURCES:
        try:
            new_rows = fetch_recent_releases(block)
        except (ValueError, requests.RequestException) as exc:
            print(f"[{block}] FAILED -- {exc}")
            continue

        out_path = out_dir / f"{block}_composite_pmi.csv"
        if args.append and out_path.exists():
            existing = pd.read_csv(out_path, parse_dates=["date", "realtime_start"])
            combined = (
                pd.concat([existing, new_rows])
                .drop_duplicates(subset="date", keep="last")
                .sort_values("date")
                .reset_index(drop=True)
            )
            combined.to_csv(out_path, index=False)
            print(f"[{block}] merged {len(new_rows)} scraped rows -> {out_path} ({len(combined)} total rows)")
        elif args.append:
            new_rows.to_csv(out_path, index=False)
            print(f"[{block}] no existing file -- wrote {len(new_rows)} rows -> {out_path} (NOT a full history, see docstring)")
        else:
            print(f"[{block}] parsed {len(new_rows)} recent release(s), not saved (pass --append to write):")
            print(new_rows.to_string(index=False))


if __name__ == "__main__":
    main()
