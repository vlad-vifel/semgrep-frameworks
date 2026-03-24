import subprocess
import shutil
from pathlib import Path

REPOS_FILE = "repos-specific2.txt"
DEST_DIR = Path("D:/vkr/repos-specific")

DIRS_TO_REMOVE = [
    ".git", "node_modules", ".yarn", "dist", "build",
    ".next", ".nuxt", ".output", "coverage", ".cache",
    ".parcel-cache", "storybook-static", ".storybook", "__pycache__",
]

EXTENSIONS_TO_REMOVE = [
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".webp", ".avif",
    ".woff", ".woff2", ".ttf", ".eot", ".otf",
    ".mp4", ".mp3", ".wav", ".ogg", ".webm",
    ".zip", ".tar", ".gz", ".rar",
    ".pdf", ".docx", ".xlsx",
    ".map", ".min.js", ".min.css", ".lock",
]

RESET  = "\033[0m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
RED    = "\033[91m"

MAX_RETRIES = 3


def format_size(size_bytes):
    if size_bytes < 1024:
        return f"{size_bytes}B"
    elif size_bytes < 1024 ** 2:
        return f"{size_bytes / 1024:.1f}KB"
    elif size_bytes < 1024 ** 3:
        return f"{size_bytes / 1024 ** 2:.1f}MB"
    else:
        return f"{size_bytes / 1024 ** 3:.2f}GB"


def dir_size(path: Path) -> int:
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


def cleanup_repo(dest_path: Path):
    for dir_name in DIRS_TO_REMOVE:
        for match in dest_path.rglob(dir_name):
            if match.is_dir():
                shutil.rmtree(match, ignore_errors=True)
    for ext in EXTENSIONS_TO_REMOVE:
        for match in dest_path.rglob(f"*{ext}"):
            if match.is_file():
                match.unlink(missing_ok=True)


def clone_repos():
    DEST_DIR.mkdir(exist_ok=True)

    tasks = []
    current_framework = ""
    with open(REPOS_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.startswith("#"):
                current_framework = line[1:].strip()
                continue
            repo_url  = line
            repo_name = repo_url.rstrip("/").removesuffix(".git").split("/")[-1]
            tasks.append({
                "repo_url":  repo_url,
                "dest_path": DEST_DIR / f"{repo_name} [{current_framework}]",
                "label":     f"{repo_name} [{current_framework}]",
            })

    total = len(tasks)
    print(f"{CYAN}Total repositories: {total}{RESET}\n")

    for i, task in enumerate(tasks, 1):
        repo_url  = task["repo_url"]
        dest_path = task["dest_path"]
        label     = task["label"]

        if dest_path.exists():
            print(f"{GREEN}[{i}/{total}] Skip: {label}{RESET}")
            continue

        print(f"{YELLOW}[{i}/{total}] Clone: {label}{RESET}")

        for attempt in range(1, MAX_RETRIES + 1):
            result = subprocess.run(
                ["git", "clone", "-c", "core.longpaths=true", "--depth=1",
                 repo_url, str(dest_path)],
            )
            if result.returncode == 0:
                break
            print(f"  {RED}❌ Clone error (attempt {attempt}/{MAX_RETRIES}){RESET}")
            if dest_path.exists():
                shutil.rmtree(dest_path, ignore_errors=True)
        else:
            print(f"  {RED}💀 Skip {label} after {MAX_RETRIES} attempts{RESET}")
            continue

        size_before = dir_size(dest_path)
        cleanup_repo(dest_path)
        size_after = dir_size(dest_path)

        print(f"{CYAN}✅ {format_size(size_before)} → {format_size(size_after)} (−{format_size(size_before - size_after)}){RESET}")


if __name__ == "__main__":
    clone_repos()