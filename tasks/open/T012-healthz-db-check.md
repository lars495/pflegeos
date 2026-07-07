---
id: T012
title: /healthz prüft die Datenbank mit
roadmap_item: Stamm-Datenbankschema + Migrations-Setup
depends_on: [T003]
target_files:
  - apps/api/routes/health.py
context_files:
  - apps/api/routes/health.py
  - apps/api/routes/residents.py
  - tests/task_tests/test_t012_healthz_db.py
test_command: pytest -q tests/task_tests/test_t012_healthz_db.py
max_attempts: 3
attempts_used: 0
---

Erweitere `GET /healthz` in `apps/api/routes/health.py`:

```python
@router.get("/healthz")
async def healthz(session: AsyncSession = Depends(get_session)) -> dict:
    try:
        await session.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception:
        db_status = "error"
    return {"status": "ok" if db_status == "ok" else "degraded", "db": db_status}
```

Zusätzlich auf Modulebene die Konstante `HEALTHZ_CHECKS_DB = True` definieren
(der Test nutzt sie als Umsetzungs-Marker).

Imports: `from sqlalchemy import text`, `from sqlalchemy.ext.asyncio import AsyncSession`,
`from fastapi import Depends`, `from apps.api.db import get_session`.
Immer HTTP 200 zurückgeben (der Docker-Healthcheck bewertet das Feld nicht) —
`/readyz` unverändert lassen.
