---
id: T016
title: Biografie direkt auf der Seite bearbeiten
roadmap_item: Bewohner-Profil mit Biografie (Lebensgeschichte, Beruf, Werte)
depends_on:
- T014
target_files:
- apps/api/templates/_biografie.html
- apps/api/web.py
context_files:
- apps/api/web.py
- apps/api/templates/bewohner_detail.html
- tests/task_tests/test_t016_ui_biografie_bearbeiten.py
test_command: pytest -q tests/task_tests/test_t016_ui_biografie_bearbeiten.py
max_attempts: 3
attempts_used: 1
completed_at: '2026-08-28'
---

Die Biografie soll ohne Seitenwechsel bearbeitbar sein (HTMX). Es entsteht ein
**Fragment-Template** — also KEIN `{% extends %}`, nur der Abschnitt selbst.

**In `apps/api/web.py`** (komplett neu ausgeben, bestehende Routen behalten):

```python
@router.get("/ui/bewohner/{resident_id}/biografie", response_class=HTMLResponse)
async def ui_biografie_formular(
    resident_id: str, request: Request, session: AsyncSession = Depends(get_session)
):
    person = await session.get(Resident, resident_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Bewohner:in nicht gefunden")
    return templates.TemplateResponse(
        request, "_biografie.html", {"person": person, "bearbeiten": True}
    )

@router.post("/ui/bewohner/{resident_id}/biografie", response_class=HTMLResponse)
async def ui_biografie_speichern(
    resident_id: str, request: Request,
    biografie: str = Form(""),
    session: AsyncSession = Depends(get_session),
):
    person = await session.get(Resident, resident_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Bewohner:in nicht gefunden")
    person.biografie = biografie.strip()
    await session.commit()
    await session.refresh(person)
    return templates.TemplateResponse(
        request, "_biografie.html", {"person": person, "bearbeiten": False}
    )
```

**In `apps/api/templates/_biografie.html`** (Fragment, kein `extends`!):

```jinja
<div id="biografie-block">
  {% if bearbeiten %}
    <form hx-post="/ui/bewohner/{{ person.id }}/biografie"
          hx-target="#biografie-block" hx-swap="outerHTML">
      <label for="biografie">Lebensgeschichte</label>
      <textarea id="biografie" name="biografie">{{ person.biografie }}</textarea>
      <button type="submit" class="btn">Speichern</button>
    </form>
  {% else %}
    <div class="biografie">{{ person.biografie }}</div>
    <button class="btn-secondary"
            hx-get="/ui/bewohner/{{ person.id }}/biografie"
            hx-target="#biografie-block" hx-swap="outerHTML">Bearbeiten</button>
  {% endif %}
</div>
```

Zusätzlich in `bewohner_detail.html` den bisherigen Biografie-Abschnitt ersetzen
durch `{% include "_biografie.html" %}` — dafür beim Rendern der Detailseite
`"bearbeiten": False` mitgeben.

**Gestaltungsregeln (gelten für jede Seite):**
- Template beginnt mit `{% extends "base.html" %}` und füllt `{% block content %}`
- Deutsche Beschriftungen, freundlich und einfach — Zielgruppe sind Pflegekräfte,
  keine Entwickler. Keine Fachbegriffe wie "Entity", "Submit", "ID".
- Vorhandene CSS-Klassen nutzen (style.css): `card`, `person-list`, `person-card`,
  `avatar`, `biografie`, `wunsch-liste`, `btn`, `btn-secondary`, `hinweis`,
  `erfolg`, `leer`, `lead`, `muted`
- Kein `<style>` und kein `<script>` im Template — kein Inline-CSS, kein Inline-JS
- Niemals echte Personendaten in Beispielen
