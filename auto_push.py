import subprocess
import sys
from datetime import datetime
from pathlib import Path

BRANCH = "branch_lee"
REPO_DIR = Path(__file__).parent


def run(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=REPO_DIR)
    if result.stdout:
        print(result.stdout.strip())
    if result.stderr:
        print(result.stderr.strip())
    return result.returncode


def update_index_timestamp():
    """Met à jour le footer de index.html avec la date du dernier push."""
    index = REPO_DIR / "index.html"
    if not index.exists():
        return
    content = index.read_text(encoding="utf-8")
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    # Remplace la ligne footer
    lines = content.splitlines()
    new_lines = []
    for line in lines:
        if '<footer>' in line and '</footer>' in line:
            indent = line[: len(line) - len(line.lstrip())]
            new_lines.append(f'{indent}<footer>branch_lee — ML_prediction_project — last push: {now}</footer>')
        else:
            new_lines.append(line)
    index.write_text("\n".join(new_lines), encoding="utf-8")
    print(f"index.html updated: {now}")


def main():
    msg = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else f"auto-push {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

    update_index_timestamp()

    run("git add -A")
    ret = run(f'git commit -m "{msg}"')
    if ret != 0:
        print("Nothing to commit or commit failed.")
    run(f"git push origin {BRANCH}")


if __name__ == "__main__":
    main()
