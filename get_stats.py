import sys
import json
import re
from pathlib import Path
from collections import defaultdict

REPOS_DIR  = Path("repos-specific")
RULES_FILE = Path("rules.yaml")

FRAMEWORKS  = ["React", "Angular", "Vue", "Svelte"]
OUTPUT_FILE = "stats.md"


def parse_rules_yaml(path: Path) -> dict:
    categories = {}
    current_category = None
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    for line in lines:
        cat_match = re.search(r'#\s+(\d+)\.', line)
        if cat_match:
            num = cat_match.group(1)
            current_category = f"Category {num}"
            if current_category not in categories:
                categories[current_category] = []
        id_match = re.match(r'\s+- id:\s+(\S+)', line)
        if id_match and current_category:
            categories[current_category].append(id_match.group(1))
    return categories


def extract_framework(repo_name: str) -> str:
    match = re.search(r'\[(\w+)\]', repo_name)
    if match:
        name = match.group(1).capitalize()
        return name if name in FRAMEWORKS else "Other"
    return "Other"


def get_repo_name_from_uri(uri: str) -> str:
    for part in uri.replace("\\", "/").split("/"):
        for fw in FRAMEWORKS:
            if f"[{fw}]" in part:
                return part
    return ""


def write_md_row(cells: list) -> str:
    return "| " + " | ".join(str(c) for c in cells) + " |"


def write_md_separator(n_cols: int) -> str:
    return "| " + " | ".join(["---"] * n_cols) + " |"


def both(lines_console, lines_md, console_line="", md_line=None):
    lines_console.append(console_line)
    lines_md.append(md_line if md_line is not None else console_line)


def make_table_both(lines_console, lines_md, headers, rows, col_width=26):
    header_line = "".join(str(h).ljust(col_width) for h in headers)
    separator   = "-" * (col_width * len(headers))
    both(lines_console, lines_md, header_line, write_md_row(headers))
    both(lines_console, lines_md, separator,   write_md_separator(len(headers)))
    for row in rows:
        console_row = "".join(str(cell).ljust(col_width) for cell in row)
        both(lines_console, lines_md, console_row, write_md_row(row))
    both(lines_console, lines_md, separator, "")


