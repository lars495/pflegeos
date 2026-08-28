---
id: T015
title: Neue Person anlegen (Formular)
roadmap_item: Bewohner-Profil mit Biografie (Lebensgeschichte, Beruf, Werte)
depends_on: [T013]
target_files:
  - apps/api/templates/bewohner_neu.html
  - apps/api/web.py
context_files:
  - apps/api/web.py
  - apps/api/templates/bewohner_liste.html
  - apps/api/models/resident.py
  - tests/task_tests/test_t015_ui_bewohner_anlegen.py
test_command: pytest -q tests/task_tests/test_t015_ui_bewohner_anlegen.py
max_attempts: 3
attempts_used: 0
---

Formular unter `/ui/bewohner/neu` — GET zeigt es, POST legt an.

**ACHTUNG Reihenfolge:** Diese Route muss in `web.py` **vor**
`/ui/bewohner/{resident_id}` stehen, sonst hält FastAPI „neu" für eine ID.

**In `apps/api/web.py`** (komplett neu ausgeben, bestehende Routen behalten):

```python
from fastapi import Form
from fastapi.responses import RedirectResponse

@router.get("/ui/bewohner/neu", response_class=HTMLResponse)
async def ui_bewohner_neu_formular(request: Request):
    return templates.TemplateResponse(request, "bewohner_neu.html", {})

@router.post("/ui/bewohner/neu")
async def ui_bewohner_neu_speichern(
    request: Request,
    name: str = Form(""),
    zimmer: str = Form(""),
    biografie: str = Form(""),
    session: AsyncSession = Depends(get_session),
):
    if not name.strip():
        return templates.TemplateResponse(
            request, "bewohner_neu.html",
            {"fehler": "Bitte einen Namen eingeben."},
        )
    person = Resident(name=name.strip(), zimmer=zimmer.strip() or None,
                      biografie=biografie.strip())
    session.add(person)
    await session.commit()
    return RedirectResponse(f"/ui/bewohner/{person.id}", status_code=303)
```

**In `apps/api/templates/bewohner_neu.html`:**
- Überschrift „Neue Person aufnehmen"
- Wenn `fehler` gesetzt ist: `<p class="hinweis">{{ fehler }}</p>`
- `<form method="post">` mit drei Feldern (jeweils `<label>` davor):
  `name` (Text, Pflicht, Beschriftung „Wie heißt die Person?"),
  `zimmer` (Text, „Zimmer"),
  `biografie` (`<textarea>`, „Was sollte man über sie wissen?")
- Absende-Knopf mit `class="btn"`, Beschriftung „Person aufnehmen"

**Gestaltungsregeln (gelten für jede Seite):**
- Template beginnt mit `{% extends "base.html" %}` und füllt `{% block content %}`
- Deutsche Beschriftungen, freundlich und einfach — Zielgruppe sind Pflegekräfte,
  keine Entwickler. Keine Fachbegriffe wie "Entity", "Submit", "ID".
- Vorhandene CSS-Klassen nutzen (style.css): `card`, `person-list`, `person-card`,
  `avatar`, `biografie`, `wunsch-liste`, `btn`, `btn-secondary`, `hinweis`,
  `erfolg`, `leer`, `lead`, `muted`
- Kein `<style>` und kein `<script>` im Template — kein Inline-CSS, kein Inline-JS
- Niemals echte Personendaten in Beispielen
