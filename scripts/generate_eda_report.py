"""
scripts/generate_eda_report.py

Reads the 3 executed EDA notebooks and generates a standalone HTML summary report.
Run after executing notebooks in JupyterLab (or via menu option 8).

Usage:
    python scripts/generate_eda_report.py
    python scripts/generate_eda_report.py --run-notebooks   # execute notebooks first
    python scripts/generate_eda_report.py --open            # open HTML in browser after
"""

import argparse
import datetime
import html as _html
import json
import subprocess
import sys
from pathlib import Path

ROOT      = Path(__file__).resolve().parent.parent
NOTEBOOKS = ROOT / "notebooks"
REPORTS   = ROOT / "reports"
OUT_FILE  = REPORTS / "eda_summary.html"

NB_SPECS = [
    ("01", "01_eda_macro.ipynb",        "Macro Indicators"),
    ("02", "02_eda_forex_equity.ipynb", "Forex & Equity"),
    ("03", "03_feature_analysis.ipynb", "Feature Analysis"),
]


# ── notebook I/O helpers ──────────────────────────────────────────────────────

def load_nb(path: Path):
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def cell_src(cell) -> str:
    s = cell.get("source", [])
    return "".join(s) if isinstance(s, list) else s


def get_text_outputs(cell) -> list:
    texts = []
    for out in cell.get("outputs", []):
        otype = out.get("output_type", "")
        if otype == "stream":
            t = out.get("text", [])
            texts.append("".join(t) if isinstance(t, list) else t)
        elif otype in ("execute_result", "display_data"):
            data  = out.get("data", {})
            plain = data.get("text/plain", "")
            if plain:
                texts.append("".join(plain) if isinstance(plain, list) else plain)
    return [t for t in texts if t.strip()]


def get_images(cell) -> list:
    images = []
    for out in cell.get("outputs", []):
        data = out.get("data", {})
        png  = data.get("image/png", "")
        if png:
            images.append(png if isinstance(png, str) else "".join(png))
    return images


def get_html_tables(cell) -> list:
    tables = []
    for out in cell.get("outputs", []):
        data = out.get("data", {})
        htm  = data.get("text/html", "")
        if htm:
            tables.append("".join(htm) if isinstance(htm, list) else htm)
    return tables


# ── minimal markdown → HTML (for Key Takeaways cells) ────────────────────────

def _md_line(line: str) -> str:
    s = line.strip()
    if not s:
        return ""
    # bold **text**
    import re
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    # inline code `text`
    s = re.sub(r"`(.+?)`", r"<code>\1</code>", s)
    return s


def md_to_html(text: str) -> str:
    lines  = text.split("\n")
    out    = []
    in_ul  = False

    for line in lines:
        raw = line.rstrip()

        # skip top-level heading (## title) — already rendered by caller
        if raw.startswith("## "):
            continue

        if raw.startswith("### "):
            if in_ul:
                out.append("</ul>"); in_ul = False
            heading = _html.escape(raw[4:])
            # re-apply bold/code
            heading = _md_line(raw[4:])
            out.append(f'<h4 class="nb-h3">{heading}</h4>')

        elif raw.startswith("**") and raw.endswith("**") and raw.count("**") == 2:
            # standalone bold line (sub-heading)
            if in_ul:
                out.append("</ul>"); in_ul = False
            out.append(f'<p class="nb-bold">{_md_line(raw)}</p>')

        elif raw.startswith("- ") or raw.startswith("* "):
            if not in_ul:
                out.append("<ul>"); in_ul = True
            out.append(f"<li>{_md_line(raw[2:])}</li>")

        elif raw == "":
            if in_ul:
                out.append("</ul>"); in_ul = False

        else:
            if in_ul:
                out.append("</ul>"); in_ul = False
            if raw.strip():
                out.append(f'<p class="nb-p">{_md_line(raw)}</p>')

    if in_ul:
        out.append("</ul>")
    return "\n".join(out)


# ── notebook renderer ─────────────────────────────────────────────────────────

