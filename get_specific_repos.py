import os
import time
import random
import requests
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

PATTERN_MAP = {
    "React": [
        "dangerouslySetInnerHTML",
        "__html:",
        "href={`",
        "useSearchParams(",
        "searchParams.get(",
        "getServerSideProps",
        "getStaticProps",
        "use server",
        "<iframe",
    ],
    "Vue": [
        "v-html=",
        "domProps: { innerHTML",
        ":href=",
        "$router.push(",
        "$router.replace(",
        "useRouter().push(",
        "$route.query",
        "useFetch(",
        "$fetch(",
        "useAsyncData(",
        "readBody(",
        "getRouterParam(",
    ],
    "Angular": [
        "bypassSecurityTrustHtml(",
        "bypassSecurityTrustScript(",
        "bypassSecurityTrustUrl(",
        "bypassSecurityTrustResourceUrl(",
        "[innerHTML]=",
        "nativeElement.innerHTML",
        "@HostBinding('innerHTML')",
        "navigateByUrl(",
        "router.navigate(",
        "snapshot.queryParams",
        "snapshot.paramMap.get(",
        "queryParams.subscribe(",
        "headers['host']",
        "headers['x-forwarded-host']",
    ],
    "Svelte": [
        "{@html",
        "$page.url.searchParams",
        "$page.params",
        "$page.url",
    ],
    "General": [
        "innerHTML =",
        "outerHTML =",
        "insertAdjacentHTML(",
        "createContextualFragment(",
        ".srcdoc =",
        ".html(",
        "document.write(",
        "document.writeln(",
        "eval(",
        "new Function(",
        'setTimeout("',
        'setInterval("',
        "javascript:",
        "window.location.href =",
        "window.location.replace(",
        "window.location.assign(",
        "addEventListener('message'",
        'addEventListener("message"',
        "__proto__",
        "constructor.prototype",
        "deepmerge(",
        "_.merge(",
        "_.mergeWith(",
        "_.defaultsDeep(",
        "marked.parse(",
        "marked(",
        "showdown.Converter",
        "markdownit(",
        "rejectUnauthorized: false",
        "NODE_TLS_REJECT_UNAUTHORIZED",
        "localStorage.setItem(",
        "sessionStorage.setItem(",
        "document.cookie =",
        "window.token =",
        "window.authToken =",
        "jwt_decode(",
        "_.template(",
        'target="_blank"',
    ],
}

MIN_STARS = 50
MAX_PAGES = 20
MIN_YEAR = "2023"
PAUSE_BETWEEN_PAGES = (2.0, 4.0)
PAUSE_BETWEEN_PATTERNS = (5.0, 10.0)

FRAMEWORKS_KEYWORDS = {
    "React": ["react", "next", "nextjs", "next.js"],
    "Angular": ["angular"],
    "Vue": ["vue", "vuejs", "nuxt", "nuxtjs"],
    "Svelte": ["svelte", "sveltekit"],
}

OUTPUT_FILE = "repos-specific2.txt"

GITHUB_HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json",
}


def random_pause(interval: tuple):
    delay = random.uniform(*interval)
    time.sleep(delay)


def fetch_from_grep_app():
    print(">>> Starting repository collection from grep.app...")
    repo_to_frameworks = {}

    lang_filters = "&f.lang=JavaScript&f.lang=TypeScript"

    for category, patterns in PATTERN_MAP.items():
        print(f"\n--- Category: {category} ---")

        for pattern in patterns:
            print(f"  Pattern: '{pattern}'")
            found_in_pattern = 0

            for page in range(1, MAX_PAGES + 1):
                url = (
                    f"https://grep.app/api/search"
                    f"?q={requests.utils.quote(pattern)}"
                    f"{lang_filters}"
                    f"&page={page}"
                )

                for attempt in range(3):
                    try:
                        response = requests.get(url, timeout=15)

                        if response.status_code == 429:
                            wait = random.uniform(30, 60) * (attempt + 1)
                            print(f"    [Rate limit] Waiting {wait:.1f}s...")
                            time.sleep(wait)
                            continue

                        response.raise_for_status()
                        data = response.json()
                        break

                    except Exception as e:
                        print(f"    [Error attempt {attempt+1}] {e}")
                        time.sleep(10)
                else:
                    print("    [!] All attempts failed, skipping page")
                    break

                hits = data.get("hits", {}).get("hits", [])
                if not hits:
                    print(f"    Page {page}: empty, moving to next pattern")
                    break

                for hit in hits:
                    repo = hit["repo"]
                    if repo not in repo_to_frameworks:
                        repo_to_frameworks[repo] = set()
                    if category != "General":
                        repo_to_frameworks[repo].add(category)

                found_in_pattern += len(hits)
                print(
                    f"    Page {page}: +{len(hits)} (total for pattern: {found_in_pattern})"
                )
                random_pause(PAUSE_BETWEEN_PAGES)

            random_pause(PAUSE_BETWEEN_PATTERNS)

    print(f"\n>>> Collection complete. Unique repositories: {len(repo_to_frameworks)}")
    return repo_to_frameworks


