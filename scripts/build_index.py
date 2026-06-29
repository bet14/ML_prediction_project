"""
build_index.py -- Scan project and regenerate index.html.

Finds .html .py .md .jsonl .pdf .csv files, organises by type,
sorts by most-recently-modified by default, and writes index.html.
Each table has clickable column headers to re-sort asc/desc.

Usage:
    python scripts/build_index.py
"""

import re
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUT_PATH     = PROJECT_ROOT / "index.html"

# ── scan config ───────────────────────────────────────────────
SKIP_DIRS  = {".git", "__pycache__", ".claude", ".mypy_cache",
              "node_modules", ".venv", "venv", "forex_chunks"}
SKIP_FILES = {"index.html"}

EXT_TO_CAT = {
    ".html":  "html",
    ".py":    "python",
    ".md":    "markdown",
    ".jsonl": "logs",
    ".pdf":   "pdf",
    ".csv":   "data",
}

# Order matters — shown top to bottom
CATEGORIES = [
    {"key": "html",     "label": "HTML",     "icon": "🌐",
     "desc": "Reports & dashboards — click to open in browser"},
    {"key": "data",     "label": "Data",     "icon": "📊",
     "desc": "CSV data files (raw, interim, processed)"},
    {"key": "python",   "label": "Python",   "icon": "🐍",
     "desc": "Fetch, feature, model and pipeline scripts"},
    {"key": "markdown", "label": "Markdown", "icon": "📄",
     "desc": "Documentation, guides, session logs"},
    {"key": "logs",     "label": "Logs",     "icon": "📋",
     "desc": "JSONL pipeline run logs"},
    {"key": "pdf",      "label": "PDF",      "icon": "📕",
     "desc": "Research papers — click to open in browser"},
]

LINKABLE_EXTS = {".html", ".pdf", ".py", ".md", ".csv", ".jsonl"}


# ── helpers ───────────────────────────────────────────────────

def _fmt_size(n: int) -> str:
    if n >= 1_048_576: return f"{n/1_048_576:.1f} MB"
    if n >= 1_024:     return f"{n/1_024:.1f} KB"
    return f"{n} B"


def _count_csv_rows(path: Path) -> tuple[str, int]:
    """Return (display_str, raw_int) row count for a CSV (excl. header)."""
    try:
        with open(path, "rb") as f:
            n = sum(1 for _ in f) - 1
        return (f"{n:,}", n) if n >= 0 else ("—", -1)
    except Exception:
        return ("—", -1)


def scan() -> dict[str, list[dict]]:
    buckets: dict[str, list] = {c["key"]: [] for c in CATEGORIES}

    for path in sorted(PROJECT_ROOT.rglob("*")):
        if not path.is_file():
            continue
        if any(skip in path.parts for skip in SKIP_DIRS):
            continue
        if path.name in SKIP_FILES:
            continue

        ext = path.suffix.lower()
        cat = EXT_TO_CAT.get(ext)
        if not cat:
            continue

        rel     = path.relative_to(PROJECT_ROOT)
        rel_str = str(rel).replace("\\", "/")
        folder  = str(rel.parent).replace("\\", "/")
        if folder == ".":
            folder = "(root)"

        stat = path.stat()
        size_bytes = stat.st_size
        mtime_ts   = stat.st_mtime           # float, used for sorting
        modified   = datetime.fromtimestamp(mtime_ts).strftime("%Y-%m-%d")

        entry = {
            "name":       path.name,
            "rel":        rel_str,
            "folder":     folder,
            "size":       _fmt_size(size_bytes),
            "size_bytes": size_bytes,
            "modified":   modified,
            "mtime_ts":   mtime_ts,
            "linkable":   ext in LINKABLE_EXTS,
        }

        if cat == "data":
            rows_str, rows_int = _count_csv_rows(path)
            entry["rows"]     = rows_str
            entry["rows_int"] = rows_int

        buckets[cat].append(entry)

    # default sort: most-recently-modified first
    for lst in buckets.values():
        lst.sort(key=lambda e: e["mtime_ts"], reverse=True)

    return buckets


# ── HTML row / section builders ───────────────────────────────

def _file_cell(f: dict) -> str:
    if f["linkable"]:
        return f'<a href="{f["rel"]}" target="_blank">{f["name"]}</a>'
    return f["name"]


