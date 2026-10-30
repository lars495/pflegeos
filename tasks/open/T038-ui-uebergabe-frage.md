---
id: T038
title: Freiwillige Frage nach der Übergabe beantworten (privat)
roadmap_item: Recherche 2026-10-29 — Reflexions-Prompt nach der Übergabe
depends_on:
- T037
target_files:
- apps/api/ui/uebergabe_frage.py
- apps/api/templates/uebergabe_frage.html
- apps/api/web.py
context_files:
- apps/api/web.py
- apps/api/ui/notizen.py
- apps/api/ui/common.py
- apps/api/models/uebergabe_reflexion.py
- apps/api/templates/reflexion.html
- tests/task_tests/test_t038_ui_uebergabe_frage.py
test_command: pytest -q tests/task_tests/test_t038_ui_uebergabe_frage.py
max_attempts: 3
attempts_used: 0
---

Neuer Bereich „Übergabe-Frage": Nach der Schichtübergabe kann eine Pflegekraft **freiwillig**
in unter einer Minute eine Frage beantworten. Die Antwort bleibt **privat**. Es gibt keinen
Zwang und keinen Fehlerton, wenn jemand die Frage auslässt.

### 1. `apps/api/ui/uebergabe_frage.py` (neu)

Aufbau wie `apps/api/ui/notizen.py` (`router = APIRouter()`, `templates` aus `apps.api.ui.common`,
`get_session` aus `apps.api.db`, `UebergabeReflexion` aus `apps.api.models.uebergabe_reflexion`).
Modul-Konstante:

```python
FRAGE = "Welche Information über eine Bewohnerin oder einen Bewohner hat dir heute gefehlt?"
```

Routen:

- `GET /ui/uebergabe-frage` (`async def ui_frage(request: Request)`): rendert
  `uebergabe_frage.html` mit `{"frage": FRAGE, "status": None, "antwort": ""}`.
- `POST /ui/uebergabe-frage` (`async def ui_frage_speichern(request, author: str = Form(""), antwort: str = Form(""), session = Depends(get_session))`):
  beide Werte mit `.strip()` bereinigen. Dann:
  - `author` und `antwort` nicht leer → `UebergabeReflexion(author=..., frage=FRAGE, antwort=..., geteilt=False)`
    speichern (commit), `status = "gespeichert"`.
  - `antwort` leer (egal ob Kürzel da) → nichts speichern, `status = "uebersprungen"`.
  - `antwort` nicht leer, aber `author` leer → nichts speichern, `status = "kuerzel_fehlt"`.
  - Immer Status 200 und `uebergabe_frage.html` mit `{"frage": FRAGE, "status": status, "antwort": antwort}`.
  - **Kein** `log_action` und kein Audit-Eintrag — die Antwort gehört der Pflegekraft, nicht der Einrichtung.

### 2. `apps/api/templates/uebergabe_frage.html` (neu)

`{% extends "base.html" %}`, füllt `{% block title %}PflegeOS — Frage zum Abschluss{% endblock %}`
und `{% block content %}`. Alles in einer `<div class="card">`:

- `<h1>Eine Frage zum Abschluss</h1>`, darunter `<p class="lead">{{ frage }}</p>`
- `<p class="muted">Das ist freiwillig und dauert unter einer Minute. Deine Antwort ist privat — nur du siehst sie.</p>`
- Je nach `status`:
  - `"gespeichert"`: `<p class="erfolg">Danke! Deine Antwort ist privat gespeichert. Du entscheidest später, ob du sie anonym mit dem Team teilst.</p>`; **kein** Formular.
  - `"uebersprungen"`: `<p class="hinweis">Kein Problem — die Frage ist freiwillig.</p>`; **kein** Formular.
  - `"kuerzel_fehlt"`: `<p class="hinweis">Bitte gib dein Kürzel an, damit nur du deine Antwort wiederfindest.</p>` und das Formular (Antwort vorbefüllt).
  - sonst (`None`): das Formular.
- Formular: `<form method="post" action="/ui/uebergabe-frage">` mit
  `<label for="author">Dein Kürzel</label><input type="text" id="author" name="author" placeholder="Dein Kürzel">`,
  `<label for="antwort">Deine Antwort</label><textarea id="antwort" name="antwort">{{ antwort }}</textarea>`,
  `<p class="muted">Bitte keine Namen von Bewohner:innen nennen.</p>` und
  `<button type="submit" class="btn">Privat speichern</button>`.
  Die Antwort wird nur normal ausgegeben (`{{ antwort }}`, Autoescape bleibt an — kein `|safe`).
- Immer darunter drei Links:
  `<a href="/ui/uebergabe-frage/meine" class="btn-secondary">Meine Antworten</a>`,
  `<a href="/ui/uebergabe-frage/team" class="btn-secondary">Was das Team geteilt hat</a>`,
  `<a href="/ui/uebergabe" class="btn-secondary">Zurück zur Übergabe</a>`.
  (Die ersten beiden Seiten baut T039.)

### 3. `apps/api/web.py` (komplett neu ausgeben, alles behalten)

Import-Zeile um `uebergabe_frage` ergänzen und `uebergabe_frage` am **Ende** von `BEREICHE` anhängen.
Sonst nichts verändern.

Hinweis: Der Eintrag in `tests/test_routen_bestand.py` ist nicht Teil dieser Task (erledigt das starke Modell nach Abschluss).

**Gestaltungsregeln (gelten für jede Seite):**
- Deutsche Beschriftungen, freundlich und einfach — Zielgruppe sind Pflegekräfte
- Vorhandene CSS-Klassen nutzen: `card`, `btn`, `btn-secondary`, `hinweis`, `erfolg`, `leer`, `lead`, `muted`
- Kein `<style>` und kein `<script>`, kein Inline-CSS/JS
- Niemals echte Personendaten in Beispielen
