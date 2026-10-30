---
id: T037
title: Modell für private Übergabe-Reflexion
roadmap_item: Recherche 2026-10-29 — Reflexions-Prompt nach der Übergabe
depends_on: []
target_files:
- apps/api/models/uebergabe_reflexion.py
context_files:
- apps/api/models/beobachtung.py
- apps/api/db.py
- tests/task_tests/test_t037_uebergabe_reflexion_modell.py
test_command: pytest -q tests/task_tests/test_t037_uebergabe_reflexion_modell.py
max_attempts: 3
attempts_used: 1
completed_at: '2026-10-30'
---

Nach der Schichtübergabe kann eine Pflegekraft freiwillig eine kurze Frage beantworten
(„Welche Information hat dir heute gefehlt?"). Die Antwort ist **zunächst privat**.
Nur wenn die Pflegekraft sie ausdrücklich teilt, geht sie **anonym** in die Teambesprechung.

Lege die neue Datei `apps/api/models/uebergabe_reflexion.py` an, im Stil von
`apps/api/models/beobachtung.py` (gleiche Imports aus `sqlalchemy`, `uuid`, `datetime`,
`Base` aus `apps.api.db`). Keine anderen Dateien ändern, keine Migration.

```python
class UebergabeReflexion(Base):
    __tablename__ = "uebergabe_reflexionen"
```

Spalten (exakt diese, keine weiteren):

| Feld | Typ | Eigenschaften |
|---|---|---|
| `id` | `String` | `primary_key=True`, `default=lambda: uuid.uuid4().hex` |
| `author` | `String` | `nullable=False`, `index=True` (Kürzel der Pflegekraft; nur für ihre eigene Ansicht) |
| `frage` | `Text` | `nullable=False` (der Wortlaut der gestellten Frage) |
| `antwort` | `Text` | `nullable=False` |
| `geteilt` | `Boolean` | `nullable=False`, `default=False` |
| `geteilt_at` | `DateTime` | `nullable=True` |
| `created_at` | `DateTime` | `default=datetime.utcnow` |

**Wichtig (Privatsphäre):** Es gibt bewusst **kein** `resident_id`-Feld. Die Antwort ist
nicht mit einer Person verknüpft und kann so nicht zu Bewohner:innen zurückverfolgt werden.

Nicht in `apps/api/models/__init__.py` eintragen — die UI-Dateien importieren das Modell direkt.

Gestaltungsregeln: Niemals echte Personendaten in Beispielen.