def _rows_standard(files: list[dict]) -> str:
    """Table body for HTML / Python / Markdown / Logs / PDF."""
    if not files:
        return '<tr><td colspan="4" class="empty">No files found</td></tr>'
    out = ""
    for f in files:
        search = f"{f['name'].lower()} {f['folder'].lower()}"
        out += (
            f'<tr data-search="{search}">'
            f'<td class="col-name">{_file_cell(f)}</td>'
            f'<td class="col-folder">{f["folder"]}</td>'
            f'<td class="col-size" data-val="{f["size_bytes"]}">{f["size"]}</td>'
            f'<td class="col-mod"  data-val="{f["modified"]}">{f["modified"]}</td>'
            f'</tr>\n'
        )
    return out


def _rows_data(files: list[dict]) -> str:
    """Table body for CSV data files (extra Rows column)."""
    if not files:
        return '<tr><td colspan="5" class="empty">No CSV files found</td></tr>'
    out = ""
    for f in files:
        rows_val = f.get("rows_int", -1)
        rows_str = f.get("rows", "—")
        search   = f"{f['name'].lower()} {f['folder'].lower()}"
        out += (
            f'<tr data-search="{search}">'
            f'<td class="col-name">{_file_cell(f)}</td>'
            f'<td class="col-folder">{f["folder"]}</td>'
            f'<td class="col-rows" data-val="{rows_val}" style="text-align:right">{rows_str}</td>'
            f'<td class="col-size" data-val="{f["size_bytes"]}">{f["size"]}</td>'
            f'<td class="col-mod"  data-val="{f["modified"]}">{f["modified"]}</td>'
            f'</tr>\n'
        )
    return out


def _thead(cols: list[tuple]) -> str:
    """cols = list of (label, key, align, is_default_sort).
       Modified column is pre-marked sorted-desc (matches Python default sort)."""
    cells = ""
    for i, (label, key, align, is_default) in enumerate(cols):
        icon    = "↓" if is_default else "↕"
        cls     = f"col-{key} sortable" + (" sorted-desc" if is_default else "")
        style   = f'style="text-align:{align}"'
        cells  += (f'<th class="{cls}" data-col="{i}" onclick="sortTable(this)" {style}>'
                   f'{label} <span class="sort-icon">{icon}</span></th>')
    return f"<thead><tr>{cells}</tr></thead>"


THEAD_STANDARD = _thead([
    ("File",     "name",   "left",  False),
    ("Folder",   "folder", "left",  False),
    ("Size",     "size",   "right", False),
    ("Modified", "mod",    "left",  True),   # ← default sort desc
])

THEAD_DATA = _thead([
    ("File",     "name",   "left",  False),
    ("Folder",   "folder", "left",  False),
    ("Rows",     "rows",   "right", False),
    ("Size",     "size",   "right", False),
    ("Modified", "mod",    "left",  True),   # ← default sort desc
])


def _section(cat: dict, files: list[dict]) -> str:
    count   = len(files)
    is_data = cat["key"] == "data"
    thead   = THEAD_DATA   if is_data else THEAD_STANDARD
    tbody   = _rows_data(files) if is_data else _rows_standard(files)
    min_w   = "580px"      if is_data else "480px"

    return f"""
  <details class="section" open>
    <summary class="section-head">
      <span class="arrow">▶</span>
      <span class="sec-icon">{cat["icon"]}</span>
      <span class="sec-label">{cat["label"]}</span>
      <span class="sec-count">{count} file{"s" if count != 1 else ""}</span>
      <span class="sec-desc">{cat["desc"]}</span>
    </summary>
    <div class="tbl-wrap">
      <table style="min-width:{min_w}">
        {thead}
        <tbody class="sec-body" data-cat="{cat["key"]}">
{tbody}
        </tbody>
      </table>
    </div>
  </details>"""


def _stats_bar(buckets: dict) -> str:
    parts = []
    for cat in CATEGORIES:
        n = len(buckets[cat["key"]])
        parts.append(f'<span class="stat">{cat["icon"]} <b>{n}</b> {cat["label"]}</span>')
    return " · ".join(parts)


# ── CSS ───────────────────────────────────────────────────────

