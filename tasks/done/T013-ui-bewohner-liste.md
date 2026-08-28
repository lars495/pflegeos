---
id: T013
title: Bewohner-Übersicht als Webseite
roadmap_item: Bewohner-Profil mit Biografie (Lebensgeschichte, Beruf, Werte)
depends_on: []
target_files:
- apps/api/templates/bewohner_liste.html
- apps/api/web.py
context_files:
- apps/api/web.py
- apps/api/templates/index.html
- apps/api/models/resident.py
- tests/task_tests/test_t013_ui_bewohner_liste.py
test_command: pytest -q tests/task_tests/test_t013_ui_bewohner_liste.py
max_attempts: 3
attempts_used: 1
completed_at: '2026-08-28'
---

Erste sichtbare Seite: die Übersicht aller Bewohner:innen unter `/ui/bewohner`.

**In `apps/api/web.py`** (Datei komplett neu ausgeben, bestehende Routen behalten):

```python
@router.get("/ui/bewohner", response_class=HTMLResponse)
async def ui_bewohner_liste(request: Request, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Resident).order_by(Resident.name))
    bewohner = result.scalars().all()
    return templates.TemplateResponse(request, "bewohner_liste.html", {"bewohner": bewohner})
```

**In `apps/api/templates/bewohner_liste.html`:**
- Überschrift „Bewohner:innen"
- Ist die Liste leer: freundlicher Hinweis mit dem Wort „niemand" in einem
  `<p class="leer">` — z. B. „Hier wohnt noch niemand."
- Sonst `<ul class="person-list">`, je Person ein `<li>` mit
  `<a class="person-card" href="/ui/bewohner/{{ p.id }}">`
- In der Karte: `<span class="avatar">{{ p.name|initialen }}</span>` (der Filter
  `initialen` ist bereits registriert), der Name als `<h3>`, darunter — falls
  vorhanden — „Zimmer {{ p.zimmer }}" in einem `<p class="muted">`
- Darunter ein Link „Person hinzufügen" (`class="btn"`) auf `/ui/bewohner/neu`

**Gestaltungsregeln (gelten für jede Seite):**
- Template beginnt mit `{% extends "base.html" %}` und füllt `{% block content %}`
- Deutsche Beschriftungen, freundlich und einfach — Zielgruppe sind Pflegekräfte,
  keine Entwickler. Keine Fachbegriffe wie "Entity", "Submit", "ID".
- Vorhandene CSS-Klassen nutzen (style.css): `card`, `person-list`, `person-card`,
  `avatar`, `biografie`, `wunsch-liste`, `btn`, `btn-secondary`, `hinweis`,
  `erfolg`, `leer`, `lead`, `muted`
- Kein `<style>` und kein `<script>` im Template — kein Inline-CSS, kein Inline-JS
- Niemals echte Personendaten in Beispielen
