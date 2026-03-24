import subprocess
from pathlib import Path
import sys
import os
import time
from datetime import datetime
import json

REPOS_DIR = Path("repos-specific")
RULES_FILE = Path("rules.yaml")
REPORTS_BASE_DIR = Path("reports")

EXCLUDE_DIRS = [
    "node_modules",
    "dist",
    "build",
    "coverage",
    ".next",
    ".nuxt",
    ".output",
    ".git",
    "vendor",
    "__pycache__",
    "*.min.js",
]

INCLUDE_PATTERNS = ["*.html", "*.js", "*.ts", "*.jsx", "*.tsx", "*.vue", "*.svelte"]

RESET  = "\033[0m"
BOLD   = "\033[1m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
CYAN   = "\033[96m"


def format_time(seconds):
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m}m {s}s" if m > 0 else f"{s}s"


def run_scanner(cmd, env):
    start = time.perf_counter()
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            env=env,
            timeout=300,
        )
    except subprocess.TimeoutExpired:
        print(f"    ⏰ timeout")
        return "ERROR", "", time.perf_counter() - start
    except Exception as e:
        print(f"    ❌ Exception: {e}")
        return "ERROR", "", 0

    elapsed = time.perf_counter() - start

    if result.returncode in (0, 1):
        return "OK", result.stdout, elapsed
    else:
        return "ERROR", "", elapsed


def sarif_count_findings(file_path: Path) -> int:
    if not file_path.exists():
        return 0
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return sum(len(run.get("results", [])) for run in data.get("runs", []))
    except Exception:
        return 0


def find_last_scanned(session_dir: Path, repos: list) -> int:
    scanned_names = {p.name for p in session_dir.iterdir() if p.is_dir()}

    last_index = -1
    for i, repo in enumerate(repos):
        if repo.name in scanned_names:
            last_index = i

    return last_index + 1


def main():
    args = sys.argv[1:]
    valid_modes = ["--all", "--semgrep", "--semgrep-pro", "--opengrep"]

    mode = "all"
    session_name = None

    for arg in args:
        if arg in valid_modes:
            mode = arg
        elif not arg.startswith("--"):
            session_name = arg
        else:
            print(f"Invalid flag. Use one of: {', '.join(valid_modes)} [session_name]")
            sys.exit(1)

    mode = mode.replace("--", "")

    if not REPOS_DIR.exists():
        print("Repositories folder not found")
        sys.exit(1)

    if not RULES_FILE.exists():
        print("Rules file not found")
        sys.exit(1)

    if session_name:
        session_dir = REPORTS_BASE_DIR / session_name
        if not session_dir.exists():
            print(f"{RED}Session '{session_name}' not found in {REPORTS_BASE_DIR}{RESET}")
            sys.exit(1)
    else:
        timestamp = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
        session_dir = REPORTS_BASE_DIR / timestamp
        session_dir.mkdir(parents=True, exist_ok=True)

    repos = [d for d in REPOS_DIR.iterdir() if d.is_dir()]
    total = len(repos)

    start_from = find_last_scanned(session_dir, repos) if session_name else 0

    print(f"{CYAN}Scanning {total} repositories...{RESET}")
    print(f"Mode: {mode}")
    print(f"Reports: {session_dir}")
    if session_name and start_from > 0:
        if start_from < total:
            print(f"Resuming from [{start_from + 1}/{total}] {repos[start_from].name}")
        else:
            print(f"{GREEN}All {total} repositories already scanned.{RESET}")
            return
    print()

    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"

    base_flags = [
        "--config", str(RULES_FILE),
        "--timeout", "180",
        "--jobs", "1",
        "--no-git-ignore",
    ]

    for d in EXCLUDE_DIRS:
        base_flags.extend(["--exclude", d])
    for p in INCLUDE_PATTERNS:
        base_flags.extend(["--include", p])

    for i, repo in enumerate(repos, 1):
        if i - 1 < start_from:
            continue

        print(f"{BOLD}[{i}/{total}] {repo.name}{RESET}")
        if mode == "all":
            print("-" * 50)

        repo_dir = session_dir / repo.name
        repo_dir.mkdir(exist_ok=True)

        scanners = []

        if mode in ["all", "semgrep"]:
            scanners.append({
                "name": "semgrep",
                "cmd": ["semgrep", "scan"] + base_flags,
                "out": repo_dir / "semgrep.sarif",
            })

        if mode in ["all", "opengrep"]:
            scanners.append({
                "name": "opengrep",
                "cmd": ["opengrep"] + base_flags,
                "out": repo_dir / "opengrep.sarif",
            })

        if mode in ["all", "semgrep-pro"]:
            scanners.append({
                "name": "semgrep-pro",
                "cmd": ["semgrep", "scan", "--pro-intrafile"] + base_flags,
                "out": repo_dir / "semgrep-pro.sarif",
            })

        total_start = time.perf_counter()
        has_findings = False

        for s in scanners:
            sys.stdout.write(f"  🔍 {s['name']:<12} ... ")
            sys.stdout.flush()

            cmd = s["cmd"] + ["--sarif", "-o", str(s["out"]), str(repo)]
            status, _, t = run_scanner(cmd, env)

            if status == "ERROR":
                print(f"{RED}❌ error{RESET} ({format_time(t)})")
                continue

            count = sarif_count_findings(s["out"])

            if count > 0:
                print(f"{YELLOW}⚠️  {count} finding{'' if count == 1 else 's'}{RESET} ({format_time(t)})")
                has_findings = True
            else:
                print(f"{GREEN}✅ clean{RESET} ({format_time(t)})")
                if s["out"].exists():
                    s["out"].unlink()

        if not has_findings:
            try:
                repo_dir.rmdir()
            except Exception:
                pass

        total_time = time.perf_counter() - total_start

        if mode == "all":
            if has_findings:
                print(f"  📊 findings detected")
            else:
                print(f"  ✅ clean repository")
            print(f"  🕒 Total scan time: {format_time(total_time)}")
            print("-" * 50)

        print("")

    print("Scanning completed successfully")


if __name__ == "__main__":
    main()