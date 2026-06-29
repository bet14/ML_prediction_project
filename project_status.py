"""
project_status.py -- Scan project filesystem and generate a progress dashboard.

Reads filesystem + pipeline_run_log.jsonl. No network required.
Outputs reports/project_status.html and prints a console summary.

Usage:
    python project_status.py            # generate HTML + print console
    python project_status.py --no-html  # console only
"""

import json
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
REPORT_PATH  = PROJECT_ROOT / "reports" / "project_status.html"
RUN_LOG_PATH = PROJECT_ROOT / "reports" / "pipeline_run_log.jsonl"

# ─────────────────────────────────────────────────────────────
# Checklist definition
# path=None + blocked="..."  → no data source exists
# is_dir=True                → check folder has files
# stale="..."                → file has data but is outdated / discontinued
# min_rows                   → minimum rows to be considered complete
# ─────────────────────────────────────────────────────────────
CHECKLIST = [
    # ── Goal 1: Thu thập dữ liệu ──────────────────────────────
    {
        "phase": "Goal 1A — Macro Raw Data",
        "items": [
            {"label": "USA GDP",               "path": "data/raw/macro/USA_gdp.csv",               "min_rows": 40},
            {"label": "USA CPI",               "path": "data/raw/macro/USA_cpi.csv",               "min_rows": 100},
            {"label": "USA Fed Funds Rate",    "path": "data/raw/macro/USA_central_bank_rate.csv", "min_rows": 1000},
            {"label": "USA Current Account",   "path": "data/raw/macro/USA_current_account.csv",   "min_rows": 40},
            {"label": "UK GDP",                "path": "data/raw/macro/UK_gdp.csv",                "min_rows": 20,
             "stale": "FRED series discontinued Jul-2020 — alternative source needed"},
            {"label": "UK CPI",                "path": "data/raw/macro/UK_cpi.csv",                "min_rows": 50,
             "stale": "Stale ~15 months — see UK_cpi_ons_alt.csv as replacement"},
            {"label": "UK CPI (ONS alt)",      "path": "data/raw/macro/UK_cpi_ons_alt.csv",        "min_rows": 100},
            {"label": "UK Current Account",    "path": "data/raw/macro/UK_current_account.csv",    "min_rows": 40},
            {"label": "USA Composite PMI",     "path": None,
             "blocked": "No historical source — investing.com keeps only ~3-4 recent releases"},
            {"label": "UK Composite PMI",      "path": None,
             "blocked": "No historical source — manual collection required"},
        ],
    },
    {
        "phase": "Goal 1B — Forex Raw (13 pairs · yfinance)",
        "items": [
            {"label": "GBP/USD  (target pair)", "path": "data/raw/forex/GBP_USD.csv", "min_rows": 2500},
            {"label": "EUR/USD",                "path": "data/raw/forex/EUR_USD.csv", "min_rows": 2500},
            {"label": "EUR/GBP",                "path": "data/raw/forex/EUR_GBP.csv", "min_rows": 2500},
            {"label": "AUD/USD",                "path": "data/raw/forex/AUD_USD.csv", "min_rows": 2500},
            {"label": "GBP/AUD",                "path": "data/raw/forex/GBP_AUD.csv", "min_rows": 2500},
            {"label": "GBP/CAD",                "path": "data/raw/forex/GBP_CAD.csv", "min_rows": 2500},
            {"label": "GBP/CHF",                "path": "data/raw/forex/GBP_CHF.csv", "min_rows": 2500},
            {"label": "GBP/JPY",                "path": "data/raw/forex/GBP_JPY.csv", "min_rows": 2500},
            {"label": "GBP/NZD",                "path": "data/raw/forex/GBP_NZD.csv", "min_rows": 2500},
            {"label": "NZD/USD",                "path": "data/raw/forex/NZD_USD.csv", "min_rows": 2500},
            {"label": "USD/CAD",                "path": "data/raw/forex/USD_CAD.csv", "min_rows": 2500},
            {"label": "USD/CHF",                "path": "data/raw/forex/USD_CHF.csv", "min_rows": 2500},
            {"label": "USD/JPY",                "path": "data/raw/forex/USD_JPY.csv", "min_rows": 2500},
        ],
    },
    {
        "phase": "Goal 1C — Equity Raw (9 indices · yfinance)",
        "items": [
            {"label": "S&P 500",          "path": "data/raw/equity/USA_SP500.csv",            "min_rows": 2500},
            {"label": "Nasdaq Composite", "path": "data/raw/equity/USA_NASDAQ_COMPOSITE.csv",  "min_rows": 2500},
            {"label": "Nasdaq 100",       "path": "data/raw/equity/USA_NASDAQ100.csv",         "min_rows": 2500},
            {"label": "Dow Jones (DJI)",  "path": "data/raw/equity/USA_DJI.csv",               "min_rows": 2500},
            {"label": "Russell 2000",     "path": "data/raw/equity/USA_RUSSELL2000.csv",       "min_rows": 2500},
            {"label": "FTSE 100",         "path": "data/raw/equity/UK_FTSE100.csv",            "min_rows": 2500},
            {"label": "FTSE 250",         "path": "data/raw/equity/UK_FTSE250.csv",            "min_rows": 2500},
            {"label": "FTSE 350",         "path": "data/raw/equity/UK_FTSE350.csv",            "min_rows": 2500},
            {"label": "FTSE All-Share",   "path": "data/raw/equity/UK_FTSE_ALL_SHARE.csv",     "min_rows": 2500},
        ],
    },
    {
        "phase": "Goal 1D — Data Gaps (Actions Needed)",
        "items": [
            {"label": "UK GDP — ONS alt source",          "path": None,
             "blocked": "TODO: fetch UK GDP from ONS directly (FRED series discontinued Jul-2020)"},
            {"label": "Composite PMI — historical data",  "path": None,
             "blocked": "TODO: manual collection 2014–2024, no automated source available"},
            {"label": "UK CPI — swap to ONS alt",         "path": None,
             "blocked": "TODO: update process_cpi.py to use UK_cpi_ons_alt.csv instead of UK_cpi.csv"},
            {"label": "UK Current Account — add to panel","path": None,
             "blocked": "TODO: update process_current_account.py to include UK_current_account.csv"},
        ],
    },
    # ── Interim ───────────────────────────────────────────────
    {
        "phase": "Phase 2 — Interim Panels (forward-filled daily)",
        "items": [
            {"label": "GDP panel",               "path": "data/interim/gdp_panel.csv",               "min_rows": 2000},
            {"label": "CPI panel",               "path": "data/interim/cpi_panel.csv",               "min_rows": 2000},
            {"label": "Central Bank Rate panel", "path": "data/interim/central_bank_rate_panel.csv", "min_rows": 2000},
            {"label": "Current Account panel",   "path": "data/interim/current_account_panel.csv",   "min_rows": 2000},
            {"label": "Forex panel",             "path": "data/interim/forex_panel.csv",             "min_rows": 2000},
            {"label": "Equity panel",            "path": "data/interim/equity_panel.csv",            "min_rows": 2000},
        ],
    },
    # ── Goal 2: EDA & Analysis ────────────────────────────────
    {
        "phase": "Goal 2 — EDA Notebooks",
        "items": [
            {"label": "01_eda_macro.ipynb",        "path": "notebooks/01_eda_macro.ipynb",        "is_script": True},
            {"label": "02_eda_forex_equity.ipynb", "path": "notebooks/02_eda_forex_equity.ipynb", "is_script": True},
            {"label": "03_feature_analysis.ipynb", "path": "notebooks/03_feature_analysis.ipynb", "is_script": True},
        ],
    },
    # ── Goal 3: Model Pipeline ────────────────────────────────
    {
        "phase": "Goal 3A — Processed Datasets (ML-ready)",
        "items": [
            {"label": "Dataset 1 — Basic Daily (~130 cols)",           "path": "data/processed/dataset_basic_daily.csv",    "min_rows": 2000},
            {"label": "Dataset 2 — 90-Day Lookback",                   "path": "data/processed/dataset_90day_lookback.csv", "min_rows": 2000},
            {"label": "Dataset 3 — Technical Indicators (~2000 cols)", "path": "data/processed/dataset_technical.csv",      "min_rows": 2000},
        ],
    },
    {
        "phase": "Goal 3B — Model & Evaluation Scripts",
        "items": [
            {"label": "src/models/train.py",                "path": "src/models/train.py",               "is_script": True},
            {"label": "src/models/bayesian_search.py",      "path": "src/models/bayesian_search.py",     "is_script": True},
            {"label": "src/evaluation/walk_forward_cv.py",  "path": "src/evaluation/walk_forward_cv.py", "is_script": True},
            {"label": "src/evaluation/backtest.py",         "path": "src/evaluation/backtest.py",        "is_script": True},
            {"label": "src/evaluation/metrics.py",          "path": "src/evaluation/metrics.py",         "is_script": True},
            {"label": "Trained models (.joblib / .pkl)",    "path": "models/trained",                    "is_dir": True},
            {"label": "Bayesian search results",            "path": "models/search_results",             "is_dir": True},
            {"label": "Model comparison table",             "path": "reports/tables/model_comparison.csv","min_rows": 1},
            {"label": "Backtest / feature plots",           "path": "reports/figures",                   "is_dir": True},
        ],
    },
    # ── Goal 4: Interface ─────────────────────────────────────
    {
        "phase": "Goal 4 — Streamlit Interface",
        "items": [
            {"label": "src/app/app.py", "path": "src/app/app.py", "is_script": True},
        ],
    },
]


