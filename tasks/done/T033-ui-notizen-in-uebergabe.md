---
id: T033
title: Freigegebene Notizen in der Übergabe zeigen
roadmap_item: Recherche 2026-10-05 — Übergabe-Notiz mit Freigabe
depends_on:
- T032
target_files:
- apps/api/templates/uebergabe.html
- apps/api/web.py
context_files:
- apps/api/web.py
- apps/api/templates/uebergabe.html
- apps/api/models/uebergabe_notiz.py
- tests/task_tests/test_t033_ui_notizen_in_uebergabe.py
test_command: pytest -q tests/task_tests/test_t033_ui_notizen_in_uebergabe.py
max_attempts: 3
attempts_used: 3
completed_at: '2026-10-05'
---

In der Übergabe erscheinen **ausschließlich freigegebene** Notizen der letzten
24 Stunden — Entwürfe niemals.

**In `apps/api/web.py`** (komplett neu ausgeben, alles behalten): In `ui_uebergabe`
zusätzlich laden:
```python
notizen_q = await session.execute(select(UebergabeNotiz)
    .where(UebergabeNotiz.status == "freigegeben", UebergabeNotiz.freigegeben_at >= seit)
    .order_by(UebergabeNotiz.freigegeben_at.desc()))
```
nach `resident_id` gruppieren und als `notizen` ans Template geben.

**In `uebergabe.html`:** in jeder Personenkarte nach dem Abschnitt „Seit gestern"
einfügen (der Kommentar muss genau so drinstehen):
```jinja
<!-- UEBERGABE-NOTIZEN -->
{% for n in notizen.get(p.id, []) %}
  <p><strong>Notiz:</strong> {{ n.text }} <span class="muted">({{ n.author }})</span></p>
{% endfor %}
```
Sonst nichts ändern.

**Gestaltungsregeln (gelten für jede Seite):**
- Template beginnt mit `{% extends "base.html" %}` und füllt `{% block content %}`
- Deutsche Beschriftungen, freundlich und einfach — Zielgruppe sind Pflegekräfte,
  keine Entwickler. Keine Fachbegriffe wie "Entity", "Submit", "ID".
- Vorhandene CSS-Klassen nutzen (style.css): `card`, `person-list`, `person-card`,
  `avatar`, `biografie`, `wunsch-liste`, `btn`, `btn-secondary`, `hinweis`,
  `erfolg`, `leer`, `lead`, `muted`
- Kein `<style>` und kein `<script>` im Template — kein Inline-CSS, kein Inline-JS
- Niemals echte Personendaten in Beispielen
