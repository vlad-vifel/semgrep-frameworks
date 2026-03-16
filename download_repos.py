import subprocess
from pathlib import Path

REPOS_FILE = "repos.txt"
DEST_DIR = Path("repos")

DEST_DIR.mkdir(exist_ok=True)

def clone_repos():
    current_framework = ""
    with open(REPOS_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.startswith("#"):
                current_framework = line[1:].strip()
                continue
            repo_url = line
            repo_name = repo_url.rstrip(".git").split("/")[-1]
            folder_name = f"{repo_name} [{current_framework}]"
            dest_path = DEST_DIR / folder_name
            if dest_path.exists():
                print(f"Пропуск {folder_name}, уже существует")
                continue
            print(f"Клонируем {repo_url} -> {dest_path}")
            subprocess.run(["git", "clone", repo_url, str(dest_path)], check=True)

if __name__ == "__main__":
    clone_repos()