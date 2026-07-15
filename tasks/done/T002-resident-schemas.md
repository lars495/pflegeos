---
id: T002
title: Pydantic-Schemas für Residents
roadmap_item: Bewohner-Profil mit Biografie (Lebensgeschichte, Beruf, Werte)
depends_on:
- T001
target_files:
- apps/api/schemas/resident.py
context_files:
- apps/api/models/resident.py
- tests/task_tests/test_t002_resident_schemas.py
test_command: pytest -q tests/task_tests/test_t002_resident_schemas.py
max_attempts: 3
attempts_used: 1
completed_at: '2026-07-15'
---

Lege drei Pydantic-v2-Schemas in `apps/api/schemas/resident.py` an:

1. `ResidentCreate` — `name: str` (Pflicht), alle anderen Resident-Felder
   optional mit Default `None` bzw. `""` für biografie/werte und `[]` für wuensche.
   Felder: name, geburtsdatum (date|None), zimmer (str|None), einzugsdatum (date|None),
   biografie (str, default ""), beruf_frueher (str|None), werte (str, default ""),
   wuensche (list[str], default []).
2. `ResidentUpdate` — ALLE Felder optional (`| None = None`), auch name.
   Für Teilupdates: nur gesetzte Felder werden übernommen.
3. `ResidentOut` — id (str) + alle Felder aus ResidentCreate.
   Mit `model_config = ConfigDict(from_attributes=True)`.

Import-Stil: `from pydantic import BaseModel, ConfigDict` und `import datetime as dt`
(dann `dt.date`).
