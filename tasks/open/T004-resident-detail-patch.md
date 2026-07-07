---
id: T004
title: "GET /v1/residents/{id} + PATCH Teilupdate"
roadmap_item: Bewohner-Profil mit Biografie (Lebensgeschichte, Beruf, Werte)
depends_on: [T003]
target_files:
  - apps/api/routes/residents.py
context_files:
  - apps/api/routes/residents.py
  - apps/api/schemas/resident.py
  - tests/task_tests/test_t004_resident_detail_patch.py
test_command: pytest -q tests/task_tests/test_t004_resident_detail_patch.py
max_attempts: 3
attempts_used: 0
---

Erweitere `apps/api/routes/residents.py` um zwei Endpoints (bestehende
Endpoints unverändert lassen, Datei komplett neu ausgeben):

1. `GET /residents/{resident_id}` → `ResidentOut` oder
   `raise HTTPException(status_code=404, detail="Bewohner:in nicht gefunden")`.
   Laden via `await session.get(Resident, resident_id)`.
2. `PATCH /residents/{resident_id}` → Body `ResidentUpdate`, Antwort `ResidentOut`.
   Teilupdate: NUR gesetzte Felder übernehmen:
   ```python
   for feld, wert in payload.model_dump(exclude_unset=True).items():
       setattr(obj, feld, wert)
   ```
   Danach commit + refresh. 404 wie oben, wenn nicht gefunden.