def main():
    if len(sys.argv) < 2:
        print("Usage: python stats.py <sarif_file>")
        sys.exit(1)

    sarif_path = Path(sys.argv[1])
    if not sarif_path.exists():
        print(f"File not found: {sarif_path}")
        sys.exit(1)

    if not RULES_FILE.exists():
        print(f"Rules file not found: {RULES_FILE}")
        sys.exit(1)

    CATEGORIES       = parse_rules_yaml(RULES_FILE)
    RULE_TO_CATEGORY = {
        rule_id: category
        for category, rules in CATEGORIES.items()
        for rule_id in rules
    }

    fw_prefixes = {fw: fw.lower() + "-" for fw in FRAMEWORKS}
    rules_per_fw        = defaultdict(int)
    general_rules_count = 0
    for rule_id in RULE_TO_CATEGORY:
        matched = False
        for fw, prefix in fw_prefixes.items():
            if rule_id.startswith(prefix):
                rules_per_fw[fw] += 1
                matched = True
                break
        if not matched:
            general_rules_count += 1

    with open(sarif_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    output_path = sarif_path.parent / OUTPUT_FILE

    repos_by_framework = defaultdict(int)
    total_repos = 0
    if REPOS_DIR.exists():
        for d in REPOS_DIR.iterdir():
            if d.is_dir():
                total_repos += 1
                repos_by_framework[extract_framework(d.name)] += 1

    all_findings = []
    for run in data.get("runs", []):
        for result in run.get("results", []):
            rule_id   = result.get("ruleId", "unknown")
            uri       = ""
            locations = result.get("locations", [])
            if locations:
                uri = (
                    locations[0]
                    .get("physicalLocation", {})
                    .get("artifactLocation", {})
                    .get("uri", "")
                )
            repo_name = get_repo_name_from_uri(uri)
            all_findings.append({
                "rule_id":   rule_id,
                "framework": extract_framework(repo_name),
                "repo_name": repo_name,
                "category":  RULE_TO_CATEGORY.get(rule_id, "Unknown"),
            })

    total_findings_count       = len(all_findings)
    findings_per_category      = defaultdict(int)
    unique_rules_per_category  = defaultdict(set)
    repos_by_cat               = defaultdict(set)
    findings_per_framework     = defaultdict(int)
    unique_rules_per_framework = defaultdict(set)
    repos_with_findings_by_fw  = defaultdict(set)
    unique_rules_fw_cat        = defaultdict(lambda: defaultdict(set))
    total_fw_cat               = defaultdict(lambda: defaultdict(int))
    repos_with_findings        = set()

    for fi in all_findings:
        cat = fi["category"]
        fw  = fi["framework"]
        rn  = fi["repo_name"]
        rid = fi["rule_id"]

        findings_per_category[cat]    += 1
        unique_rules_per_category[cat].add(rid)
        if rn:
            repos_by_cat[cat].add(rn)

        findings_per_framework[fw]    += 1
        unique_rules_per_framework[fw].add(rid)
        if rn:
            repos_with_findings_by_fw[fw].add(rn)
            repos_with_findings.add(rn)

        unique_rules_fw_cat[fw][cat].add(rid)
        total_fw_cat[fw][cat]         += 1

    all_rule_ids = set(fi["rule_id"] for fi in all_findings)

    lines_console = []
    lines_md      = []

    def b(console_line="", md_line=None):
        both(lines_console, lines_md, console_line, md_line)

    def table(headers, rows, col_width=26):
        make_table_both(lines_console, lines_md, headers, rows, col_width)

    # Header
    b("=" * 80, f"# SARIF Statistics: {sarif_path.name}")
    b(f"SARIF STATISTICS: {sarif_path.name}", "")
    b(f"Total findings     : {total_findings_count}", f"**Total findings:** {total_findings_count}")
    b(f"Total repositories : {total_repos}",          f"**Total repositories:** {total_repos}")
    b("=" * 80, "")

    # [0a] Rules per framework
    b("", "")
    b("[0a] RULES PER FRAMEWORK", "## [0a] Rules per Framework")
    b("", "")
    headers_0a = ["Metric", "General"] + FRAMEWORKS
    rows_0a = [(
        "Number of rules",
        general_rules_count,
        *[rules_per_fw.get(fw, 0) for fw in FRAMEWORKS],
    )]
    table(headers_0a, rows_0a, col_width=20)

    # [0b] Repositories per framework
    b("", "")
    b("[0b] REPOSITORIES PER FRAMEWORK", "## [0b] Repositories per Framework")
    b("", "")
    headers_0b = ["Metric"] + FRAMEWORKS + ["Total"]
    rows_0b = [(
        "Number of repositories",
        *[repos_by_framework.get(fw, 0) for fw in FRAMEWORKS],
        total_repos,
    )]
    table(headers_0b, rows_0b, col_width=24)

    # [1] Findings per category
    b("", "")
    b("[1] FINDINGS PER CATEGORY", "## [1] Findings per Category")
    b("", "")
    rows = [
        (cat,
         findings_per_category.get(cat, 0),
         len(unique_rules_per_category.get(cat, set())),
         len(repos_by_cat.get(cat, set())))
        for cat in CATEGORIES
    ]
    rows.append(("TOTAL", total_findings_count, len(all_rule_ids), len(repos_with_findings)))
    table(["Category", "Total findings", "Unique rules", "Repositories affected"], rows)

    # [2] Findings per framework
    b("", "")
    b("[2] FINDINGS PER FRAMEWORK", "## [2] Findings per Framework")
    b("", "")
    headers_2 = ["Metric"] + FRAMEWORKS + ["Total"]
    rows_2 = [
        (
            "Total findings",
            *[findings_per_framework.get(fw, 0) for fw in FRAMEWORKS],
            total_findings_count,
        ),
        (
            "Unique rules",
            *[len(unique_rules_per_framework.get(fw, set())) for fw in FRAMEWORKS],
            len(all_rule_ids),
        ),
        (
            "Repositories with findings",
            *[len(repos_with_findings_by_fw.get(fw, set())) for fw in FRAMEWORKS],
            len(repos_with_findings),
        ),
        (
            "Total repositories",
            *[repos_by_framework.get(fw, 0) for fw in FRAMEWORKS],
            total_repos,
        ),
    ]
    table(headers_2, rows_2, col_width=28)

    # [3a] Framework x Category — unique rules
    b("", "")
    b("[3a] FRAMEWORK x CATEGORY — UNIQUE RULES TRIGGERED", "## [3a] Framework × Category — Unique Rules Triggered")
    b("", "")
    cat_names = list(CATEGORIES.keys())
    headers_3 = ["Category"] + FRAMEWORKS + ["Total"]
    col_w_3   = 28

    console_header_3 = "".join(str(h).ljust(col_w_3) for h in headers_3)
    separator_3      = "-" * (col_w_3 * len(headers_3))
    both(lines_console, lines_md, console_header_3, write_md_row(headers_3))
    both(lines_console, lines_md, separator_3,      write_md_separator(len(headers_3)))

    for cat in cat_names:
        md_cells    = [cat]
        console_row = cat.ljust(col_w_3)
        row_total   = 0
        for fw in FRAMEWORKS:
            val = len(unique_rules_fw_cat[fw][cat])
            row_total += val
            console_row += str(val).ljust(col_w_3)
            md_cells.append(val)
        console_row += str(row_total).ljust(col_w_3)
        md_cells.append(row_total)
        b(console_row, write_md_row(md_cells))

    console_total = "TOTAL".ljust(col_w_3)
    md_cells      = ["**TOTAL**"]
    grand_total   = 0
    for fw in FRAMEWORKS:
        val = len(set(rid for cat in cat_names for rid in unique_rules_fw_cat[fw][cat]))
        grand_total += val
        console_total += str(val).ljust(col_w_3)
        md_cells.append(val)
    console_total += str(grand_total).ljust(col_w_3)
    md_cells.append(grand_total)
    b(console_total, write_md_row(md_cells))
    b(separator_3, "")

    # [3b] Framework x Category — total findings
    b("", "")
    b("[3b] FRAMEWORK x CATEGORY — TOTAL FINDINGS", "## [3b] Framework × Category — Total Findings")
    b("", "")
    both(lines_console, lines_md, console_header_3, write_md_row(headers_3))
    both(lines_console, lines_md, separator_3,      write_md_separator(len(headers_3)))

    for cat in cat_names:
        md_cells    = [cat]
        console_row = cat.ljust(col_w_3)
        row_total   = 0
        for fw in FRAMEWORKS:
            val = total_fw_cat[fw][cat]
            row_total += val
            console_row += str(val).ljust(col_w_3)
            md_cells.append(val)
        console_row += str(row_total).ljust(col_w_3)
        md_cells.append(row_total)
        b(console_row, write_md_row(md_cells))

    console_total = "TOTAL".ljust(col_w_3)
    md_cells      = ["**TOTAL**"]
    grand_total   = 0
    for fw in FRAMEWORKS:
        val = sum(total_fw_cat[fw][cat] for cat in cat_names)
        grand_total += val
        console_total += str(val).ljust(col_w_3)
        md_cells.append(val)
    console_total += str(grand_total).ljust(col_w_3)
    md_cells.append(grand_total)
    b(console_total, write_md_row(md_cells))
    b(separator_3, "")

    # [4] Repositories with findings
    b("", "")
    b("[4] REPOSITORIES WITH FINDINGS", "## [4] Repositories with Findings")
    b("", "")
    headers_4 = ["Metric"] + FRAMEWORKS + ["Total"]
    rw_total  = len(repos_with_findings)
    cov_total = f"{rw_total / total_repos * 100:.1f}%" if total_repos > 0 else "0%"
    rows_4 = [
        (
            "Repositories with findings",
            *[len(repos_with_findings_by_fw.get(fw, set())) for fw in FRAMEWORKS],
            rw_total,
        ),
        (
            "Total repositories",
            *[repos_by_framework.get(fw, 0) for fw in FRAMEWORKS],
            total_repos,
        ),
        (
            "Coverage",
            *[
                f"{len(repos_with_findings_by_fw.get(fw, set())) / repos_by_framework[fw] * 100:.1f}%"
                if repos_by_framework.get(fw, 0) > 0 else "0%"
                for fw in FRAMEWORKS
            ],
            cov_total,
        ),
    ]
    table(headers_4, rows_4, col_width=28)

    # [5] Repositories with findings per category
    b("", "")
    b("[5] REPOSITORIES WITH FINDINGS PER CATEGORY", "## [5] Repositories with Findings per Category")
    b("", "")
    rows_5 = []
    for cat in CATEGORIES:
        rw  = len(repos_by_cat.get(cat, set()))
        cov = f"{rw / total_repos * 100:.1f}%" if total_repos > 0 else "0%"
        rows_5.append((cat, rw, total_repos, cov))
    table(["Category", "Repositories affected", "Total repositories", "Coverage"], rows_5)

    b("", "")
    b("=" * 80, "---")

    for line in lines_console:
        print(line)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines_md) + "\n")

    print(f"\nStats saved: {output_path}")


if __name__ == "__main__":
    main()