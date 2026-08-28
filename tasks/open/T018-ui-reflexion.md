---
id: T018
title: Reflexion nach der Schicht (Formular)
roadmap_item: Reflexions-Tool (60-Sek nach Schicht)
depends_on: []
target_files:
  - apps/api/templates/reflexion.html
  - apps/api/web.py
context_files:
  - apps/api/web.py
  - apps/api/models/reflection.py
  - apps/api/templates/index.html
  - tests/task_tests/test_t018_ui_reflexion.py
test_command: pytest -q tests/task_tests/test_t018_ui_reflexion.py
max_attempts: 3
attempts_used: 0
---

Das Reflexions-Werkzeug unter `/ui/reflexion` — **für die Pflegekraft, nicht für
die Akte.** Diese Zusicherung muss auf der Seite stehen (Empowerment-Prinzip).

**In `apps/api/web.py`** (komplett neu ausgeben, bestehende Routen behalten):

```python
from apps.api.models.reflection import Reflection

@router.get("/ui/reflexion", response_class=HTMLResponse)
async def ui_reflexion_formular(request: Request):
    return templates.TemplateResponse(request, "reflexion.html", {})

@router.post("/ui/reflexion")
async def ui_reflexion_speichern(
    request: Request,
    author: str = Form(""),
    gut: str = Form(""),
    schwierig: str = Form(""),
    mitnehmen: str = Form(""),
    session: AsyncSession = Depends(get_session),
):
    if not author.strip():
        return templates.TemplateResponse(
            request, "reflexion.html", {"fehler": "Bitte dein Kürzel eintragen."}
        )
    session.add(Reflection(
        author=author.strip(), gut=gut.strip(),
        schwierig=schwierig.strip(), mitnehmen=mitnehmen.strip(),
    ))
    await session.commit()
    return RedirectResponse(f"/ui/reflexion/meine?author={author.strip()}", status_code=303)
```

**In `apps/api/templates/reflexion.html`:**
- Überschrift „60 Sekunden für dich"
- Ein `<p class="erfolg">`-Kasten mit dem Satz:
  **„Das hier ist nur für dich — nicht für die Akte. Niemand liest es ohne deine Erlaubnis."**
  (Der Wortlaut „nur für dich" muss vorkommen.)
- Bei gesetztem `fehler`: `<p class="hinweis">{{ fehler }}</p>`
- `<form method="post">` mit vier Feldern, jeweils mit `<label>`:
  `author` (Text, „Dein Kürzel"),
  `gut` (textarea, „Was lief heute gut?"),
  `schwierig` (textarea, „Was war schwierig?"),
  `mitnehmen` (textarea, „Was nimmst du mit?")
- Knopf „Reflexion speichern" (`class="btn"`)

**Gestaltungsregeln (gelten für jede Seite):**
- Template beginnt mit `{% extends "base.html" %}` und füllt `{% block content %}`
- Deutsche Beschriftungen, freundlich und einfach — Zielgruppe sind Pflegekräfte,
  keine Entwickler. Keine Fachbegriffe wie "Entity", "Submit", "ID".
- Vorhandene CSS-Klassen nutzen (style.css): `card`, `person-list`, `person-card`,
  `avatar`, `biografie`, `wunsch-liste`, `btn`, `btn-secondary`, `hinweis`,
  `erfolg`, `leer`, `lead`, `muted`
- Kein `<style>` und kein `<script>` im Template — kein Inline-CSS, kein Inline-JS
- Niemals echte Personendaten in Beispielen
