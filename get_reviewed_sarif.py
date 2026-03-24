import sys
import json
from pathlib import Path

if len(sys.argv) < 2:
    print("Usage: python filter_sarif.py <sarif_file>")
    sys.exit(1)

sarif_path = Path(sys.argv[1])
explorer_path = Path(str(sarif_path) + ".sarifexplorer")

if not sarif_path.exists():
    print(f"File not found: {sarif_path}")
    sys.exit(1)

if not explorer_path.exists():
    print(f"Explorer file not found: {explorer_path}")
    sys.exit(1)

with open(sarif_path, "r", encoding="utf-8") as f:
    sarif_data = json.load(f)

with open(explorer_path, "r", encoding="utf-8") as f:
    explorer_data = json.load(f)

result_id_to_notes = explorer_data.get("resultIdToNotes", {})

total_findings = 0
unmarked = []

for run_idx, run in enumerate(sarif_data.get("runs", [])):
    for result_idx, _ in enumerate(run.get("results", [])):
        total_findings += 1
        key = f"{run_idx}|{result_idx}"
        if key not in result_id_to_notes:
            unmarked.append(key)

if unmarked:
    print(f"The following findings are not marked ({len(unmarked)} total):")
    for key in unmarked:
        print(f"  [{key}]")
    print("\nPlease mark all findings before filtering. Exiting.")
    sys.exit(1)

filtered_runs = []
fp_count = 0
tp_count = 0

for run_idx, run in enumerate(sarif_data.get("runs", [])):
    filtered_results = []
    for result_idx, result in enumerate(run.get("results", [])):
        key = f"{run_idx}|{result_idx}"
        status = result_id_to_notes[key].get("status")
        if status == 2:
            filtered_results.append(result)
            tp_count += 1
        elif status == 1:
            fp_count += 1

    filtered_run = dict(run)
    filtered_run["results"] = filtered_results
    filtered_runs.append(filtered_run)

filtered_sarif = dict(sarif_data)
filtered_sarif["runs"] = filtered_runs

output_path = sarif_path.with_stem(sarif_path.stem + "-reviewed")
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(filtered_sarif, f, ensure_ascii=False, indent=2)

print(f"Total findings : {total_findings}")
print(f"False positives: {fp_count} (removed)")
print(f"True positives : {tp_count} (kept)")
print(f"Output         : {output_path}")