def determine_framework_fallback(repo_data):
    name = repo_data.get("name", "") or ""
    description = repo_data.get("description", "") or ""
    topics = " ".join(repo_data.get("topics", []))
    search_text = f"{name} {description} {topics}".lower()

    for fw_name, keywords in FRAMEWORKS_KEYWORDS.items():
        for kw in keywords:
            if kw in search_text:
                return fw_name
    return None


def filter_github_repos(repo_to_frameworks):
    print("\n>>> Filtering via GitHub API...")

    categorized_repos = {fw: [] for fw in FRAMEWORKS_KEYWORDS.keys()}

    skipped_stars = 0
    skipped_404 = 0
    added = 0
    total = len(repo_to_frameworks)

    for count, (repo_name, known_fws) in enumerate(repo_to_frameworks.items(), 1):
        url = f"https://api.github.com/repos/{repo_name}"

        for attempt in range(3):
            try:
                response = requests.get(url, headers=GITHUB_HEADERS, timeout=10)

                if response.status_code == 403:
                    remaining = int(response.headers.get("X-RateLimit-Remaining", 0))
                    reset_at = int(response.headers.get("X-RateLimit-Reset", time.time() + 60))
                    wait = max(reset_at - int(time.time()), 0) + 5
                    print(f"\n  [Rate limit] Remaining={remaining}. Waiting {wait}s...")
                    time.sleep(wait)
                    continue

                if response.status_code == 404:
                    skipped_404 += 1
                    break

                response.raise_for_status()
                repo_data = response.json()
                break

            except Exception as e:
                print(f"  [{count}/{total}] Error {repo_name}: {e}")
                time.sleep(5)
        else:
            continue

        if response.status_code == 404:
            continue

        stars = repo_data.get("stargazers_count", 0)
        created_at = repo_data.get("created_at", "")[:4]
        clone_url = repo_data.get("clone_url")

        if stars < MIN_STARS:
            skipped_stars += 1
            continue


        if created_at < MIN_YEAR:
            continue

        final_fws = set(known_fws)

        if not final_fws:
            guessed = determine_framework_fallback(repo_data)
            if guessed:
                final_fws.add(guessed)
            continue

        for fw in final_fws:
            if fw in categorized_repos:
                categorized_repos[fw].append(clone_url)

        added += 1
        print(f"  [{count}/{total}] ✅ {repo_name} | {', '.join(final_fws)} | {stars}⭐ | created {created_at}")

    print(f"\n  Added: {added} | Skipped (stars): {skipped_stars} | 404: {skipped_404}")
    return categorized_repos


def main():
    if not GITHUB_TOKEN:
        print("Error: GITHUB_TOKEN not found in .env file.")
        return

    repo_to_frameworks = fetch_from_grep_app()

    if not repo_to_frameworks:
        print("No repositories found. Exiting.")
        return

    categorized_repos = filter_github_repos(repo_to_frameworks)

    print(f"\n>>> Saving to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for fw_name, urls in categorized_repos.items():
            if urls:
                f.write(f"# {fw_name}\n")
                for url in urls:
                    f.write(f"{url}\n")
                f.write("\n")

    print("\nFinal statistics:")
    total_repos = 0
    for fw_name, urls in categorized_repos.items():
        print(f"  - {fw_name}: {len(urls)} repositories")
        total_repos += len(urls)
    print(f"  Total URLs: {total_repos}")


if __name__ == "__main__":
    main()
