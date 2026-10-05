---
id: T029
title: "Modell: anonymes Team-Feedback zur Übergabe"
roadmap_item: Recherche 2026-10-05 — Team-Reflexion zur Übergabe (anonym)
depends_on: []
target_files:
  - apps/api/models/team_feedback.py
context_files:
  - apps/api/models/beobachtung.py
  - apps/api/db.py
  - tests/task_tests/test_t029_team_feedback_modell.py
test_command: pytest -q tests/task_tests/test_t029_team_feedback_modell.py
max_attempts: 3
attempts_used: 0
---

Das Team soll anonym sagen können, was in Übergaben fehlt oder stört. **Anonymität
ist eingebaut, nicht versprochen:** Das Modell hat KEIN Feld, das auf eine Person
zurückführt (kein author, kein Kürzel, keine IP).

Lege `apps/api/models/team_feedback.py` an, im selben Stil wie `apps/api/models/beobachtung.py` (Column-Stil, erbt von `Base`, `id` als String-PK mit `default=lambda: uuid.uuid4().hex`, `created_at` mit `default=datetime.utcnow`). Keine weiteren Dateien anfassen.

Klasse `TeamFeedback`, Tabelle `team_feedback`: `id`, `gefehlt`, `unnoetig`,
`hilft` (alle Text, `default=""`), `created_at`. Sonst keine Felder.
