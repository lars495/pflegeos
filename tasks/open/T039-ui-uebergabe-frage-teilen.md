---
id: T039
title: Eigene Antworten ansehen, anonym teilen, Team-Sicht
roadmap_item: Recherche 2026-10-29 — Reflexions-Prompt nach der Übergabe
depends_on:
- T038
target_files:
- apps/api/ui/uebergabe_frage.py
- apps/api/templates/uebergabe_frage_liste.html
- apps/api/templates/uebergabe.html
context_files:
- apps/api/ui/uebergabe_frage.py
- apps/api/templates/uebergabe_frage.html
- apps/api/templates/uebergabe.html
- apps/api/models/uebergabe_reflexion.py
- tests/task_tests/test_t039_ui_uebergabe_frage_teilen.py
test_command: pytest -q tests/task_tests/test_t039_ui_uebergabe_frage_teilen.py
max_attempts: 3
attempts_used: 0
---

Die Pflegekraft sieht ihre eigenen Antworten, entscheidet **selbst**, welche sie anonym mit dem
Team teilt (und kann das zurücknehmen). Die Teambesprechung sieht nur die geteilten Texte —
ohne Kürzel, ohne Zeitpunkt, in zufälliger Reihenfolge. So entscheidet das Team selbst,
welche Felder der Übergabe angepasst werden.

### 1. `apps/api/ui/uebergabe_frage.py` (komplett neu ausgeben, bestehende Routen und `FRAGE` unverändert behalten)

Zusätzliche Imports: `datetime as dt`, `from urllib.parse import quote`, `RedirectResponse`.
**Nirgends `log_action` aufrufen** — kein Audit-Eintrag, damit niemand über das Protokoll
Kürzel und geteilte Texte zusammenführen kann.

Neue Routen:

- `GET /ui/uebergabe-frage/meine` (`async def ui_meine(request, author: str = "", session = Depends(get_session))`):
  `author` mit `.strip()`. Ist er leer: `eintraege = []`. Sonst alle `UebergabeReflexion` mit
  `author == author`, `order_by(created_at.desc()).limit(20)`.
  Rendert `uebergabe_frage_liste.html` mit `{"modus": "meine", "author": author, "eintraege": eintraege, "punkte": []}`.
- `POST /ui/uebergabe-frage/{reflexion_id}/teilen` (`author: str = Form("")`): Eintrag per `session.get` laden
  (404, wenn fehlt). Stimmt `author.strip()` nicht mit `eintrag.author` überein → `HTTPException(403)`, nichts ändern.
  Sonst `geteilt = True`, `geteilt_at = dt.datetime.utcnow()`, commit, dann
  `RedirectResponse(url=f"/ui/uebergabe-frage/meine?author={quote(eintrag.author, safe='')}", status_code=303)`.
- `POST /ui/uebergabe-frage/{reflexion_id}/zuruecknehmen` (`author: str = Form("")`): wie oben (404/403),
  setzt `geteilt = False`, `geteilt_at = None`, commit, gleiche Weiterleitung (303).
- `GET /ui/uebergabe-frage/team` (`async def ui_team(request, session = Depends(get_session))`):
  alle `UebergabeReflexion` mit `geteilt == True`, `order_by(UebergabeReflexion.id)` (die ID ist zufällig —
  so verrät die Reihenfolge nichts über den Zeitpunkt). Rendert `uebergabe_frage_liste.html` mit
  `{"modus": "team", "author": "", "eintraege": [], "punkte": [e.antwort for e in ...]}`.
  Es werden **nur die Antworttexte** an das Template gegeben, nie Kürzel oder Zeiten.

### 2. `apps/api/templates/uebergabe_frage_liste.html` (neu)

`{% extends "base.html" %}`, `{% block content %}`, alles in einer `<div class="card">`. Die Variable `modus` steuert:

**`modus == "meine"`:**
- `<h1>Meine Antworten</h1>` und `<p class="muted">Nur du siehst diese Seite mit deinem Kürzel. Geteilte Punkte erscheinen anonym.</p>`
- Immer ein Formular `<form method="get" action="/ui/uebergabe-frage/meine">` mit
  `<label for="author">Dein Kürzel</label><input type="text" id="author" name="author" value="{{ author }}">` und Knopf „Anzeigen".
- Je Eintrag eine `<div class="card">` mit `<p>{{ e.antwort }}</p>` und:
  - `e.geteilt` falsch: `<span>Privat</span>` und
    `<form method="post" action="/ui/uebergabe-frage/{{ e.id }}/teilen">` mit
    `<input type="hidden" name="author" value="{{ author }}">` und `<button type="submit" class="btn">Anonym teilen</button>`.
  - `e.geteilt` wahr: `<span>Mit dem Team geteilt (anonym)</span>` und ein gleichartiges Formular auf
    `/ui/uebergabe-frage/{{ e.id }}/zuruecknehmen` mit Knopf „Zurücknehmen" (`btn-secondary`).
- Ist `author` gesetzt, aber `eintraege` leer: `<p class="leer">Noch keine Antworten.</p>`.

**`modus == "team"`:**
- `<h1>Was das Team geteilt hat</h1>`
- `<p class="muted">Diese Punkte sind anonym und wurden freiwillig geteilt. Das Team entscheidet gemeinsam, welche Felder der Übergabe angepasst werden.</p>`
- Je Punkt `<div class="card"><p>{{ punkt }}</p></div>`; leer: `<p class="leer">Noch nichts geteilt.</p>`.

Am Ende in beiden Modi Links: `<a href="/ui/uebergabe-frage" class="btn-secondary">Zur Frage</a>` und
`<a href="/ui/uebergabe" class="btn-secondary">Zurück zur Übergabe</a>`.
Alle Texte nur mit `{{ ... }}` ausgeben (Autoescape), niemals `|safe`.

### 3. `apps/api/templates/uebergabe.html` (komplett neu ausgeben, alles behalten)

Am **Ende** von `{% block content %}` (nach dem bisherigen Inhalt) einfügen — ein Link, kein Pop-up, kein Zwang:

```jinja
  <p><a href="/ui/uebergabe-frage" class="btn-secondary">Eine Frage zum Abschluss (freiwillig, unter einer Minute)</a></p>
```

Sonst nichts an der Übergabe-Seite verändern.

**Gestaltungsregeln:** deutsche, einfache Beschriftungen; nur vorhandene CSS-Klassen
(`card`, `btn`, `btn-secondary`, `leer`, `muted`); kein `<style>`/`<script>`; keine echten Personendaten in Beispielen.
