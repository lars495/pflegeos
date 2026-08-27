import re
from datetime import datetime
import json
from pathlib import Path

def export_roadmap(
    roadmap_path: str = "ROADMAP.md",
    out_path: str = "apps/public-site/roadmap-status.json",
) -> dict:
    ROOT = Path(__file__).resolve().parents[1]
    roadmap_file = ROOT / roadmap_path
    out_file = ROOT / out_path

    with open(roadmap_file, "r", encoding="utf-8") as f:
        content = f.read()

    phase_re = re.compile(r"## Phase (.*)")
    row_re = re.compile(r"^\|\s*([⏳🔨✅⛔❌])\s*\|\s*(.+?)\s*\|.*\*\*(\d+)\*\*")

    phases = []
    current_phase = None

    for line in content.splitlines():
        phase_match = phase_re.match(line)
        if phase_match:
            current_phase = {"name": phase_match.group(1), "items": []}
            phases.append(current_phase)
            continue

        row_match = row_re.match(line)
        if row_match and current_phase:
            current_phase["items"].append({
                "status": row_match.group(1),
                "title": row_match.group(2),
                "score": int(row_match.group(3))
            })

    result = {
        "generated_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "phases": phases
    }

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    return result

if __name__ == "__main__":
    export_roadmap()