# ─────────────────────────────────────────────────────────────
# File inspection helpers
# ─────────────────────────────────────────────────────────────

def _read_csv_meta(path: Path) -> tuple[int, str]:
    """Return (row_count, date_range) by reading lines — no pandas needed."""
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        rows = len(lines) - 1
        if rows <= 0:
            return 0, ""
        first = lines[1].split(",")[0].strip()[:10]
        last  = lines[-1].split(",")[0].strip()[:10]
        return rows, f"{first} → {last}" if first and last else ""
    except Exception:
        return -1, ""


def check_item(item: dict) -> dict:
    """Inspect one checklist item. Returns a result dict with:
    status    : OK | WARN | HEADER_ONLY | MISSING | BLOCKED | EMPTY
    rows      : int or None
    date_range: str
    note      : str
    modified  : str YYYY-MM-DD HH:MM or ""
    """
    if item.get("path") is None:
        return {"status": "BLOCKED", "rows": None, "date_range": "",
                "note": item.get("blocked", "N/A"), "modified": ""}

    path = PROJECT_ROOT / item["path"]

    if item.get("is_dir"):
        if not path.exists():
            return {"status": "MISSING", "rows": None, "date_range": "", "note": "", "modified": ""}
        contents = [f for f in path.iterdir() if f.name not in (".gitkeep", ".gitignore")]
        if not contents:
            return {"status": "EMPTY", "rows": None, "date_range": "",
                    "note": "Folder is empty", "modified": ""}
        return {"status": "OK", "rows": None, "date_range": "",
                "note": f"{len(contents)} file(s)", "modified": ""}

    if item.get("is_script"):
        if not path.exists():
            return {"status": "MISSING", "rows": None, "date_range": "", "note": "", "modified": ""}
        modified = datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        kb = max(1, path.stat().st_size // 1024)
        return {"status": "OK", "rows": None, "date_range": "",
                "note": f"{kb} KB", "modified": modified}

    if not path.exists():
        return {"status": "MISSING", "rows": None, "date_range": "", "note": "", "modified": ""}

    modified = datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
    size = path.stat().st_size

    if size <= 60:
        return {"status": "HEADER_ONLY", "rows": 0, "date_range": "",
                "note": "Header only — no data rows yet", "modified": modified}

    rows, date_range = _read_csv_meta(path)
    min_rows = item.get("min_rows", 1)
    stale    = item.get("stale", "")

    if stale:
        return {"status": "WARN", "rows": rows, "date_range": date_range,
                "note": stale, "modified": modified}
    if rows < min_rows:
        return {"status": "WARN", "rows": rows, "date_range": date_range,
                "note": f"Only {rows:,} rows (need ≥ {min_rows:,})", "modified": modified}
    return {"status": "OK", "rows": rows, "date_range": date_range,
            "note": "", "modified": modified}


def run_checks() -> list[dict]:
    results = []
    for phase_def in CHECKLIST:
        phase_results = []
        for item in phase_def["items"]:
            r = check_item(item)
            phase_results.append({**item, **r})
        results.append({"phase": phase_def["phase"], "items": phase_results})
    return results


# ─────────────────────────────────────────────────────────────
# Pipeline run history
# ─────────────────────────────────────────────────────────────

def load_run_history(n: int = 8) -> list[dict]:
    if not RUN_LOG_PATH.exists():
        return []
    records = []
    with RUN_LOG_PATH.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return records[-n:]


# ─────────────────────────────────────────────────────────────
# Console output
# ─────────────────────────────────────────────────────────────

STATUS_ICON = {
    "OK":          "[OK]     ",
    "WARN":        "[WARN]   ",
    "HEADER_ONLY": "[EMPTY]  ",
    "MISSING":     "[MISSING]",
    "BLOCKED":     "[BLOCKED]",
    "EMPTY":       "[EMPTY]  ",
}

def print_console(results: list[dict]) -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"\n{'='*72}")
    print(f"  GBP/USD ML Prediction — Project Status  [{now}]")
    print(f"{'='*72}")

    total_ok = total_countable = 0

    for phase in results:
        print(f"\n  {phase['phase']}")
        print(f"  {'─'*62}")
        for item in phase["items"]:
            icon   = STATUS_ICON.get(item["status"], "[?]")
            label  = item["label"]
            rows   = f"{item['rows']:,} rows" if item.get("rows") and item["rows"] > 0 else ""
            drange = item.get("date_range", "")
            note   = item.get("note", "")
            parts  = [x for x in [rows, drange, note] if x]
            detail = "  |  ".join(parts)
            print(f"  {icon}  {label:<38} {detail}")

            if item["status"] != "BLOCKED":
                total_countable += 1
            if item["status"] == "OK":
                total_ok += 1

    pct        = round(total_ok / total_countable * 100) if total_countable else 0
    bar_filled = int(pct / 5)
    bar        = "█" * bar_filled + "░" * (20 - bar_filled)

    print(f"\n  {'─'*72}")
    print(f"  Overall  [{bar}]  {pct}%  ({total_ok}/{total_countable} items OK)")
    print(f"  Report   {REPORT_PATH}")
    print(f"{'='*72}\n")


