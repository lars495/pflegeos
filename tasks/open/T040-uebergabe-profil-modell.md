---
id: T040
title: UebergabeProfil-Modell (eigene Fassung des Übergabe-Blocks)
roadmap_item: Recherche 2026-10-29 — Wunsch- und Biografie-Block in der Übergabeansicht
depends_on: []
target_files:
- apps/api/models/uebergabe_profil.py
context_files:
- apps/api/models/beobachtung.py
- apps/api/db.py
- tests/task_tests/test_t040_uebergabe_profil_modell.py
test_command: pytest -q tests/task_tests/test_t040_uebergabe_profil_modell.py
max_attempts: 3
attempts_used: 0
---

Neue Datei `apps/api/models/uebergabe_profil.py` mit **einer** Klasse `UebergabeProfil`.
Sie speichert die von der Pflegekraft angepasste Fassung des Übergabe-Blocks, damit das
Bewohnerprofil selbst nie verändert wird. Kein Eingriff in bestehende Tabellen.

Aufbau wie `apps/api/models/beobachtung.py` (gleiche Imports-Art, `Base` aus `apps.api.db`).

- `__tablename__ = "uebergabe_profile"`
- `id` — `Column(String, primary_key=True, default=lambda: uuid.uuid4().hex)`
- `resident_id` — `Column(String, nullable=False, unique=True, index=True)` (höchstens eine Zeile pro Person)
- `biografie` — `Column(Text, nullable=True)`
- `wuensche` — `Column(Text, nullable=True)`
- `wohlbefinden` — `Column(Text, nullable=True)`
- `bearbeitet_von` — `Column(String, nullable=True)`
- `updated_at` — `Column(DateTime, default=datetime.utcnow)`

**Bedeutung (als Kommentar in die Klasse schreiben):** `None` heißt „nicht angepasst — es gilt
live der Wert aus dem Bewohnerprofil". Ein leerer Text `""` heißt „bewusst leer gelassen".
Diese beiden Zustände müssen unterscheidbar bleiben; nichts darf `""` zu `None` umwandeln.

Keine weiteren Dateien ändern (`models/__init__.py` bleibt unberührt; die Tabelle wird
angelegt, sobald die Oberfläche das Modell importiert).
