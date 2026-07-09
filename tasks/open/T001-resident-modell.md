---
id: T001
title: Resident-ORM-Modell anlegen
roadmap_item: Bewohner-Profil mit Biografie (Lebensgeschichte, Beruf, Werte)
depends_on: []
target_files:
- apps/api/models/resident.py
context_files:
- apps/api/db.py
- tests/task_tests/test_t001_resident_model.py
test_command: pytest -q tests/task_tests/test_t001_resident_model.py
max_attempts: 3
attempts_used: 1
---

Lege das SQLAlchemy-2.0-Modell `Resident` an. Die Biografie steht im
Mittelpunkt — nicht Diagnosen. Tabelle: `residents`.

Exakte Felder (SQLAlchemy 2.0 Stil mit `Mapped[...]` und `mapped_column`):

| Feld | Typ | Vorgabe |
|---|---|---|
| id | str, Primary Key | `default=lambda: uuid.uuid4().hex` |
| name | str | not null |
| geburtsdatum | date, nullable | |
| zimmer | str, nullable | |
| einzugsdatum | date, nullable | |
| biografie | Text | `default=""` |
| beruf_frueher | str, nullable | |
| werte | Text | `default=""` |
| wuensche | JSON | `default=list` |
| created_at | DateTime | `default=datetime.utcnow` |
| updated_at | DateTime | `default=datetime.utcnow, onupdate=datetime.utcnow` |

Wichtig:
- `from apps.api.db import Base` — von dieser Base erben
- Für JSON: `from sqlalchemy import JSON` und `mapped_column(JSON, default=list)`
- Für Text: `from sqlalchemy import Text`
- KEINE weiteren Dateien anfassen — die Registrierung passiert automatisch