# ─────────────────────────────────────────────────────────────
# HTML generation
# ─────────────────────────────────────────────────────────────

_BADGE_CLASS = {
    "OK":          ("badge-ok",   "OK"),
    "WARN":        ("badge-warn", "WARN"),
    "HEADER_ONLY": ("badge-hdr",  "HEADER ONLY"),
    "MISSING":     ("badge-miss", "MISSING"),
    "BLOCKED":     ("badge-blk",  "BLOCKED"),
    "EMPTY":       ("badge-emp",  "EMPTY"),
}

def _badge(status: str) -> str:
    cls, label = _BADGE_CLASS.get(status, ("badge-blk", status))
    return f'<span class="badge {cls}">{label}</span>'


def _phase_card(ph_name: str, items: list[dict]) -> str:
    n_ok      = sum(1 for it in items if it["status"] == "OK")
    n_warn    = sum(1 for it in items if it["status"] == "WARN")
    n_blocked = sum(1 for it in items if it["status"] == "BLOCKED")
    n_total   = len(items) - n_blocked
    pct       = round(n_ok / n_total * 100) if n_total else 0
    warn_tag  = f' <span class="warn-count">⚠ {n_warn}</span>' if n_warn else ""
    return f"""
    <div class="phase-card">
      <div class="phase-card-name">{ph_name}</div>
      <div class="mini-bar"><div class="mini-fill" style="width:{pct}%"></div></div>
      <div class="phase-card-stats">{n_ok}/{n_total} done{warn_tag}</div>
    </div>"""


