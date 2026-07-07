---
id: T007
title: Audit-Helper + Logging bei Resident-Änderungen
roadmap_item: Login + Rollen + Audit-Log
depends_on: [T005, T006]
target_files:
  - apps/api/audit.py
  - apps/api/routes/residents.py
context_files:
  - apps/api/models/audit.py
  - apps/api/routes/residents.py
  - tests/task_tests/test_t007_audit_integration.py
test_command: pytest -q tests/task_tests/test_t007_audit_integration.py
max_attempts: 3
attempts_used: 0
---

Zwei Schritte:

1. Neue Datei `apps/api/audit.py` mit genau einer Funktion:
   ```python
   async def log_action(
       session: AsyncSession,
       *,
       actor: str,
       action: str,
       resource_type: str,
       resource_id: str,
       details: dict | None = None,
   ) -> None:
   ```
   Sie erstellt einen `AuditLog`-Eintrag und macht `session.add(...)` —
   KEIN eigenes commit (der Aufrufer committet).

2. In `apps/api/routes/residents.py` (Datei komplett neu ausgeben,
   bestehende Endpoints beibehalten):
   - Nach dem Anlegen (POST /residents): VOR dem commit
     `await log_action(session, actor="system", action="resident.created",
     resource_type="resident", resource_id=obj.id)` — dafür das Objekt
     vorher mit `await session.flush()` persistieren, damit `obj.id` existiert.
   - Nach dem PATCH: analog mit `action="resident.updated"`.
