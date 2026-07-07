---
id: T009
title: Reflexions-Endpoints (privat per Default)
roadmap_item: Reflexions-Tool (60-Sek nach Schicht)
depends_on: [T003, T008]
target_files:
  - apps/api/routes/reflections.py
  - apps/api/main.py
context_files:
  - apps/api/models/reflection.py
  - apps/api/routes/residents.py
  - apps/api/main.py
  - tests/task_tests/test_t009_reflection_endpoints.py
test_command: pytest -q tests/task_tests/test_t009_reflection_endpoints.py
max_attempts: 3
attempts_used: 0
---

Neue Datei `apps/api/routes/reflections.py` + Registrierung in main.py
(`prefix="/v1", tags=["reflexionen"]`).

Pydantic-Schemas direkt in der Datei definieren:
- `ReflectionIn`: author (str, Pflicht), gut/schwierig/mitnehmen (str, default "")
- `ReflectionOut`: id, author, gut, schwierig, mitnehmen, nur_fuer_mich (bool),
  mit from_attributes=True

Endpoints:
1. `POST /reflections` → 201, `ReflectionOut`
2. `GET /reflections?author=X` → nur Reflexionen dieses Autors,
   `author` ist PFLICHT-Query-Parameter (`author: str = Query(...)`) —
   ohne author gibt FastAPI automatisch 422. Filter:
   `select(Reflection).where(Reflection.author == author)`

Solange es kein Login gibt, ist das Pseudonym der Zugriffsschutz.
Später (Login-Serie) wird author aus dem Token gelesen.