CSS = """
:root{
  --bg:#f1f5f9;--surface:#fff;--surface2:#f8fafc;
  --border:#e2e8f0;--text:#0f172a;--muted:#64748b;
  --accent:#3b82f6;--accent2:#1d4ed8;
  --shadow:0 1px 4px rgba(0,0,0,.08);
  --th-bg:#f1f5f9;
}
[data-theme="dark"]{
  --bg:#0f172a;--surface:#1e293b;--surface2:#162032;
  --border:#334155;--text:#f1f5f9;--muted:#94a3b8;
  --accent:#60a5fa;--accent2:#93c5fd;
  --shadow:0 1px 4px rgba(0,0,0,.4);
  --th-bg:#162032;
}
*{box-sizing:border-box;margin:0;padding:0;}
html{scroll-behavior:smooth;}
body{background:var(--bg);color:var(--text);
     font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
     font-size:15px;line-height:1.5;transition:background .2s,color .2s;}
.layout{max-width:1040px;margin:0 auto;padding:24px 16px 48px;}

/* header */
header{display:flex;justify-content:space-between;align-items:flex-start;
       gap:12px;flex-wrap:wrap;margin-bottom:20px;}
h1{font-size:clamp(18px,4vw,24px);font-weight:800;letter-spacing:-.3px;}
.subtitle{color:var(--muted);font-size:13px;margin-top:3px;}
.theme-btn{background:var(--surface);color:var(--text);
           border:1px solid var(--border);border-radius:8px;
           padding:7px 14px;font-size:14px;cursor:pointer;white-space:nowrap;
           transition:background .15s;}
.theme-btn:hover{background:var(--surface2);}
[data-theme="light"] .icon-sun {display:none;}
[data-theme="dark"]  .icon-moon{display:none;}

/* search */
.search-wrap{position:relative;margin-bottom:16px;}
.search-wrap input{width:100%;padding:10px 16px 10px 40px;
  border:1px solid var(--border);border-radius:8px;
  background:var(--surface);color:var(--text);font-size:15px;outline:none;
  transition:border .15s;}
.search-wrap input:focus{border-color:var(--accent);}
.search-icon{position:absolute;left:13px;top:50%;transform:translateY(-50%);
             color:var(--muted);pointer-events:none;}

/* stats bar */
.stats{display:flex;flex-wrap:wrap;gap:10px;margin-bottom:20px;
       background:var(--surface);border:1px solid var(--border);
       border-radius:10px;padding:13px 18px;box-shadow:var(--shadow);}
.stat{font-size:14px;color:var(--muted);}
.stat b{color:var(--text);}

/* sections */
.section{border:1px solid var(--border);border-radius:10px;
         margin-bottom:12px;overflow:hidden;box-shadow:var(--shadow);}
.section-head{display:flex;align-items:center;gap:10px;flex-wrap:wrap;
              padding:12px 16px;background:var(--surface);
              cursor:pointer;list-style:none;user-select:none;}
.section-head::-webkit-details-marker{display:none;}
.section-head:hover{background:var(--surface2);}
.arrow{font-size:11px;color:var(--muted);transition:transform .2s;flex-shrink:0;}
details[open] .arrow{transform:rotate(90deg);}
.sec-icon{font-size:18px;flex-shrink:0;}
.sec-label{font-weight:700;font-size:15px;}
.sec-count{background:var(--surface2);border:1px solid var(--border);
           border-radius:20px;padding:1px 9px;font-size:12px;color:var(--muted);}
.sec-desc{font-size:13px;color:var(--muted);}

/* table */
.tbl-wrap{overflow-x:auto;}
table{width:100%;border-collapse:collapse;font-size:14px;}
thead tr{background:var(--th-bg);}
th{padding:8px 12px;text-align:left;font-size:11px;font-weight:600;
   color:var(--muted);text-transform:uppercase;letter-spacing:.4px;
   border-bottom:2px solid var(--border);white-space:nowrap;
   position:sticky;top:0;background:var(--th-bg);z-index:1;}

/* sortable headers */
th.sortable{cursor:pointer;transition:color .15s;}
th.sortable:hover{color:var(--accent);}
th.sorted-asc,th.sorted-desc{color:var(--accent);}
.sort-icon{display:inline-block;margin-left:3px;font-size:12px;
           opacity:.45;transition:opacity .15s;}
th.sortable:hover .sort-icon{opacity:.8;}
th.sorted-asc .sort-icon,th.sorted-desc .sort-icon{opacity:1;}

td{padding:8px 12px;border-bottom:1px solid var(--border);vertical-align:middle;}
tbody tr:last-child td{border-bottom:none;}
tbody tr:hover{background:var(--surface2);}
tr.hidden{display:none;}
.empty{color:var(--muted);text-align:center;padding:14px;}

/* columns */
.col-name  {min-width:160px;}
.col-folder{font-size:12px;color:var(--muted);min-width:120px;}
.col-size  {text-align:right;font-family:monospace;font-size:12px;white-space:nowrap;}
.col-rows  {text-align:right;font-family:monospace;font-size:12px;white-space:nowrap;}
.col-mod   {font-size:12px;color:var(--muted);white-space:nowrap;}

a{color:var(--accent);text-decoration:none;}
a:hover{color:var(--accent2);text-decoration:underline;}

.no-match{display:none;text-align:center;padding:32px 16px;
          color:var(--muted);font-size:15px;}

/* dashboard */
.dash-card{background:var(--surface);border:1px solid var(--border);
           border-radius:10px;padding:18px 22px;margin-bottom:14px;
           box-shadow:var(--shadow);}
.dash-header{display:flex;justify-content:space-between;align-items:flex-start;
             gap:12px;flex-wrap:wrap;margin-bottom:10px;}
.dash-pct{font-size:clamp(28px,6vw,38px);font-weight:800;line-height:1;flex-shrink:0;}
.status-link{display:inline-block;padding:6px 14px;border-radius:8px;
             background:var(--accent);color:#fff;font-size:13px;font-weight:600;
             text-decoration:none;white-space:nowrap;align-self:center;}
.status-link:hover{background:var(--accent2);color:#fff;text-decoration:none;}
.progress-track{height:12px;background:var(--border);border-radius:99px;
                overflow:hidden;margin-bottom:16px;}
.progress-fill{height:100%;border-radius:99px;transition:width .4s ease;}
.dash-phase-grid{display:grid;gap:8px;
                 grid-template-columns:repeat(auto-fill,minmax(220px,1fr));
                 margin-top:4px;}
.dash-phase-card{background:var(--surface2);border:1px solid var(--border);
                 border-radius:8px;padding:10px 12px;}
.dash-phase-name{font-size:12px;font-weight:600;margin-bottom:6px;line-height:1.3;}
.dash-phase-stats{margin-top:4px;font-size:11px;color:var(--muted);}
.mini-bar{height:5px;background:var(--border);border-radius:99px;overflow:hidden;}
.mini-fill{height:100%;background:#22c55e;border-radius:99px;}
.dash-sub{font-size:12px;color:var(--muted);margin-top:2px;}
.recent-tbl{width:100%;border-collapse:collapse;font-size:13px;margin-top:10px;}
.recent-tbl th{text-align:left;font-size:11px;font-weight:600;color:var(--muted);
               text-transform:uppercase;letter-spacing:.4px;padding:6px 10px;
               border-bottom:1px solid var(--border);}
.recent-tbl td{padding:6px 10px;border-bottom:1px solid var(--border);}
.recent-tbl tbody tr:last-child td{border-bottom:none;}
.recent-tbl tbody tr:hover{background:var(--surface2);}
.recent-tbl .rc-folder{font-size:11px;color:var(--muted);}
.recent-tbl .rc-mod{font-size:11px;color:var(--muted);white-space:nowrap;}

footer{margin-top:28px;font-size:12px;color:var(--muted);
       border-top:1px solid var(--border);padding-top:12px;}
code{background:var(--surface2);border:1px solid var(--border);
     border-radius:4px;padding:1px 5px;font-size:12px;}

@media(max-width:600px){
  .sec-desc{display:none;}
  .layout{padding:12px 10px 32px;}
  td,th{padding:7px 8px;}
  h1{font-size:18px;}
}
"""

