---
id: T003
title: "POST + GET /v1/residents Endpoints"
roadmap_item: Bewohner-Profil mit Biografie (Lebensgeschichte, Beruf, Werte)
depends_on: [T001, T002]
target_files:
  - apps/api/routes/residents.py
  - apps/api/main.py
context_files:
  - apps/api/models/resident.py
  - apps/api/schemas/resident.py
  - apps/api/routes/contribute.py
  - apps/api/main.py
  - tests/task_tests/test_t003_residents_endpoints.py
test_command: pytest -q tests/task_tests/test_t003_residents_endpoints.py
max_attempts: 3
attempts_used: 0
---

Lege `apps/api/routes/residents.py` an und registriere den Router in `main.py`.

Endpoints:
1. `POST /residents` → Status 201, Body `ResidentCreate`, Antwort `ResidentOut`.
   Session via `Depends(get_session)` (`from apps.api.db import get_session`).
   Ablauf: `Resident(**payload.model_dump())` → `session.add` → `await session.commit()`
   → `await session.refresh(obj)` → zurückgeben.
2. `GET /residents` → Liste aller Residents als `list[ResidentOut]`.
   `from sqlalchemy import select` → `(await session.execute(select(Resident))).scalars().all()`

Router-Definition wie in contribute.py: `router = APIRouter()`, Pfade OHNE
/v1-Präfix (das setzt main.py beim Registrieren).

In `main.py`: `residents` mit importieren und
`app.include_router(residents.router, prefix="/v1", tags=["residents"])`
an der markierten Stelle ergänzen. Den Rest von main.py NICHT verändern.
