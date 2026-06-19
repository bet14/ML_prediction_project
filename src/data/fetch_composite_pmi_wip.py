"""
WIP / STUB -- Composite PMI (Purchasing Managers' Index), USA + UK. No working fetch
logic yet -- this file records the source investigation and gives a scaffold to fill in
once a concrete source is chosen, instead of mixing speculative code into the
production fetch_*.py family (see fred_common.py docstring: Composite PMI is
intentionally absent from that family).

Why this is hard
-----------------
Composite PMI (manufacturing + services blend, published by S&P Global / CIPS) is
proprietary and is not on FRED. This is a DIFFERENT, broader index than ISM
Manufacturing PMI (manufacturing only, USA only, published by the Institute for Supply
Management): ISM Manufacturing PMI *was* on FRED -- series NAPM and the rest of the
"ISM Report on Business" family (NAPMPI, NAPMEI, NAPMNOI, NAPMSDI, NAPMII, NAPMPRI -- 22
series total) -- until ISM had the entire family removed from FRED in June 2016 at its
own request. No free replacement API has been found since, for either ISM
Manufacturing PMI or S&P Global Composite PMI, on either side of the Atlantic.

Only documented option so far: investing.com's PMI history pages, exported by hand
(search "United States Composite PMI" / "United Kingdom Composite PMI" on
investing.com), or scraped. Neither has been implemented or tested here --
fetch_composite_pmi() below raises NotImplementedError on purpose, so this file fails
loudly instead of silently producing nothing.

Output convention (once implemented)
-------------------------------------
data/raw/macro/USA_composite_pmi.csv, data/raw/macro/UK_composite_pmi.csv -- same
columns as the rest of the pipeline: date, realtime_start, value. investing.com PMI
prints are single-vintage (no ALFRED-style revision history), so realtime_start can
reasonably just equal date unless a real publication-lag figure is found.

Manual fallback (works today, no code needed)
-----------------------------------------------
1. Export the PMI history CSV from investing.com for each country by hand.
2. Reshape it to columns date, realtime_start, value (realtime_start = date is fine).
3. Save as data/raw/macro/USA_composite_pmi.csv / UK_composite_pmi.csv.
4. Run src/features/process_composite_pmi.py -- it picks up whichever of the two files
   exist, the same way process_current_account.py already does for UK.

Usage
-----
    python fetch_composite_pmi_wip.py --verify-only   # prints status below, does nothing else
    python fetch_composite_pmi_wip.py                 # raises NotImplementedError on purpose
"""

import argparse

SOURCES = {
    "USA": "not implemented -- candidate: investing.com 'United States Composite PMI'",
    "UK": "not implemented -- candidate: investing.com 'United Kingdom Composite PMI'",
}


def fetch_composite_pmi(block: str) -> None:
    raise NotImplementedError(
        f"[{block}] No working fetch path for Composite PMI yet. Candidate: "
        f"{SOURCES[block]}. See module docstring for the manual-export fallback that "
        "works today without writing scraper code."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()

    print("Composite PMI fetch status:")
    for block, candidate in SOURCES.items():
        print(f"  [{block}] {candidate}")

    if args.verify_only:
        return

    for block in SOURCES:
        fetch_composite_pmi(block)  # raises NotImplementedError -- see module docstring


if __name__ == "__main__":
    main()