def generate_html(results: list[dict], run_history: list[dict]) -> str:
    now        = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    total_ok   = sum(1 for ph in results for it in ph["items"] if it["status"] == "OK")
    total_countable = sum(1 for ph in results for it in ph["items"] if it["status"] != "BLOCKED")
    pct        = round(total_ok / total_countable * 100) if total_countable else 0
    pct_color  = "#16a34a" if pct >= 70 else "#d97706" if pct >= 40 else "#dc2626"

    phase_cards    = "".join(_phase_card(ph["phase"], ph["items"]) for ph in results)
    phase_sections = _build_phase_sections(results)
    history_rows   = _build_history_rows(run_history)

    CSS = _css()
    JS  = _js()

    return f"""<!DOCTYPE html>
<html lang="en" data-theme="light">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Project Status — GBP/USD ML</title>
  <script>
    /* Prevent flash of wrong theme before CSS loads */
    (function(){{
      var t = localStorage.getItem("theme") ||
              (window.matchMedia("(prefers-color-scheme:dark)").matches ? "dark" : "light");
      document.documentElement.setAttribute("data-theme", t);
    }})();
  </script>
  <style>{CSS}</style>
</head>
<body>

<div class="layout">

  <!-- ── Header ── -->
  <header class="header">
    <div>
      <h1>GBP/USD Direction Prediction</h1>
      <p class="subtitle">Project Status Dashboard · {now}</p>
    </div>
    <button class="theme-btn" onclick="toggleTheme()" aria-label="Toggle theme">
      <span class="icon-moon">🌙 Dark</span>
      <span class="icon-sun">☀️ Light</span>
    </button>
  </header>

  <!-- ── Overall progress ── -->
  <section class="card">
    <div class="progress-header">
      <div>
        <h2>Overall Progress</h2>
        <p class="muted">{total_ok} of {total_countable} items complete (BLOCKED items excluded)</p>
      </div>
      <span class="pct-big" style="color:{pct_color}">{pct}%</span>
    </div>
    <div class="progress-track">
      <div class="progress-fill" style="width:{pct}%"></div>
    </div>

    <h3 style="margin:24px 0 12px">Phase Summary</h3>
    <div class="phase-grid">{phase_cards}
    </div>
  </section>

  <!-- ── Phase detail ── -->
  <h2 class="section-title">Phase Details</h2>
  {phase_sections}

  <!-- ── Pipeline run history ── -->
  <section class="card" style="margin-top:8px">
    <h2 style="margin-bottom:16px">Recent Pipeline Runs</h2>
    <div class="tbl-wrap">
      <table>
        <thead>
          <tr>
            <th>Timestamp (UTC)</th><th>Pipeline</th><th>Mode</th>
            <th>Status</th><th>Steps OK</th><th>Elapsed</th>
          </tr>
        </thead>
        <tbody>
          {history_rows or '<tr><td colspan="6" class="no-data">No run history yet</td></tr>'}
        </tbody>
      </table>
    </div>
    <p class="muted" style="margin-top:8px;font-size:12px">
      Source: {RUN_LOG_PATH.relative_to(PROJECT_ROOT)}
    </p>
  </section>

  <!-- ── Legend ── -->
  <div class="legend">
    <span class="muted" style="font-size:13px">Legend:</span>
    {_legend()}
  </div>

  <!-- ── Footer ── -->
  <footer class="footer">
    Run <code>python project_status.py</code> to refresh · Root: {PROJECT_ROOT}
  </footer>

</div><!-- /layout -->

<script>{JS}</script>
</body>
</html>"""


