---
id: T031
title: 'Modell: Übergabe-Notiz mit Freigabe-Status'
roadmap_item: Recherche 2026-10-05 — Übergabe-Notiz mit Freigabe
depends_on: []
target_files:
- apps/api/models/uebergabe_notiz.py
context_files:
- apps/api/models/beobachtung.py
- apps/api/db.py
- tests/task_tests/test_t031_notiz_modell.py
test_command: pytest -q tests/task_tests/test_t031_notiz_modell.py
max_attempts: 3
attempts_used: 1
completed_at: '2026-10-05'
---

Notizen sind zuerst **Entwürfe** und werden erst durch ausdrückliche Freigabe
Teil der Übergabe (Prinzip: nichts wird ohne Bestätigung Teil der Doku).

Lege `apps/api/models/uebergabe_notiz.py` an, im selben Stil wie `apps/api/models/beobachtung.py` (Column-Stil, erbt von `Base`, `id` als String-PK mit `default=lambda: uuid.uuid4().hex`, `created_at` mit `default=datetime.utcnow`). Keine weiteren Dateien anfassen.

Klasse `UebergabeNotiz`, Tabelle `uebergabe_notizen`: `id`, `resident_id` (String,
nullable=False, index=True), `author` (String, nullable=False), `text` (Text,
nullable=False), `status` (String, `default="entwurf"`), `freigegeben_at`
(DateTime, nullable=True), `created_at`.
