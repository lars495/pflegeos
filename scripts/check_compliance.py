"""Compliance-Check: prüft legal_requirements.yaml gegen Codebase.

Heutiger Stand: Stub. Erste echte Implementierung kommt mit Phase 1.
Verhalten:
  - Liest legal_requirements.yaml
  - Für jedes Requirement mit `implemented_in`-Einträgen: prüft Datei-Existenz
  - Loggt kritische Gaps; exit 1 nur bei Severity=critical und Status=gap
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
REQS = ROOT / "legal_requirements.yaml"


def main() -> int:
    data = yaml.safe_load(REQS.read_text())
    critical_gaps: list[str] = []
    missing_files: list[str] = []

    for req in data.get("requirements", []):
        rid = req.get("id", "?")
        sev = req.get("severity", "medium")
        status = req.get("status", "gap")

        if status == "gap" and sev == "critical":
            critical_gaps.append(f"{rid} ({req.get('title', '')})")

        for f in req.get("implemented_in", []):
            if not (ROOT / f).exists():
                missing_files.append(f"{rid} → {f}")

    print(f"[compliance] {len(data.get('requirements', []))} requirements geprüft")

    if critical_gaps:
        print("[compliance] KRITISCHE Lücken (akzeptiert in Phase 0):")
        for g in critical_gaps:
            print(f"  - {g}")
        # In Phase 0 noch nicht fatal — die Roadmap arbeitet sich da hin.
        # Sobald PRINCIPLES.md-konforme Implementierungen existieren, hier auf exit 1 schalten.

    if missing_files:
        print("[compliance] Files in implemented_in fehlen:")
        for m in missing_files:
            print(f"  - {m}")
        return 1

    print("[compliance] ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
