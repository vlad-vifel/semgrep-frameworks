from pathlib import Path
import sys
import json
from collections import defaultdict

RESET = "\033[0m"
BOLD = "\033[1m"

SCANNERS = ["semgrep", "opengrep", "semgrep-pro"]

OUTPUT_FILE = "scanner-stats.md"

def sarif_count_findings(file_path: Path) -> int:
    if not file_path.exists():
        return 0
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return sum(len(run.get("results", [])) for run in data.get("runs", []))
    except Exception:
        return 0


def sarif_get_rule_ids(file_path: Path) -> list[str]:
    if not file_path.exists():
        return []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        rule_ids = []
        for run in data.get("runs", []):
            for result in run.get("results", []):
                rule_id = result.get("ruleId")
                if rule_id:
                    rule_ids.append(rule_id)
        return rule_ids
    except Exception:
        return []


def print_line(line=""):
    print(line)


def write_md_row(cells: list) -> str:
    return "| " + " | ".join(str(c) for c in cells) + " |"


def write_md_separator(n_cols: int) -> str:
    return "| " + " | ".join(["---"] * n_cols) + " |"


def main():
    if len(sys.argv) < 2:
        print("Usage: python analyzer.py <reports_folder>")
        sys.exit(1)

    reports_dir = Path(sys.argv[1])
    if not reports_dir.exists():
        print("Reports folder not found")
        sys.exit(1)

    repos = [d for d in reports_dir.iterdir() if d.is_dir()]

    total_findings = defaultdict(int)
    repos_with_findings = defaultdict(int)
    unique_findings = defaultdict(int)
    rule_counts = defaultdict(lambda: defaultdict(int))

    for repo in repos:
        counts = {}
        for scanner in SCANNERS:
            sarif_path = repo / f"{scanner}.sarif"
            counts[scanner] = sarif_count_findings(sarif_path)
            for rule_id in sarif_get_rule_ids(sarif_path):
                rule_counts[scanner][rule_id] += 1

        for scanner in SCANNERS:
            total_findings[scanner] += counts[scanner]
            if counts[scanner] > 0:
                repos_with_findings[scanner] += 1

        for scanner in SCANNERS:
            others = [s for s in SCANNERS if s != scanner]
            if counts[scanner] > 0 and all(counts[s] == 0 for s in others):
                unique_findings[scanner] += 1

    summary_file = reports_dir / OUTPUT_FILE
    lines_console = []
    lines_md = []

    def both(console_line="", md_line=None):
        lines_console.append(console_line)
        lines_md.append(md_line if md_line is not None else console_line)

    both(
        f"{BOLD}TOTAL FINDINGS & REPOSITORIES WITH FINDINGS{RESET}",
        "## Total findings & Repositories with findings",
    )
    both("-" * 60, "")
    both(
        f"{'Scanner':<16} {'Repositories with findings':>20} {'Total findings':>16}",
        write_md_row(["Scanner", "Repositories with findings", "Total findings"]),
    )
    both("-" * 60, write_md_separator(3))
    for scanner in SCANNERS:
        repos_found = repos_with_findings[scanner]
        findings = total_findings[scanner]
        both(
            f"{scanner:<16} {repos_found:>20} {findings:>16}",
            write_md_row([scanner, repos_found, findings]),
        )
    both("", "")

    both(
        f"{BOLD}UNIQUE FINDINGS (only this scanner found, others found nothing){RESET}",
        "## Unique Findings",
    )
    both("-" * 60, "")
    both(
        f"{'Scanner':<16} {'Unique Repositories':>12}",
        write_md_row(["Scanner", "Unique Repositories"]),
    )
    both("-" * 60, write_md_separator(2))
    for scanner in SCANNERS:
        both(
            f"{scanner:<16} {unique_findings[scanner]:>12}",
            write_md_row([scanner, unique_findings[scanner]]),
        )
    both("", "")

    both(f"{BOLD}FINDINGS BY RULE ID{RESET}", "## Findings by Rule ID")
    both("-" * 60, "")

    all_rules = sorted(
        set(rule_id for scanner in SCANNERS for rule_id in rule_counts[scanner])
    )

    if not all_rules:
        both("No rule data found.")
    else:
        both(
            f"{'Rule ID':<50}" + "".join(f"{s:>16}" for s in SCANNERS),
            write_md_row(["Rule ID"] + SCANNERS),
        )
        both("-" * (50 + 16 * len(SCANNERS)), write_md_separator(1 + len(SCANNERS)))
        for rule_id in all_rules:
            counts_row = [rule_counts[scanner].get(rule_id, 0) for scanner in SCANNERS]
            both(
                f"{rule_id:<50}" + "".join(f"{c:>16}" for c in counts_row),
                write_md_row([rule_id] + counts_row),
            )
        totals = [total_findings[scanner] for scanner in SCANNERS]
        both(
            f"{'TOTAL':<50}" + "".join(f"{t:>16}" for t in totals),
            write_md_row(["**TOTAL**"] + [f"**{t}**" for t in totals]),
        )

    both("", "")
    both("=" * 60, "---")

    for line in lines_console:
        print(line)

    with open(summary_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines_md) + "\n")

    print(f"\n💾 Summary saved: {summary_file}")


if __name__ == "__main__":
    main()