# ── JavaScript ────────────────────────────────────────────────

JS = """
/* ── theme ── */
function toggleTheme(){
  var h=document.documentElement;
  var t=h.getAttribute("data-theme")==="dark"?"light":"dark";
  h.setAttribute("data-theme",t);
  localStorage.setItem("theme",t);
}

/* ── search ── */
var $search=document.getElementById("search");
$search.addEventListener("input",function(){
  var q=this.value.trim().toLowerCase();
  var anyVisible=false;
  document.querySelectorAll("tbody[data-cat]").forEach(function(tbody){
    var vis=0;
    tbody.querySelectorAll("tr[data-search]").forEach(function(row){
      var match=!q||row.dataset.search.includes(q);
      row.classList.toggle("hidden",!match);
      if(match)vis++;
    });
    anyVisible=anyVisible||(vis>0);
    var det=tbody.closest("details");
    if(det)det.open=(vis>0||!q);
  });
  document.getElementById("no-match").style.display=(!anyVisible&&q)?"block":"none";
});

/* ── sort ── */
function sortTable(th){
  var table=th.closest("table");
  var tbody=table.querySelector("tbody");
  var col=parseInt(th.dataset.col);

  /* toggle direction; default to desc on first click of a new column */
  var wasDesc=th.classList.contains("sorted-desc");
  var asc=wasDesc;  /* if was desc → go asc; otherwise → go desc */

  /* clear all sort markers in this table */
  table.querySelectorAll("th.sortable").forEach(function(t){
    t.classList.remove("sorted-asc","sorted-desc");
    var icon=t.querySelector(".sort-icon");
    if(icon)icon.textContent="↕";
  });

  th.classList.add(asc?"sorted-asc":"sorted-desc");
  var icon=th.querySelector(".sort-icon");
  if(icon)icon.textContent=asc?"↑":"↓";

  /* sort all rows (hidden rows stay hidden via CSS) */
  var rows=Array.from(tbody.querySelectorAll("tr"));
  rows.sort(function(a,b){
    var ca=a.cells[col],cb=b.cells[col];
    if(!ca||!cb)return 0;
    /* prefer data-val for numeric/date precision */
    var va=ca.dataset.val!==undefined?ca.dataset.val:ca.textContent.trim();
    var vb=cb.dataset.val!==undefined?cb.dataset.val:cb.textContent.trim();
    var na=parseFloat(va),nb=parseFloat(vb);
    if(!isNaN(na)&&!isNaN(nb))return asc?na-nb:nb-na;
    if(va<vb)return asc?-1:1;
    if(va>vb)return asc?1:-1;
    return 0;
  });
  rows.forEach(function(r){tbody.appendChild(r);});
}
"""

