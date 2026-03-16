import subprocess
from pathlib import Path
import sys
import os
from datetime import datetime

REPOS_DIR = Path("repos")
RULES_FILE = Path("rules.yaml")
REPORTS_DIR = Path("reports")

REPORTS_DIR.mkdir(exist_ok=True)

EXCLUDE_DIRS = [
    "node_modules",
    "dist",
    "build",
    "coverage",
    ".next",
    ".nuxt",
    ".output",
    ".git",
]

INCLUDE_PATTERNS = [
    "*.html",
    "*.js",
    "*.ts",
    "*.jsx",
    "*.tsx",
    "*.vue",
    "*.svelte",
]

if not REPOS_DIR.exists():
    print(f"Папка {REPOS_DIR} не найдена.")
    sys.exit(1)

if not RULES_FILE.exists():
    print(f"Файл правил {RULES_FILE} не найден.")
    sys.exit(1)

timestamp = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
output_file = REPORTS_DIR / f"semgrep_{timestamp}.sarif"

print(f"Запуск Semgrep на {REPOS_DIR}")
print(f"Правила: {RULES_FILE}")
print(f"Результат: {output_file}\n")

cmd = [
    "semgrep",
    "scan",
    str(REPOS_DIR),
    "--config", str(RULES_FILE),
    "--sarif",
    f"--sarif-output={output_file}",
    "--max-lines-per-finding", "8",
    "--timeout", "60",
    "--max-target-bytes", "2000000",
    "--jobs", "4",
    "--skip-unknown-extensions",
    "--no-git-ignore",
]

for d in EXCLUDE_DIRS:
    cmd.extend(["--exclude", d])

for p in INCLUDE_PATTERNS:
    cmd.extend(["--include", p])

env = os.environ.copy()
env["PYTHONUTF8"] = "1"

try:
    subprocess.run(cmd, check=True, encoding="utf-8", env=env)
    print("\nСканирование успешно завершено.")

except subprocess.CalledProcessError as e:
    print("\nВо время сканирования возникли ошибки.")
    print(e)
    sys.exit(1)