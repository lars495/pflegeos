---
id: T024
title: "Modell: Hinweise der Person zur Übergabe"
roadmap_item: Recherche 2026-10-05 — Bewohnerblick auf die Übergabe
depends_on: []
target_files:
  - apps/api/models/hinweis.py
context_files:
  - apps/api/models/beobachtung.py
  - apps/api/db.py
  - tests/task_tests/test_t024_hinweis_modell.py
test_command: pytest -q tests/task_tests/test_t024_hinweis_modell.py
max_attempts: 3
attempts_used: 0
---

Bewohner:innen sollen festhalten können, was ihnen bei Übergaben wichtig ist —
z. B. „Bitte nicht vor Besuch über meine Gesundheit sprechen" oder „Ich brauche
morgens Zeit".

Lege `apps/api/models/hinweis.py` an, im selben Stil wie `apps/api/models/beobachtung.py` (Column-Stil, erbt von `Base`, `id` als String-PK mit `default=lambda: uuid.uuid4().hex`, `created_at` mit `default=datetime.utcnow`). Keine weiteren Dateien anfassen.

Klasse `PersonHinweis`, Tabelle `person_hinweise`: `id`, `resident_id` (String,
nullable=False, index=True), `text` (Text, nullable=False), `created_at`.