# ── dashboard helpers ─────────────────────────────────────────

STATUS_PATH = PROJECT_ROOT / "reports" / "project_status.html"
STATUS_REL  = "reports/project_status.html"   # relative link for cloned repos


def _parse_project_status() -> dict | None:
    """Extract progress data from reports/project_status.html via regex."""
    if not STATUS_PATH.exists():
        return None
    try:
        html = STATUS_PATH.read_text(encoding="utf-8")

        m = re.search(r'class="pct-big"[^>]*>(\d+)%', html)
        overall_pct = int(m.group(1)) if m else 0

        m = re.search(r'class="muted">(\d+ of \d+ items complete[^<]*)<', html)
        summary = m.group(1).strip() if m else ""

        names     = re.findall(r'class="phase-card-name">\s*(.*?)\s*</div>', html, re.DOTALL)
        fills     = [int(x) for x in re.findall(r'class="mini-fill"[^>]*style="width:(\d+)%"', html)]
        stats_raw = re.findall(r'class="phase-card-stats">(.*?)</div>', html, re.DOTALL)
        stats     = [re.sub(r'<[^>]+>', '', s).strip() for s in stats_raw]

        phases = [
            {"name": n, "pct": p, "stats": s}
            for n, p, s in zip(names, fills, stats)
        ]
        return {"overall_pct": overall_pct, "summary": summary, "phases": phases}
    except Exception:
        return None


