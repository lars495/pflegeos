# Task-System — LLM-sichere Arbeitspakete

Der tägliche Build-Agent arbeitet **nicht mehr direkt an Roadmap-Features**,
sondern an Micro-Tasks aus diesem Ordner. Grund: Ein Feature wie
„Bewohner-Profil" ist für ein 70B-Modell in einem Wurf nicht machbar —
eine präzise spezifizierte Einzeldatei mit fertigem Test dagegen schon.

## Das Prinzip

**Das teure Modell denkt, das billige Modell tippt.**
Etwa einmal im Monat zerlegt ein starkes Modell (Claude, mit Lars) die
Roadmap in Tasks. Für jede Task existiert **der Test bereits im Repo**
(`tests/task_tests/`) — die Spezifikation ist ausführbarer Code:
Task fertig = Test grün. Kein Interpretationsspielraum.

## Ordner

| Ordner | Bedeutung |
|---|---|
| `tasks/open/` | Wartet auf Bearbeitung. Agent nimmt die niedrigste ID, deren Abhängigkeiten erledigt sind. |
| `tasks/done/` | Erfolgreich abgeschlossen (Test grün, committed). |
| `tasks/blocked/` | Nach `max_attempts` Fehlversuchen geparkt — braucht menschliche/starke-Modell-Hilfe. |

## Task-Format

Dateiname: `T001-kurzer-slug.md`. YAML-Frontmatter + Beschreibung:

```markdown
---
id: T001
title: Resident-Modell anlegen
roadmap_item: Bewohner-Profil mit Biografie
depends_on: []
target_files:
  - apps/api/models/resident.py
context_files:
  - apps/api/db.py
  - tests/task_tests/test_t001_resident_model.py
test_command: pytest -q tests/task_tests/test_t001_resident_model.py
max_attempts: 3
attempts_used: 0
---

Beschreibung, exakte Feldlisten, Signaturen, Beispiele.
```

Regeln für gute Tasks (beim monatlichen Zerlegen beachten):

1. **Max. 2 target_files** — eine Implementierungsdatei, ggf. eine Registrierung
2. **Test zuerst schreiben** — er beginnt mit `pytest.importorskip(...)`,
   damit die Gesamt-Suite nicht an noch-nicht-existierenden Modulen stirbt
3. **Signaturen vorgeben** — Klassenname, Feldnamen, Endpoint-Pfade exakt nennen
4. **context_files klein halten** — nur was wirklich gebraucht wird; der
   Task-Test gehört immer dazu (er IST die Spezifikation)
5. **Keine Auth-/Krypto-/Migrations-Tasks** — zu riskant für kleine Modelle
   bei Gesundheitsdaten; macht das starke Modell direkt

## Agent-Verhalten (scripts/build_agent.py)

1. Wählt niedrigste offene Task-ID, deren `depends_on` alle in `tasks/done/` liegen
2. Prompt = Task-Beschreibung + vollständiger Inhalt der `context_files`
3. Schreiben nur in `target_files` erlaubt
4. Bis zu 3 Versuche; ab Versuch 3 Eskalation auf Hermes 4 405B (falls Budget reicht)
5. Test grün → Task nach `done/`, Commit `feat(T001): …`
6. Alle Versuche rot → `attempts_used` hochzählen; bei `max_attempts` → `blocked/`
7. `tasks/open/` leer → Daily Report meldet „Backlog leer — Nachschub nötig"