def _build_phase_sections(results: list[dict]) -> str:
    sections = ""
    for ph in results:
        rows_html = ""
        for it in ph["items"]:
            rows_str   = f'{it["rows"]:,}' if it.get("rows") and it["rows"] > 0 else "—"
            date_range = it.get("date_range") or "—"
            note       = it.get("note") or ""
            modified   = it.get("modified") or "—"
            note_cell  = f'<span class="note-warn">{note}</span>' if note and it["status"] in ("WARN","HEADER_ONLY","BLOCKED","EMPTY","MISSING") else note
            rows_html += f"""
          <tr>
            <td class="col-label">{it["label"]}</td>
            <td class="col-status">{_badge(it["status"])}</td>
            <td class="col-num">{rows_str}</td>
            <td class="col-date">{date_range}</td>
            <td class="col-mod">{modified}</td>
            <td class="col-note">{note_cell}</td>
          </tr>"""

        sections += f"""
  <details class="phase-detail" open>
    <summary class="phase-summary">
      <span class="summary-arrow">▶</span>
      <span>{ph["phase"]}</span>
    </summary>
    <div class="tbl-wrap">
      <table>
        <thead>
          <tr>
            <th class="col-label">Item</th>
            <th class="col-status">Status</th>
            <th class="col-num">Rows</th>
            <th class="col-date">Date Range</th>
            <th class="col-mod">Modified</th>
            <th class="col-note">Note</th>
          </tr>
        </thead>
        <tbody>{rows_html}
        </tbody>
      </table>
    </div>
  </details>"""
    return sections