def render_nb(nb: dict) -> str:
    if nb is None:
        return '<p class="warn">Notebook not found or not yet executed. Run notebooks first (menu option 7 or 8).</p>'

    parts = []
    for cell in nb.get("cells", []):
        ctype  = cell.get("cell_type", "code")
        source = cell_src(cell).strip()
        if not source:
            continue

        if ctype == "markdown":
            lines = source.split("\n")
            first = lines[0].strip()
            rest  = "\n".join(lines[1:]).strip()

            if first.startswith("# "):
                # top-level title — skip (shown in tab header)
                pass
            elif first.startswith("## "):
                heading = first[3:]
                parts.append(f'<h3 class="nb-h2">{_html.escape(heading)}</h3>')
                if rest:
                    parts.append(f'<div class="nb-body">{md_to_html(rest)}</div>')
            elif first.startswith("### "):
                heading = first[4:]
                parts.append(f'<h4 class="nb-h3">{_html.escape(heading)}</h4>')
                if rest:
                    parts.append(f'<div class="nb-body">{md_to_html(rest)}</div>')
            else:
                # description / formula block
                if source:
                    parts.append(f'<p class="nb-desc">{_html.escape(source[:300])}</p>')
            continue

        # code cell — show outputs only
        texts  = get_text_outputs(cell)
        images = get_images(cell)
        tables = get_html_tables(cell)

        if not (texts or images or tables):
            continue

        cell_html = ['<div class="cell-out">']
        for text in texts:
            cell_html.append(f'<pre class="text-out">{_html.escape(text)}</pre>')
        for tbl in tables:
            cell_html.append(f'<div class="table-wrap">{tbl}</div>')
        for img in images:
            cell_html.append(
                f'<div class="img-wrap">'
                f'<img src="data:image/png;base64,{img}" alt="chart">'
                f'</div>'
            )
        cell_html.append('</div>')
        parts.append("\n".join(cell_html))

    if not parts:
        return '<p class="warn">No cell outputs found — run the notebook first (menu option 7 or 8).</p>'
    return "\n".join(parts)


# ── run notebooks ─────────────────────────────────────────────────────────────

