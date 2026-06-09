import subprocess
import sys
from datetime import datetime

BRANCH = "branch_lee"

def run(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout.strip())
    if result.stderr:
        print(result.stderr.strip())
    return result.returncode

def main():
    msg = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else f"auto-push {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

    run("git add -A")
    ret = run(f'git commit -m "{msg}"')
    if ret != 0:
        print("Nothing to commit or commit failed.")
    run(f"git push origin {BRANCH}")

if __name__ == "__main__":
    main()
