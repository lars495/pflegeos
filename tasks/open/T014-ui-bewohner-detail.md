---
id: T014
title: Bewohner-Profil als Webseite (Biografie im Mittelpunkt)
roadmap_item: Bewohner-Profil mit Biografie (Lebensgeschichte, Beruf, Werte)
depends_on: [T013]
target_files:
  - apps/api/templates/bewohner_detail.html
  - apps/api/web.py
context_files:
  - apps/api/web.py
  - apps/api/templates/bewohner_liste.html
  - apps/api/models/resident.py
  - tests/task_tests/test_t014_ui_bewohner_detail.py
test_command: pytest -q tests/task_tests/test_t014_ui_bewohner_detail.py
max_attempts: 3
attempts_used: 0
---

Die Profilseite unter `/ui/bewohner/{resident_id}`. **Wichtigste Regel aus
PRINCIPLES.md: Die Biografie steht oben — vor allem anderen.** Keine Diagnosen,
keine Pflegegrade.

**In `apps/api/web.py`** (komplett neu ausgeben, bestehende Routen behalten):

```python
@router.get("/ui/bewohner/{resident_id}", response_class=HTMLResponse)
async def ui_bewohner_detail(
    resident_id: str, request: Request, session: AsyncSession = Depends(get_session)
):
    person = await session.get(Resident, resident_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Bewohner:in nicht gefunden")
    return templates.TemplateResponse(request, "bewohner_detail.html", {"person": person})
```
`HTTPException` aus `fastapi` importieren.

**In `apps/api/templates/bewohner_detail.html`:**
- Kopf: `<span class="avatar">{{ person.name|initialen }}</span>` und
  `<h1>{{ person.name }}</h1>`; darunter Zimmer und Geburtsdatum
  in `<p class="muted">`, falls vorhanden
- **Direkt darunter** ein Abschnitt „Wer ich bin" mit
  `<div class="biografie">{{ person.biografie }}</div>`
- Danach „Meine Wünsche": `<ul class="wunsch-liste">` mit einem `<li>` je Eintrag
  aus `person.wuensche`; ist die Liste leer, ein Satz in `<p class="leer">`
- Zurück-Link auf `/ui/bewohner` (`class="btn-secondary"`)

**Gestaltungsregeln (gelten für jede Seite):**
- Template beginnt mit `{% extends "base.html" %}` und füllt `{% block content %}`
- Deutsche Beschriftungen, freundlich und einfach — Zielgruppe sind Pflegekräfte,
  keine Entwickler. Keine Fachbegriffe wie "Entity", "Submit", "ID".
- Vorhandene CSS-Klassen nutzen (style.css): `card`, `person-list`, `person-card`,
  `avatar`, `biografie`, `wunsch-liste`, `btn`, `btn-secondary`, `hinweis`,
  `erfolg`, `leer`, `lead`, `muted`
- Kein `<style>` und kein `<script>` im Template — kein Inline-CSS, kein Inline-JS
- Niemals echte Personendaten in Beispielen
