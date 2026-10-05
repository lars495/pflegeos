---
id: T022
title: Beobachtungen auf der Profilseite zeigen
roadmap_item: Recherche 2026-10-05 — Stop-and-Watch-Karte im Bewohnerprofil
depends_on:
- T021
target_files:
- apps/api/templates/_beobachtungen.html
- apps/api/templates/bewohner_detail.html
- apps/api/web.py
context_files:
- apps/api/web.py
- apps/api/templates/bewohner_detail.html
- apps/api/templates/_wuensche.html
- apps/api/models/beobachtung.py
- tests/task_tests/test_t022_ui_beobachtungen_im_profil.py
test_command: pytest -q tests/task_tests/test_t022_ui_beobachtungen_im_profil.py
max_attempts: 3
attempts_used: 1
completed_at: '2026-10-05'
---

Die gemeldeten Beobachtungen sollen auf der Profilseite sichtbar sein — **unter**
Biografie und Wünschen (die Person zuerst, dann die Veränderung).

**In `apps/api/web.py`** (komplett neu ausgeben, alles andere behalten): In
`ui_bewohner_detail` zusätzlich die letzten 5 Beobachtungen dieser Person laden
und als `beobachtungen` ans Template geben:
```python
result = await session.execute(
    select(Beobachtung).where(Beobachtung.resident_id == resident_id)
    .order_by(Beobachtung.created_at.desc()).limit(5))
beobachtungen = result.scalars().all()
```

**Neues Fragment `apps/api/templates/_beobachtungen.html`** (kein `extends`):
- Ist `beobachtungen` leer: `<p class="leer">Keine Beobachtungen in letzter Zeit.</p>`
- Sonst `<ul class="wunsch-liste">`, je Eintrag `<li>`: **Kategorie** fett,
  dahinter die Notiz (falls vorhanden), darunter in `<span class="muted">` das
  Datum `{{ b.created_at.strftime('%d.%m. %H:%M') }}` und das Kürzel
- Darunter ein Link `<a class="btn-secondary" href="/ui/bewohner/{{ person.id }}/beobachtung">Mir ist etwas aufgefallen</a>`

**In `apps/api/templates/bewohner_detail.html`:** nach dem Wünsche-Block
(nach `{% include "_wuensche.html" %}`) einfügen:
```jinja
  <h2>Beobachtungen</h2>
  {% include "_beobachtungen.html" %}
```
Den Rest der Datei unverändert lassen.

**Gestaltungsregeln (gelten für jede Seite):**
- Template beginnt mit `{% extends "base.html" %}` und füllt `{% block content %}`
- Deutsche Beschriftungen, freundlich und einfach — Zielgruppe sind Pflegekräfte,
  keine Entwickler. Keine Fachbegriffe wie "Entity", "Submit", "ID".
- Vorhandene CSS-Klassen nutzen (style.css): `card`, `person-list`, `person-card`,
  `avatar`, `biografie`, `wunsch-liste`, `btn`, `btn-secondary`, `hinweis`,
  `erfolg`, `leer`, `lead`, `muted`
- Kein `<style>` und kein `<script>` im Template — kein Inline-CSS, kein Inline-JS
- Niemals echte Personendaten in Beispielen
