from __future__ import annotations

import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parent
results_path = ROOT / "visual-results.json"
summary_path = os.getenv("GITHUB_STEP_SUMMARY")

lines = ["## Visual regression summary", ""]
if results_path.exists():
    results = json.loads(results_path.read_text(encoding="utf-8"))
    lines.extend(["| Snapshot | Result | Pixels changed |", "|---|---:|---:|"])
    for result in results:
        status = "✅ Pass" if result["passed"] else "❌ Fail"
        lines.append(f"| `{result['name']}` | {status} | {result['diff_percent']:.4f}% |")
else:
    lines.append("No result file was produced; inspect the pytest log.")

output = "\n".join(lines) + "\n"
print(output)
if summary_path:
    with Path(summary_path).open("a", encoding="utf-8") as summary:
        summary.write(output)