def _dashboard_block(buckets: dict) -> str:
    """Build the top dashboard: progress card + recent files card."""
    status = _parse_project_status()

    # collect all files for recent list
    all_files = [f for lst in buckets.values() for f in lst]
    recent = sorted(all_files, key=lambda e: e["mtime_ts"], reverse=True)[:5]

    recent_rows = ""
    for f in recent:
        cell = (f'<a href="{f["rel"]}" target="_blank">{f["name"]}</a>'
                if f["linkable"] else f["name"])
        recent_rows += (
            f'<tr>'
            f'<td class="col-name">{cell}</td>'
            f'<td class="rc-folder">{f["folder"]}</td>'
            f'<td class="rc-mod">{f["modified"]}</td>'
            f'</tr>\n'
        )

    # progress card
    if status:
        pct   = status["overall_pct"]
        color = "#22c55e" if pct >= 70 else ("#d97706" if pct >= 40 else "#ef4444")
        phase_cards = "".join(
            f'<div class="dash-phase-card">'
            f'<div class="dash-phase-name">{ph["name"]}</div>'
            f'<div class="mini-bar"><div class="mini-fill" style="width:{ph["pct"]}%"></div></div>'
            f'<div class="dash-phase-stats">{ph["stats"]}</div>'
            f'</div>'
            for ph in status["phases"]
        )
        progress_html = f"""
  <div class="dash-card">
    <div class="dash-header">
      <div>
        <h2>Project Progress</h2>
        <p class="dash-sub">{status["summary"]}</p>
      </div>
      <div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap">
        <span class="dash-pct" style="color:{color}">{pct}%</span>
        <a href="{STATUS_REL}" target="_blank" class="status-link">Full Status →</a>
      </div>
    </div>
    <div class="progress-track">
      <div class="progress-fill" style="width:{pct}%;background:{color}"></div>
    </div>
    <div class="dash-phase-grid">{phase_cards}</div>
  </div>"""
    else:
        progress_html = f"""
  <div class="dash-card">
    <div class="dash-header">
      <h2>Project Progress</h2>
      <a href="{STATUS_REL}" target="_blank" class="status-link">View Status →</a>
    </div>
    <p style="color:var(--muted);font-size:13px">
      Run <code>python scripts/project_status.py</code> to generate the status report.
    </p>
  </div>"""

    recent_card = f"""
  <div class="dash-card">
    <h2>Recently Modified</h2>
    <table class="recent-tbl">
      <thead><tr>
        <th>File</th><th>Folder</th><th>Modified</th>
      </tr></thead>
      <tbody>{recent_rows}</tbody>
    </table>
  </div>"""

    return progress_html + recent_card


# ── main ─────────────────────────────────────────────────────

def build() -> None:
    now     = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    buckets = scan()
    total   = sum(len(v) for v in buckets.values())

    sections  = "".join(_section(cat, buckets[cat["key"]]) for cat in CATEGORIES)
    stats     = _stats_bar(buckets)
    dashboard = _dashboard_block(buckets)

    html = f"""<!DOCTYPE html>
<html lang="en" data-theme="light">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Index — GBP/USD ML Project</title>
  <script>
    /* prevent theme flash */
    (function(){{
      var t=localStorage.getItem("theme")||
            (window.matchMedia("(prefers-color-scheme:dark)").matches?"dark":"light");
      document.documentElement.setAttribute("data-theme",t);
    }})();
  </script>
  <style>{CSS}</style>
</head>
<body>
<div class="layout">

  <header>
    <div>
      <h1>GBP/USD ML Prediction — File Index</h1>
      <p class="subtitle">{total} files · Generated {now} · Default sort: most recently modified</p>
    </div>
    <button class="theme-btn" onclick="toggleTheme()">
      <span class="icon-moon">🌙 Dark</span>
      <span class="icon-sun">☀️ Light</span>
    </button>
  </header>

  {dashboard}

  <div class="search-wrap">
    <span class="search-icon">🔍</span>
    <input id="search" type="search"
           placeholder="Filter by file name or folder…" autocomplete="off">
  </div>

  <div class="stats">{stats}</div>
  <p id="no-match" class="no-match">No files match your search.</p>

  {sections}

  <footer>
    Auto-generated by <code>python scripts/build_index.py</code> ·
    Click any column header to sort ↑↓ ·
    Run <code>update.bat</code> to refresh
  </footer>

</div>
<script>{JS}</script>
</body>
</html>"""

    OUT_PATH.write_text(html, encoding="utf-8")
    print(f"Index saved → {OUT_PATH}  ({total} files)")
    for cat in CATEGORIES:
        n = len(buckets[cat["key"]])
        print(f"  {cat['icon']}  {cat['label']:10} {n}")


if __name__ == "__main__":
    build()
