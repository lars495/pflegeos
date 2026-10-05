---
id: T026
title: Hinweise der Person in der Übergabe zuerst zeigen
roadmap_item: Recherche 2026-10-05 — Bewohnerblick auf die Übergabe
depends_on:
- T025
target_files:
- apps/api/templates/uebergabe.html
- apps/api/web.py
context_files:
- apps/api/web.py
- apps/api/templates/uebergabe.html
- apps/api/models/hinweis.py
- tests/task_tests/test_t026_ui_hinweise_in_uebergabe.py
test_command: pytest -q tests/task_tests/test_t026_ui_hinweise_in_uebergabe.py
max_attempts: 3
attempts_used: 1
completed_at: '2026-10-05'
---

In der Übergabe soll die Stimme der Person **zuerst** kommen — noch vor Wünschen
und Biografie.

**In `apps/api/web.py`** (komplett neu ausgeben, alles behalten): In `ui_uebergabe`
alle `PersonHinweis` laden und nach `resident_id` gruppieren (wie die
Beobachtungen, als dict `hinweise`), ans Template geben.

**In `uebergabe.html`:** in jeder Personenkarte direkt nach der `<h2>`-Zeile und
VOR den Wünschen — nur wenn Hinweise vorhanden:
```jinja
{% set hw = hinweise.get(p.id, []) %}
{% if hw %}
  <div class="hinweis"><!-- PERSON-HINWEIS -->
    <strong>Wunsch für die Übergabe:</strong>
    <ul>{% for h in hw %}<li>{{ h.text }}</li>{% endfor %}</ul>
  </div>
{% endif %}
```
Der Kommentar `<!-- PERSON-HINWEIS -->` muss genau so im Template stehen. Sonst nichts ändern.

**Gestaltungsregeln (gelten für jede Seite):**
- Template beginnt mit `{% extends "base.html" %}` und füllt `{% block content %}`
- Deutsche Beschriftungen, freundlich und einfach — Zielgruppe sind Pflegekräfte,
  keine Entwickler. Keine Fachbegriffe wie "Entity", "Submit", "ID".
- Vorhandene CSS-Klassen nutzen (style.css): `card`, `person-list`, `person-card`,
  `avatar`, `biografie`, `wunsch-liste`, `btn`, `btn-secondary`, `hinweis`,
  `erfolg`, `leer`, `lead`, `muted`
- Kein `<style>` und kein `<script>` im Template — kein Inline-CSS, kein Inline-JS
- Niemals echte Personendaten in Beispielen
