---
id: T025
title: "Hinweise der Person im Profil festhalten"
roadmap_item: Recherche 2026-10-05 — Bewohnerblick auf die Übergabe
depends_on: [T024, T023]
target_files:
  - apps/api/templates/_hinweise.html
  - apps/api/templates/bewohner_detail.html
  - apps/api/web.py
context_files:
  - apps/api/web.py
  - apps/api/templates/bewohner_detail.html
  - apps/api/templates/_wuensche.html
  - apps/api/models/hinweis.py
  - tests/task_tests/test_t025_ui_hinweise_im_profil.py
test_command: pytest -q tests/task_tests/test_t025_ui_hinweise_im_profil.py
max_attempts: 3
attempts_used: 0
---

Auf der Profilseite ein neuer Abschnitt **„Das ist mir bei Übergaben wichtig"**,
ohne Seitenwechsel (HTMX) — genau nach dem Muster der Wünsche (`_wuensche.html`
und Route `ui_wunsch_hinzufuegen`).

**In `apps/api/web.py`** (komplett neu ausgeben, alles behalten):
- Import `from apps.api.models.hinweis import PersonHinweis`
- `POST /ui/bewohner/{resident_id}/hinweise` mit `text: str = Form("")`:
  Person laden (404 wenn fehlt); wenn `text.strip()` nicht leer: `PersonHinweis`
  anlegen und committen. Dann alle Hinweise der Person laden
  (`order_by(PersonHinweis.created_at)`) und `_hinweise.html` rendern mit
  `{"person": person, "hinweise": hinweise}`.
- In `ui_bewohner_detail` ebenfalls `hinweise` (gleiche Abfrage) ans Template geben.

**Neues Fragment `apps/api/templates/_hinweise.html`** (kein extends), Wurzel
`<div id="hinweise-block">`: Liste `<ul class="wunsch-liste">` der Hinweistexte
(oder `<p class="leer">Noch nichts festgehalten.</p>`), darunter ein Formular
`hx-post="/ui/bewohner/{{ person.id }}/hinweise" hx-target="#hinweise-block"
hx-swap="outerHTML"` mit Textfeld `name="text"` (Label „Was sollen alle bei der
Übergabe über dich wissen — oder was nicht?") und Knopf „Festhalten".

**In `bewohner_detail.html`:** nach dem Wünsche-Block und VOR „Beobachtungen":
```jinja
  <h2>Das ist mir bei Übergaben wichtig</h2>
  {% include "_hinweise.html" %}
```

**Gestaltungsregeln (gelten für jede Seite):**
- Template beginnt mit `{% extends "base.html" %}` und füllt `{% block content %}`
- Deutsche Beschriftungen, freundlich und einfach — Zielgruppe sind Pflegekräfte,
  keine Entwickler. Keine Fachbegriffe wie "Entity", "Submit", "ID".
- Vorhandene CSS-Klassen nutzen (style.css): `card`, `person-list`, `person-card`,
  `avatar`, `biografie`, `wunsch-liste`, `btn`, `btn-secondary`, `hinweis`,
  `erfolg`, `leer`, `lead`, `muted`
- Kein `<style>` und kein `<script>` im Template — kein Inline-CSS, kein Inline-JS
- Niemals echte Personendaten in Beispielen