def _build_history_rows(run_history: list[dict]) -> str:
    rows = ""
    for rec in reversed(run_history):
        ts       = rec.get("timestamp", "")[:19].replace("T", " ")
        pipeline = rec.get("pipeline", "?")
        mode     = rec.get("mode", "?")
        success  = rec.get("success")
        steps    = rec.get("steps", [])
        n_ok_s   = sum(1 for s in steps if s.get("ok")) if steps else "—"
        n_total_s= len(steps) if steps else "—"
        elapsed  = rec.get("total_elapsed_seconds") or rec.get("elapsed_s")
        elapsed_str = f"{elapsed:.1f}s" if isinstance(elapsed, (int, float)) else "—"
        badge    = _badge("OK") if success else (_badge("WARN") if success is None else _badge("MISSING"))
        rows += f"""
          <tr>
            <td style="font-family:monospace;font-size:12px">{ts}</td>
            <td><strong>{pipeline}</strong></td>
            <td class="muted" style="font-size:13px">{mode}</td>
            <td>{badge}</td>
            <td style="text-align:center">{n_ok_s}/{n_total_s}</td>
            <td style="text-align:right;font-family:monospace">{elapsed_str}</td>
          </tr>"""
    return rows


def _legend() -> str:
    items = [
        ("OK",          "Sufficient data"),
        ("WARN",        "Has data but stale or partial"),
        ("HEADER_ONLY", "File has header only — no rows"),
        ("MISSING",     "File does not exist"),
        ("BLOCKED",     "No data source available"),
        ("EMPTY",       "Folder is empty"),
    ]
    return "".join(f'<span>{_badge(s)} <span class="muted">{d}</span></span>' for s, d in items)


# ─────────────────────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────────────────────

