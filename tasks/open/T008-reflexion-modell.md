---
id: T008
title: Reflexions-ORM-Modell
roadmap_item: Reflexions-Tool (60-Sek nach Schicht)
depends_on: [T001]
target_files:
  - apps/api/models/reflection.py
context_files:
  - apps/api/models/resident.py
  - tests/task_tests/test_t008_reflection_model.py
test_command: pytest -q tests/task_tests/test_t008_reflection_model.py
max_attempts: 3
attempts_used: 0
---

Modell `Reflection` in `apps/api/models/reflection.py` (Vorbild resident.py).
Tabelle: `reflections`. Das ist das Reflexions-Tool für Pflegekräfte —
für sie selbst, nicht für die Akte. Privatsphäre ist Default!

| Feld | Typ | Vorgabe |
|---|---|---|
| id | str, Primary Key | `default=lambda: uuid.uuid4().hex` |
| author | str | not null — Pseudonym der Pflegekraft |
| gut | Text | `default=""` — was lief gut |
| schwierig | Text | `default=""` — was war schwer |
| mitnehmen | Text | `default=""` — was nehme ich mit |
| nur_fuer_mich | Boolean | `default=True` — WICHTIG: privat per Default |
| created_at | DateTime | `default=datetime.utcnow` |
