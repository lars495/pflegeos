---
id: T020
title: Beobachtungs-Modell (Stop-and-Watch)
roadmap_item: Recherche 2026-10-05 — Stop-and-Watch-Karte im Bewohnerprofil
depends_on: []
target_files:
- apps/api/models/beobachtung.py
context_files:
- apps/api/models/audit.py
- apps/api/db.py
- tests/task_tests/test_t020_beobachtung_modell.py
test_command: pytest -q tests/task_tests/test_t020_beobachtung_modell.py
max_attempts: 3
attempts_used: 1
completed_at: '2026-10-05'
---

Hintergrund (aus der internationalen Recherche, ideas/accepted/): Das INTERACT-
Werkzeug „Stop and Watch" lässt jede Berufsgruppe — auch Pflegehilfe und
Hauswirtschaft — kurz melden, wenn jemand „anders wirkt als sonst". Die Menschen,
die Bewohner:innen täglich sehen, bemerken Veränderungen oft zuerst.

Lege `apps/api/models/beobachtung.py` an, im selben Stil wie `audit.py`
(Column-Stil, erbt von `Base`). Tabelle `beobachtungen`:

| Feld | Typ | Vorgabe |
|---|---|---|
| id | String, Primary Key | `default=lambda: uuid.uuid4().hex` |
| resident_id | String | nullable=False, index=True |
| author | String | nullable=False — Kürzel der meldenden Person |
| kategorie | String | nullable=False |
| notiz | Text | `default=""` |
| created_at | DateTime | `default=datetime.utcnow` |

Kein ForeignKey nötig. Keine weiteren Dateien anfassen.
