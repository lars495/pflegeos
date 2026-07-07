---
id: T010
title: Roadmap-Export als JSON für die Website
roadmap_item: Public Roadmap-Tracker (autogeneriert)
depends_on: []
target_files:
  - scripts/roadmap_export.py
context_files:
  - ROADMAP.md
  - tests/task_tests/test_t010_roadmap_export.py
test_command: pytest -q tests/task_tests/test_t010_roadmap_export.py
max_attempts: 3
attempts_used: 0
---

Neue Datei `scripts/roadmap_export.py`: parst ROADMAP.md und schreibt
maschinenlesbares JSON für die öffentliche Website.

Pflicht-Signatur:
```python
def export_roadmap(
    roadmap_path: str = "ROADMAP.md",
    out_path: str = "apps/public-site/roadmap-status.json",
) -> dict:
```

Parsing: Phasen-Überschriften matchen `## Phase ...`; Tabellenzeilen haben
das Format `| ⏳ | Titel | 5 | 1 | 3 | 1 | 2 | **21** |` (Status-Emoji,
Titel, 5 Zahlen, Score fett). Regex-Vorschlag:
```python
row_re = re.compile(r"^\|\s*([⏳🔨✅⛔❌])\s*\|\s*(.+?)\s*\|.*\*\*(\d+)\*\*")
```

Rückgabe-Struktur (auch als JSON in out_path schreiben, ensure_ascii=False, indent=2):
```json
{
  "generated_at": "2026-07-07T12:00:00Z",
  "phases": [
    {"name": "Phase 1 — Fundament (Wochen 1–4)",
     "items": [{"status": "⏳", "title": "…", "score": 21}]}
  ]
}
```

Am Ende: `if __name__ == "__main__": export_roadmap()`.
Pfade relativ zum Repo-Root auflösen: `ROOT = Path(__file__).resolve().parents[1]`.