def _css() -> str:
    return """
:root {
  --bg:       #f1f5f9;
  --surface:  #ffffff;
  --surface2: #f8fafc;
  --border:   #e2e8f0;
  --text:     #0f172a;
  --text2:    #475569;
  --muted:    #64748b;
  --shadow:   0 1px 4px rgba(0,0,0,.08);
  --radius:   10px;
  --prog-bg:  #e2e8f0;
  --prog-fill:#22c55e;

  --ok-bg:#f0fdf4;   --ok-fg:#15803d;   --ok-bd:#86efac;
  --warn-bg:#fffbeb; --warn-fg:#92400e; --warn-bd:#fcd34d;
  --hdr-bg:#fff7ed;  --hdr-fg:#c2410c;  --hdr-bd:#fdba74;
  --miss-bg:#fef2f2; --miss-fg:#b91c1c; --miss-bd:#fca5a5;
  --blk-bg:#f1f5f9;  --blk-fg:#475569;  --blk-bd:#cbd5e1;
  --emp-bg:#faf5ff;  --emp-fg:#6d28d9;  --emp-bd:#c4b5fd;
}

[data-theme="dark"] {
  --bg:       #0f172a;
  --surface:  #1e293b;
  --surface2: #0f172a;
  --border:   #334155;
  --text:     #f1f5f9;
  --text2:    #cbd5e1;
  --muted:    #94a3b8;
  --shadow:   0 1px 4px rgba(0,0,0,.4);
  --prog-bg:  #334155;
  --prog-fill:#4ade80;

  --ok-bg:#052e16;   --ok-fg:#4ade80;   --ok-bd:#166534;
  --warn-bg:#1c1002; --warn-fg:#fbbf24; --warn-bd:#92400e;
  --hdr-bg:#1c0900;  --hdr-fg:#fb923c;  --hdr-bd:#7c2d12;
  --miss-bg:#1c0202; --miss-fg:#f87171; --miss-bd:#7f1d1d;
  --blk-bg:#1e293b;  --blk-fg:#94a3b8;  --blk-bd:#334155;
  --emp-bg:#1a0038;  --emp-fg:#a78bfa;  --emp-bd:#4c1d95;
}

*  { box-sizing:border-box; margin:0; padding:0; }
html { scroll-behavior:smooth; }
body { background:var(--bg); color:var(--text);
       font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
       font-size:15px; line-height:1.5; transition:background .2s,color .2s; }

.layout { max-width:1100px; margin:0 auto; padding:20px 16px 40px; }

/* ── Header ── */
.header { display:flex; justify-content:space-between; align-items:flex-start;
          gap:12px; margin-bottom:20px; flex-wrap:wrap; }
h1 { font-size:clamp(18px,4vw,24px); font-weight:800; letter-spacing:-.3px; }
.subtitle { color:var(--muted); font-size:13px; margin-top:3px; }

.theme-btn { display:flex; align-items:center; gap:6px;
             background:var(--surface); color:var(--text);
             border:1px solid var(--border); border-radius:8px;
             padding:8px 14px; font-size:14px; cursor:pointer;
             white-space:nowrap; transition:background .15s; }
.theme-btn:hover { background:var(--surface2); }

/* Show/hide theme icons via CSS — no JS flash */
[data-theme="light"] .icon-sun  { display:none; }
[data-theme="dark"]  .icon-moon { display:none; }

/* ── Cards ── */
.card { background:var(--surface); border:1px solid var(--border);
        border-radius:var(--radius); padding:20px 24px;
        box-shadow:var(--shadow); margin-bottom:16px; }

.section-title { font-size:17px; font-weight:700; margin:24px 0 10px; }

h2 { font-size:17px; font-weight:700; }
h3 { font-size:15px; font-weight:600; }

/* ── Progress ── */
.progress-header { display:flex; justify-content:space-between;
                   align-items:flex-start; gap:12px; margin-bottom:12px; }
.pct-big { font-size:clamp(28px,6vw,40px); font-weight:800; line-height:1; flex-shrink:0; }
.progress-track { height:14px; background:var(--prog-bg); border-radius:99px; overflow:hidden; }
.progress-fill  { height:100%; background:var(--prog-fill);
                  border-radius:99px; transition:width .4s ease; }

/* ── Phase summary grid ── */
.phase-grid { display:grid; gap:10px;
              grid-template-columns:repeat(auto-fill,minmax(230px,1fr)); }
.phase-card { background:var(--surface2); border:1px solid var(--border);
              border-radius:8px; padding:12px 14px; }
.phase-card-name  { font-size:13px; font-weight:600; color:var(--text);
                    margin-bottom:8px; line-height:1.3; }
.mini-bar  { height:6px; background:var(--prog-bg); border-radius:99px; overflow:hidden; }
.mini-fill { height:100%; background:var(--prog-fill); border-radius:99px; }
.phase-card-stats { margin-top:6px; font-size:12px; color:var(--muted); }
.warn-count { color:#d97706; font-weight:600; }

/* ── Phase detail (details/summary) ── */
.phase-detail { border:1px solid var(--border); border-radius:var(--radius);
                margin-bottom:12px; overflow:hidden; }
.phase-summary { display:flex; align-items:center; gap:10px;
                 padding:12px 16px; background:var(--surface);
                 cursor:pointer; font-weight:600; font-size:15px;
                 list-style:none; user-select:none; }
.phase-summary::-webkit-details-marker { display:none; }
.phase-summary:hover { background:var(--surface2); }
.summary-arrow { font-size:11px; color:var(--muted); transition:transform .2s; flex-shrink:0; }
details[open] .summary-arrow { transform:rotate(90deg); }

/* ── Tables ── */
.tbl-wrap { overflow-x:auto; }
table  { width:100%; border-collapse:collapse; font-size:14px; min-width:540px; }
thead tr { background:var(--surface2); }
th { padding:8px 12px; text-align:left; font-size:12px; font-weight:600;
     color:var(--muted); text-transform:uppercase; letter-spacing:.4px;
     white-space:nowrap; border-bottom:1px solid var(--border); }
td { padding:9px 12px; border-bottom:1px solid var(--border); vertical-align:top; }
tbody tr:last-child td { border-bottom:none; }
tbody tr:hover { background:var(--surface2); }
.no-data { color:var(--muted); padding:16px; text-align:center; }

/* column widths */
.col-label  { min-width:160px; }
.col-status { white-space:nowrap; }
.col-num    { text-align:right; font-family:monospace; white-space:nowrap; }
.col-date   { font-family:monospace; font-size:12px; white-space:nowrap; }
.col-mod    { font-size:12px; color:var(--muted); white-space:nowrap; }
.col-note   { font-size:12px; min-width:140px; }

/* ── Badges ── */
.badge { display:inline-block; padding:2px 8px; border-radius:5px;
         font-size:11px; font-weight:700; border:1px solid; white-space:nowrap; }
.badge-ok   { background:var(--ok-bg);   color:var(--ok-fg);   border-color:var(--ok-bd); }
.badge-warn { background:var(--warn-bg); color:var(--warn-fg); border-color:var(--warn-bd); }
.badge-hdr  { background:var(--hdr-bg);  color:var(--hdr-fg);  border-color:var(--hdr-bd); }
.badge-miss { background:var(--miss-bg); color:var(--miss-fg); border-color:var(--miss-bd); }
.badge-blk  { background:var(--blk-bg);  color:var(--blk-fg);  border-color:var(--blk-bd); }
.badge-emp  { background:var(--emp-bg);  color:var(--emp-fg);  border-color:var(--emp-bd); }

.note-warn { color:var(--warn-fg); }
.muted     { color:var(--muted); }

/* ── Legend ── */
.legend { display:flex; flex-wrap:wrap; gap:12px;
          align-items:center; padding:16px 0 8px; font-size:13px; }

/* ── Footer ── */
.footer { margin-top:24px; font-size:12px; color:var(--muted);
          border-top:1px solid var(--border); padding-top:12px; }
code { background:var(--surface2); border:1px solid var(--border);
       border-radius:4px; padding:1px 5px; font-size:12px; }

/* ── Mobile ── */
@media (max-width:600px) {
  .layout { padding:12px 10px 32px; }
  .card   { padding:14px 14px; }
  .phase-grid { grid-template-columns:1fr 1fr; }
  .progress-header { flex-direction:column; }
  .pct-big { font-size:32px; }
  h1 { font-size:18px; }
  td, th { padding:7px 8px; }
}
@media (max-width:400px) {
  .phase-grid { grid-template-columns:1fr; }
}
"""


# ─────────────────────────────────────────────────────────────
# JavaScript
# ─────────────────────────────────────────────────────────────

def _js() -> str:
    return """
function toggleTheme() {
  var html = document.documentElement;
  var next = html.getAttribute("data-theme") === "dark" ? "light" : "dark";
  html.setAttribute("data-theme", next);
  localStorage.setItem("theme", next);
}
"""


# ─────────────────────────────────────────────────────────────
# main
# ─────────────────────────────────────────────────────────────

def main() -> None:
    no_html = "--no-html" in sys.argv

    results     = run_checks()
    run_history = load_run_history()

    print_console(results)

    if not no_html:
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        REPORT_PATH.write_text(generate_html(results, run_history), encoding="utf-8")
        print(f"Report saved → {REPORT_PATH}\n")


if __name__ == "__main__":
    main()
