---
id: T011
title: "GET /v1/stats — öffentliche Zahlen ohne Personenbezug"
roadmap_item: Public Roadmap-Tracker (autogeneriert)
depends_on: [T003, T009]
target_files:
  - apps/api/routes/stats.py
  - apps/api/main.py
context_files:
  - apps/api/routes/residents.py
  - apps/api/main.py
  - tests/task_tests/test_t011_stats_endpoint.py
test_command: pytest -q tests/task_tests/test_t011_stats_endpoint.py
max_attempts: 3
attempts_used: 0
---

Neue Datei `apps/api/routes/stats.py` + Registrierung in main.py
(`prefix="/v1", tags=["meta"]`).

`GET /stats` → Antwort:
```json
{"residents": 0, "reflections": 0, "version": "0.1.0"}
```

Zählen via `select(func.count()).select_from(Resident)`
(`from sqlalchemy import func, select`), Version aus
`from apps.api.main import app` wäre ein Zirkelimport — stattdessen
hart `"0.1.0"` zurückgeben. Nur Anzahlen, niemals Namen oder Daten —
das ist ein ÖFFENTLICHER Endpoint.
