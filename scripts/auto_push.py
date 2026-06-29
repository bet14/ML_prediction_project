import subprocess
import sys
from datetime import datetime
from pathlib import Path

BRANCH = "branch_lee"
REPO_DIR = Path(__file__).resolve().parent.parent

# Folders to scan and their card titles
SCAN_FOLDERS = {
    "References": "Références",
    "data": "Données",
    "notebooks": "Notebooks",
    "models": "Modèles",
    "reports": "Rapports",
}

# File extensions to show (others ignored)
ALLOWED_EXT = {".html", ".pdf", ".ipynb", ".csv", ".md", ".png", ".jpg", ".jpeg"}

FILE_ICONS = {
    ".html": "&#128196;",
    ".pdf": "&#128196;",
    ".ipynb": "&#128202;",
    ".csv": "&#128202;",
    ".md": "&#128196;",
    ".png": "&#128444;",
    ".jpg": "&#128444;",
    ".jpeg": "&#128444;",
}


def run(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=REPO_DIR)
    if result.stdout:
        print(result.stdout.strip())
    if result.stderr:
        print(result.stderr.strip())
    return result.returncode


def scan_folders():
    """Returns dict: {folder_name: [relative_paths]}"""
    result = {}
    for folder in SCAN_FOLDERS:
        folder_path = REPO_DIR / folder
        if not folder_path.exists():
            continue
        files = sorted(
            f for f in folder_path.iterdir()
            if f.is_file() and f.suffix.lower() in ALLOWED_EXT
        )
        if files:
            result[folder] = [f.relative_to(REPO_DIR) for f in files]
    return result


def build_card(folder, title, files):
    links = ""
    for f in files:
        icon = FILE_ICONS.get(f.suffix.lower(), "&#128196;")
        href = str(f).replace("\\", "/")
        links += f'                <a class="file-link" href="{href}" target="_blank">\n'
        links += f'                    <span class="file-icon">{icon}</span> {f.name}\n'
        links += f'                </a>\n'
    return (
        f'        <div class="card" id="folder-{folder}">\n'
        f'            <h2>{title}</h2>\n'
        f'            <div class="file-list">\n'
        f'{links}'
        f'            </div>\n'
        f'        </div>'
    )


def update_index():
    index = REPO_DIR / "index.html"
    if not index.exists():
        print("index.html not found, skipping.")
        return

    content = index.read_text(encoding="utf-8")
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    # --- Rebuild dynamic cards block ---
    scanned = scan_folders()
    cards_html = ""
    for folder, files in scanned.items():
        title = SCAN_FOLDERS.get(folder, folder)
        cards_html += build_card(folder, title, files) + "\n"

    # Replace block between markers (or insert before closing card-grid)
    START = "<!-- AUTO-FOLDERS-START -->"
    END = "<!-- AUTO-FOLDERS-END -->"
    block = f"{START}\n{cards_html.rstrip()}\n        {END}"

    if START in content and END in content:
        import re
        content = re.sub(
            re.escape(START) + r".*?" + re.escape(END),
            block,
            content,
            flags=re.DOTALL,
        )
    else:
        # First run: insert before closing </div> of card-grid
        content = content.replace(
            "    </div>\n\n    <footer>",
            f"    {block}\n    </div>\n\n    <footer>"
        )

    # Update footer timestamp
    lines = content.splitlines()
    new_lines = []
    for line in lines:
        if "<footer>" in line and "</footer>" in line:
            indent = line[: len(line) - len(line.lstrip())]
            new_lines.append(
                f"{indent}<footer>branch_lee — ML_prediction_project — last push: {now}</footer>"
            )
        else:
            new_lines.append(line)
    content = "\n".join(new_lines)

    index.write_text(content, encoding="utf-8")
    print(f"index.html updated: {now} — {sum(len(v) for v in scanned.values())} files linked")


def main():
    msg = (
        " ".join(sys.argv[1:])
        if len(sys.argv) > 1
        else f"auto-push {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )

    update_index()

    run("git add -A")
    ret = run(f'git commit -m "{msg}"')
    if ret != 0:
        print("Nothing to commit or commit failed.")
    run(f"git push origin {BRANCH}")


if __name__ == "__main__":
    main()
