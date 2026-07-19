---
id: T006
title: AuditLog-ORM-Modell
roadmap_item: Login + Rollen + Audit-Log
depends_on:
- T001
target_files:
- apps/api/models/audit.py
context_files:
- apps/api/db.py
- apps/api/models/resident.py
- tests/task_tests/test_t006_audit_model.py
test_command: pytest -q tests/task_tests/test_t006_audit_model.py
max_attempts: 3
attempts_used: 1
completed_at: '2026-07-19'
---

Lege das Modell `AuditLog` in `apps/api/models/audit.py` an (Vorbild:
resident.py). Tabelle: `audit_log`. Compliance-Anforderung: DSGVO Art. 32
verlangt Nachvollziehbarkeit aller Zugriffe auf Gesundheitsdaten.

| Feld | Typ | Vorgabe |
|---|---|---|
| id | str, Primary Key | `default=lambda: uuid.uuid4().hex` |
| timestamp | DateTime | `default=datetime.utcnow` |
| actor | str | not null — wer hat gehandelt ("system" bis Login existiert) |
| action | str | not null — z.B. "resident.created" |
| resource_type | str | not null — z.B. "resident" |
| resource_id | str | not null |
| details | JSON | `default=dict` |
