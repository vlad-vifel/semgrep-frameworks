import os
import sys
import json

VALID_FLAGS = ["--semgrep", "--semgrep-pro", "--opengrep", "--all"]

FLAG_TO_FILENAME = {
    "--semgrep": "semgrep.sarif",
    "--semgrep-pro": "semgrep-pro.sarif",
    "--opengrep": "opengrep.sarif",
    "--all": None,
}

if len(sys.argv) < 3:
    print(f"Usage: python merge_sarif.py <reports_folder> <flag>")
    print(f"Flags: {', '.join(VALID_FLAGS)}")
    sys.exit(1)

reports_folder = sys.argv[1]
flag = sys.argv[2]

if not os.path.isdir(reports_folder):
    print(f"Folder {reports_folder} not found")
    sys.exit(1)

if flag not in VALID_FLAGS:
    print(f"Invalid flag '{flag}'. Available: {', '.join(VALID_FLAGS)}")
    sys.exit(1)

target_filename = FLAG_TO_FILENAME[flag]

sarif_files = []
for root, dirs, files in os.walk(reports_folder):
    for f in files:
        if not f.lower().endswith(".sarif"):
            continue
        if f.startswith("final-"):
            continue
        if target_filename is None or f == target_filename:
            sarif_files.append(os.path.join(root, f))

if not sarif_files:
    print(f"No matching .sarif files found for flag {flag}")
    sys.exit(0)

print(f"Flag: {flag}")
print(f"Found {len(sarif_files)} files, merging...\n")

merged_results = []
merged_rules = []
seen_rule_ids = set()

for path in sarif_files:
    print(f"  Loading {path}")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for run in data.get("runs", []):
            merged_results.extend(run.get("results", []))
            for rule in run.get("tool", {}).get("driver", {}).get("rules", []):
                if rule.get("id") not in seen_rule_ids:
                    seen_rule_ids.add(rule.get("id"))
                    merged_rules.append(rule)
    except Exception as e:
        print(f"  Warning: failed to read {path}: {e}")

scanner_name = flag.replace("--", "")

merged_sarif = {
    "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
    "version": "2.1.0",
    "runs": [
        {
            "tool": {
                "driver": {
                    "name": scanner_name,
                    "rules": merged_rules,
                }
            },
            "results": merged_results,
        }
    ],
}

output_path = os.path.join(reports_folder, f"final-{scanner_name}.sarif")

with open(output_path, "w", encoding="utf-8") as out:
    json.dump(merged_sarif, out, ensure_ascii=False, indent=2)

print(f"\nDone! {len(merged_results)} findings across {len(sarif_files)} files")
print(f"Output: {output_path}")