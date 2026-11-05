---
id: T043
title: Datenmodell für gespeicherte SBAR-Meldungen an Ärzt:innen
roadmap_item: Recherche 2026-10-29 — SBAR-Vorlage für die Meldung an Ärzt:innen
depends_on: []
target_files:
- apps/api/models/sbar_meldung.py
context_files:
- apps/api/models/beobachtung.py
- apps/api/models/sbar.py
- tests/task_tests/test_t043_sbar_meldung_modell.py
test_command: pytest -q tests/task_tests/test_t043_sbar_meldung_modell.py
max_attempts: 3
attempts_used: 1
completed_at: '2026-11-05'
---

Neue Tabelle für SBAR-Meldungen, die eine Pflegekraft **ausdrücklich bestätigt** hat.
Entwürfe werden nie gespeichert, deshalb gibt es kein `status`-Feld.

Lege **nur** die neue Datei `apps/api/models/sbar_meldung.py` an. Aufbau exakt wie
`apps/api/models/beobachtung.py` (gleiche Imports, `Base` aus `apps.api.db`).
Ändere weder `apps/api/models/sbar.py` noch andere bestehende Dateien. Die Datei
`sbar.py` ist nur Kontext: Klassen- und Tabellennamen dürfen **nicht** kollidieren.

```python
class SbarMeldung(Base):
    __tablename__ = "sbar_meldungen"
```

Spalten (exakt diese Namen):

| Feld | Typ | Eigenschaften |
|---|---|---|
| `id` | String | primary_key, default `uuid.uuid4().hex` (32 Zeichen) |
| `resident_id` | String | nullable=False, index=True |
| `fruehwarnung_id` | String | nullable=True (Meldung kann ohne Frühwarnung entstehen) |
| `author` | String | nullable=False (Kürzel der Pflegekraft, die bestätigt hat) |
| `situation` | Text | default `""` |
| `hintergrund` | Text | default `""` |
| `einschaetzung` | Text | default `""` |
| `empfehlung` | Text | default `""` |
| `created_at` | DateTime | default `datetime.utcnow` |

Keine Migration, keine Änderung an bestehenden Tabellen, kein ForeignKey.