def run_notebooks():
    print("Running all 3 notebooks via nbconvert...")
    for nb_id, nb_file, nb_name in NB_SPECS:
        nb_path = NOTEBOOKS / nb_file
        print(f"  [{nb_id}] {nb_name} ...", end=" ", flush=True)
        result = subprocess.run(
            [sys.executable, "-m", "jupyter", "nbconvert",
             "--to", "notebook", "--execute", "--inplace",
             "--ExecutePreprocessor.timeout=600",
             str(nb_path)],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            print("OK")
        else:
            print("FAILED")
            if result.stderr:
                print(result.stderr[-600:])


# ── CSS / JS ──────────────────────────────────────────────────────────────────

_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: #f4f6f9; color: #1f2937; font-size: 14px;
}
header {
  background: linear-gradient(135deg, #1e3a5f 0%, #2563eb 100%);
  color: white; padding: 20px 32px;
}
header h1 { font-size: 1.4rem; margin-bottom: 4px; font-weight: 700; }
header p  { opacity: 0.75; font-size: 0.82rem; }

.tab-bar {
  background: #1e3a5f; display: flex; gap: 2px;
  padding: 0 24px; overflow-x: auto;
}
.tablink {
  background: transparent; color: rgba(255,255,255,0.6);
  border: none; padding: 10px 22px; cursor: pointer;
  font-size: 0.88rem; border-bottom: 3px solid transparent;
  transition: all .2s; white-space: nowrap;
}
.tablink:hover  { color: #fff; }
.tablink.active { color: #fff; border-bottom-color: #60a5fa; font-weight: 600; }

.tabcontent { display: none; padding: 24px 32px 48px; max-width: 1200px; }
.tabcontent.visible { display: block; }

h2 {
  font-size: 1.2rem; color: #1e3a5f; margin-bottom: 18px;
  padding-bottom: 8px; border-bottom: 2px solid #2563eb;
}
h3.nb-h2 {
  font-size: 1rem; color: #1e3a5f; margin: 22px 0 6px;
  padding: 6px 12px; background: #e8f0fe;
  border-left: 4px solid #2563eb; border-radius: 2px;
}
h4.nb-h3 {
  font-size: 0.91rem; font-weight: 600; color: #374151;
  margin: 14px 0 4px; padding-left: 10px;
  border-left: 3px solid #93c5fd;
}
.nb-body { margin: 4px 0 10px 6px; }
.nb-body ul  { padding-left: 20px; margin: 4px 0; }
.nb-body li  { margin: 3px 0; line-height: 1.6; }
.nb-body p, .nb-p  { margin: 4px 0; line-height: 1.6; }
.nb-bold { font-weight: 600; color: #1e40af; margin: 8px 0 2px; }
.nb-desc { color: #6b7280; font-style: italic; font-size: 0.82rem; margin: 3px 0 8px; }
code { background: #f3f4f6; padding: 1px 4px; border-radius: 3px;
       font-family: 'Consolas', monospace; font-size: 0.9em; }

.cell-out {
  margin: 6px 0 14px; background: #fff;
  border-radius: 6px; border: 1px solid #e5e7eb; overflow: hidden;
}
pre.text-out {
  font-family: 'Consolas', 'SF Mono', monospace;
  font-size: 12px; line-height: 1.55; color: #1f2937;
  background: #f9fafb; padding: 12px 16px;
  overflow-x: auto; white-space: pre-wrap; word-break: break-word;
  border-bottom: 1px solid #e5e7eb;
}
pre.text-out:last-child { border-bottom: none; }

.table-wrap { padding: 10px 14px; overflow-x: auto; }
.table-wrap table { border-collapse: collapse; font-size: 12px; }
.table-wrap th, .table-wrap td {
  border: 1px solid #d1d5db; padding: 4px 12px; text-align: right;
}
.table-wrap th { background: #f3f4f6; color: #374151; text-align: center; }

.img-wrap { padding: 14px; text-align: center; background: #fff; }
.img-wrap img {
  max-width: 100%; border-radius: 4px;
  box-shadow: 0 1px 5px rgba(0,0,0,0.10);
}

.warn {
  color: #b91c1c; background: #fee2e2;
  padding: 12px 16px; border-radius: 6px; margin: 10px 0;
  font-size: 0.88rem;
}
footer {
  text-align: center; padding: 20px; color: #9ca3af;
  font-size: 0.78rem; border-top: 1px solid #e5e7eb; margin-top: 24px;
}
"""

_JS = """
function openTab(evt, tabId) {
  document.querySelectorAll('.tabcontent').forEach(t => t.classList.remove('visible'));
  document.querySelectorAll('.tablink').forEach(b => b.classList.remove('active'));
  document.getElementById(tabId).classList.add('visible');
  evt.currentTarget.classList.add('active');
}
document.querySelector('.tablink').click();
"""


# ── HTML assembly ─────────────────────────────────────────────────────────────

def build_html(rendered: dict) -> str:
    now  = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    btns = "\n".join(
        f'  <button class="tablink" onclick="openTab(event,\'nb{nb_id}\')">{_html.escape(name)}</button>'
        for nb_id, _, name in NB_SPECS
    )
    tabs = "\n".join(
        f'<div id="nb{nb_id}" class="tabcontent">\n<h2>{_html.escape(name)}</h2>\n{rendered.get(nb_id, "")}\n</div>'
        for nb_id, _, name in NB_SPECS
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>EDA Summary — GBP/USD ML Project</title>
<style>{_CSS}</style>
</head>
<body>

<header>
  <h1>EDA Summary — GBP/USD Direction Prediction (2014–2024)</h1>
  <p>Generated: {now}&nbsp;&nbsp;|&nbsp;&nbsp;Branch: branch_lee&nbsp;&nbsp;|&nbsp;&nbsp;
     Notebooks: 01 Macro &middot; 02 Forex &amp; Equity &middot; 03 Feature Analysis</p>
</header>

<div class="tab-bar">
{btns}
</div>

{tabs}

<footer>Auto-generated by <code>scripts/generate_eda_report.py</code> — GBP/USD ML Prediction Project</footer>

<script>{_JS}</script>
</body>
</html>"""


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="Generate EDA HTML summary from executed notebooks.")
    ap.add_argument("--run-notebooks", action="store_true",
                    help="Execute all 3 notebooks before generating the report.")
    ap.add_argument("--open", action="store_true",
                    help="Open the HTML report in the default browser after generating.")
    args = ap.parse_args()

    if args.run_notebooks:
        run_notebooks()

    print("Reading notebooks...", flush=True)
    rendered = {}
    for nb_id, nb_file, nb_name in NB_SPECS:
        nb = load_nb(NOTEBOOKS / nb_file)
        if nb is None:
            print(f"  WARNING: {nb_file} not found — tab will show placeholder.")
        else:
            n_cells = len(nb.get("cells", []))
            n_out   = sum(1 for c in nb.get("cells", []) if c.get("outputs"))
            print(f"  [{nb_id}] {nb_name}: {n_cells} cells, {n_out} with outputs")
        rendered[nb_id] = render_nb(nb)

    print("Building HTML...", flush=True)
    htm = build_html(rendered)

    REPORTS.mkdir(exist_ok=True)
    OUT_FILE.write_text(htm, encoding="utf-8")
    size_kb = OUT_FILE.stat().st_size / 1024
    print(f"Saved: {OUT_FILE.relative_to(ROOT)}  ({size_kb:.0f} KB)")

    if args.open:
        import webbrowser
        webbrowser.open(OUT_FILE.as_uri())
        print("Opened in browser.")
    else:
        print(f"Open manually: {OUT_FILE}")


if __name__ == "__main__":
    main()
