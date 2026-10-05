---
id: T028
title: "SBAR-Vorlage für den Arztanruf"
roadmap_item: Recherche 2026-10-05 — SBAR-Vorlage für den Arztanruf
depends_on: [T027, T026]
target_files:
  - apps/api/templates/sbar.html
  - apps/api/templates/_beobachtungen.html
  - apps/api/web.py
context_files:
  - apps/api/web.py
  - apps/api/templates/_beobachtungen.html
  - apps/api/templates/beobachtung_neu.html
  - apps/api/models/sbar.py
  - apps/api/models/beobachtung.py
  - tests/task_tests/test_t028_ui_sbar.py
test_command: pytest -q tests/task_tests/test_t028_ui_sbar.py
max_attempts: 3
attempts_used: 0
---

Eine Gesprächsstütze für den Anruf bei Ärzt:innen. **Wichtig (Empowerment):**
Die Software füllt nur vor, was sie sicher weiß — Fakten aus den Daten. Die
Felder **Einschätzung** und **Empfehlung** bleiben LEER; die schreibt die
Pflegekraft. Keine KI, keine automatisch formulierten Texte.

**In `apps/api/web.py`** (komplett neu ausgeben, alles behalten), Routen VOR
`/ui/bewohner/{resident_id}` einfügen, Import `from apps.api.models.sbar import SbarNotiz`:

- `GET /ui/bewohner/{resident_id}/sbar`: Person laden (404). Beobachtungen der
  letzten 24 Stunden dieser Person laden. Vorbefüllung:
  ```python
  situation = "\n".join(b.kategorie + (f" — {b.notiz}" if b.notiz else "") for b in beob)
  hintergrund = person.name + (f", Zimmer {person.zimmer}" if person.zimmer else "") + ". " + (person.biografie or "")[:200]
  ```
  Rendern `sbar.html` mit `person`, `situation`, `hintergrund`.
- `POST /ui/bewohner/{resident_id}/sbar` mit Form-Feldern `author, situation,
  hintergrund, einschaetzung, empfehlung` (je `Form("")`): Person laden (404).
  Ohne `author.strip()` → `sbar.html` erneut rendern mit `fehler="Bitte dein Kürzel eintragen."`
  (und den eingegebenen Werten). Sonst `SbarNotiz` speichern,
  `log_action(session, actor=author.strip(), action="sbar.created", resource_type="resident", resource_id=resident_id)`,
  commit, `RedirectResponse(f"/ui/bewohner/{resident_id}", status_code=303)`.

**`apps/api/templates/sbar.html`** (extends base): Überschrift „Arztanruf vorbereiten",
`{{ person.name }}`, Kasten `<p class="erfolg">Einschätzung und Empfehlung
schreibst du — du kennst die Person.</p>`, ggf. `fehler`. `<form method="post">`
mit Feld `author` (Text, „Dein Kürzel") und vier `<textarea>`s mit den Labels
„S — Situation: Was ist los?" (`situation`, Inhalt `{{ situation }}`),
„B — Hintergrund" (`hintergrund`, Inhalt `{{ hintergrund }}`),
„A — Deine Einschätzung" (`einschaetzung`, leer),
„R — Was schlägst du vor?" (`empfehlung`, leer). Knopf „Notiz speichern".

**In `_beobachtungen.html`:** neben dem vorhandenen Link einen zweiten Link
`<a class="btn-secondary" href="/ui/bewohner/{{ person.id }}/sbar">Arztanruf vorbereiten</a>` ergänzen.

**Gestaltungsregeln (gelten für jede Seite):**
- Template beginnt mit `{% extends "base.html" %}` und füllt `{% block content %}`
- Deutsche Beschriftungen, freundlich und einfach — Zielgruppe sind Pflegekräfte,
  keine Entwickler. Keine Fachbegriffe wie "Entity", "Submit", "ID".
- Vorhandene CSS-Klassen nutzen (style.css): `card`, `person-list`, `person-card`,
  `avatar`, `biografie`, `wunsch-liste`, `btn`, `btn-secondary`, `hinweis`,
  `erfolg`, `leer`, `lead`, `muted`
- Kein `<style>` und kein `<script>` im Template — kein Inline-CSS, kein Inline-JS
- Niemals echte Personendaten in Beispielen
