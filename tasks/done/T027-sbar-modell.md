---
id: T027
title: 'Modell: SBAR-Notiz für den Arztanruf'
roadmap_item: Recherche 2026-10-05 — SBAR-Vorlage für den Arztanruf
depends_on: []
target_files:
- apps/api/models/sbar.py
context_files:
- apps/api/models/beobachtung.py
- apps/api/db.py
- tests/task_tests/test_t027_sbar_modell.py
test_command: pytest -q tests/task_tests/test_t027_sbar_modell.py
max_attempts: 3
attempts_used: 1
completed_at: '2026-10-05'
---

SBAR (Situation, Hintergrund, Einschätzung, Empfehlung) ist im Pflegeheim vor
allem für den Anruf bei Ärzt:innen bei Zustandsveränderung belegt.

Lege `apps/api/models/sbar.py` an, im selben Stil wie `apps/api/models/beobachtung.py` (Column-Stil, erbt von `Base`, `id` als String-PK mit `default=lambda: uuid.uuid4().hex`, `created_at` mit `default=datetime.utcnow`). Keine weiteren Dateien anfassen.

Klasse `SbarNotiz`, Tabelle `sbar_notizen`: `id`, `resident_id` (String,
nullable=False, index=True), `author` (String, nullable=False), `situation`,
`hintergrund`, `einschaetzung`, `empfehlung` (alle Text, `default=""`), `created_at`.
