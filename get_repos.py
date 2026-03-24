import os
import requests
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

MIN_STARS = 500
MAX_STARS = 5000

FRAMEWORKS = ["Angular", "React", "Vue", "Svelte"]
YEAR_START = 2025
YEAR_END = 2026 
REPOS_PER_FRAMEWORK = 50

HEADERS = {"Authorization": f"token {GITHUB_TOKEN}"}

def fetch_repos(framework, min_stars=MIN_STARS, max_stars=MAX_STARS, per_page=50):
    query = (
        f"{framework} in:name,description,readme "
        f"stars:{min_stars}..{max_stars} "
        f"created:{YEAR_START}-01-01..{YEAR_END}-12-31"
    )
    url = "https://api.github.com/search/repositories"
    params = {"q": query, "sort": "stars", "order": "desc", "per_page": per_page}
    response = requests.get(url, headers=HEADERS, params=params)
    response.raise_for_status()
    return response.json().get("items", [])

def main():
    with open("repos.txt", "w") as f:
        for fw in FRAMEWORKS:
            f.write(f"# {fw}\n")
            repos = fetch_repos(fw, per_page=REPOS_PER_FRAMEWORK)
            for repo in repos:
                f.write(repo["clone_url"] + "\n")

    print("Script is finished")

if __name__ == "__main__":
    main()