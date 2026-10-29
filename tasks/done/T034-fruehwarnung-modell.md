---
id: T034
title: Frühwarn-Modelle (Fragen und Meldungen) anlegen
roadmap_item: Recherche 2026-10-29 — Stop-and-Watch-Frühwarnkarte für alle Qualifikationsstufen
depends_on: []
target_files:
- apps/api/models/fruehwarnung.py
- apps/api/models/__init__.py
context_files:
- apps/api/models/beobachtung.py
- apps/api/models/uebergabe_notiz.py
- apps/api/models/__init__.py
- apps/api/db.py
- tests/task_tests/test_t034_fruehwarnung_modell.py
test_command: pytest -q tests/task_tests/test_t034_fruehwarnung_modell.py
max_attempts: 3
attempts_used: 1
completed_at: '2026-10-29'
---

Zwei neue Tabellen für die Frühwarnkarte (Stop-and-Watch). Nur neue Tabellen, keine Änderung
an bestehenden. Muster: `apps/api/models/beobachtung.py` (String-Primärschlüssel mit
`uuid.uuid4().hex`, `Base` aus `apps.api.db`).

## Neue Datei `apps/api/models/fruehwarnung.py`

Importe: `json`, `uuid`, `datetime`, `Boolean, Column, DateTime, Integer, String, Text` aus
`sqlalchemy`, `select` aus `sqlalchemy`, `AsyncSession` aus `sqlalchemy.ext.asyncio`,
`Base` aus `apps.api.db`.

### Klasse `FruehwarnFrage` (`__tablename__ = "fruehwarn_fragen"`)
Eine Frage der Karte. Die Fragen gelten für die ganze Einrichtung und sind ein Vorschlag,
das Team kann sie ein- und ausschalten oder ergänzen.

| Feld | Typ | Details |
|---|---|---|
| `id` | String | Primärschlüssel, `default=lambda: uuid.uuid4().hex` |
| `schluessel` | String | `nullable=False`, `unique=True` |
| `text` | String | `nullable=False` |
| `aktiv` | Boolean | `nullable=False`, `default=True` |
| `position` | Integer | `nullable=False`, `default=0` |

### Klasse `FruehwarnMeldung` (`__tablename__ = "fruehwarn_meldungen"`)
Eine ausgefüllte Karte zu einer Person.

| Feld | Typ | Details |
|---|---|---|
| `id` | String | Primärschlüssel, `default=lambda: uuid.uuid4().hex` |
| `resident_id` | String | `nullable=False`, `index=True` |
| `author` | String | `nullable=False` (Kürzel) |
| `auffaelligkeiten` | Text | `default="[]"` — JSON-Liste der angekreuzten Fragetexte |
| `freitext` | Text | `default=""` |
| `created_at` | DateTime | `default=datetime.utcnow` |

Bewusst **kein** Feld für Rolle, Qualifikation, Punktzahl, Ampel oder Dringlichkeit:
Jede Stimme im Team zählt gleich.

Methode an `FruehwarnMeldung`:
```python
def auffaelligkeiten_liste(self) -> list[str]:
    """JSON aus `auffaelligkeiten` als Liste; bei None, leer oder ungültigem JSON: []"""
```

### Konstante und Funktion
```python
STANDARDFRAGEN: list[tuple[str, str]] = [
    ("weniger_gegessen_getrunken", "Hat weniger gegessen oder getrunken"),
    ("wirkt_anders", "Wirkt anders als sonst"),
    ("muede_schwach", "Ist müder, schwächer oder schläfriger als sonst"),
    ("spricht_weniger", "Spricht oder reagiert weniger als sonst"),
    ("mehr_hilfe", "Braucht mehr Hilfe als sonst"),
    ("unruhig_schmerz", "Wirkt unruhig oder hat vermutlich Schmerzen"),
]

async def standardfragen_sicherstellen(session: AsyncSession) -> None:
    """Legt jede Standardfrage an, deren `schluessel` noch fehlt.
    position = 1, 2, 3 … in der Reihenfolge von STANDARDFRAGEN, aktiv=True.
    Bestehende Fragen (auch ausgeschaltete oder eigene) bleiben unverändert.
    Nur wenn etwas angelegt wurde: `await session.commit()`.
    Mehrfaches Aufrufen ändert nichts (idempotent)."""
```

## `apps/api/models/__init__.py`
Eine Importzeile für das neue Modul ergänzen, im selben Stil wie die vorhandenen Importe
(damit die Tabellen bei `create_all` registriert werden). Alles andere in der Datei
unverändert lassen.
