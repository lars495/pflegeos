---
id: T017
title: Wunsch festhalten (ohne Seitenwechsel)
roadmap_item: Bewohner-Profil mit Biografie (Lebensgeschichte, Beruf, Werte)
depends_on:
- T016
target_files:
- apps/api/templates/_wuensche.html
- apps/api/web.py
context_files:
- apps/api/web.py
- apps/api/templates/_biografie.html
- apps/api/templates/bewohner_detail.html
- tests/task_tests/test_t017_ui_wunsch_hinzufuegen.py
test_command: pytest -q tests/task_tests/test_t017_ui_wunsch_hinzufuegen.py
max_attempts: 3
attempts_used: 1
completed_at: '2026-08-28'
---

Wünsche sind ein Kernstück der Personenzentrierung — sie dürfen nie verloren
gehen. Ein Eingabefeld direkt auf der Profilseite, ohne Seitenwechsel (HTMX).

**In `apps/api/web.py`** (komplett neu ausgeben, bestehende Routen behalten):

```python
@router.post("/ui/bewohner/{resident_id}/wuensche", response_class=HTMLResponse)
async def ui_wunsch_hinzufuegen(
    resident_id: str, request: Request,
    wunsch: str = Form(""),
    session: AsyncSession = Depends(get_session),
):
    person = await session.get(Resident, resident_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Bewohner:in nicht gefunden")
    if wunsch.strip():
        # neue Liste zuweisen, nicht .append() — sonst merkt SQLAlchemy
        # die Änderung am JSON-Feld nicht
        person.wuensche = [*person.wuensche, wunsch.strip()]
        await session.commit()
        await session.refresh(person)
    return templates.TemplateResponse(request, "_wuensche.html", {"person": person})
```

**In `apps/api/templates/_wuensche.html`** (Fragment, kein `extends`!):

```jinja
<div id="wuensche-block">
  {% if person.wuensche %}
    <ul class="wunsch-liste">
      {% for w in person.wuensche %}<li>{{ w }}</li>{% endfor %}
    </ul>
  {% else %}
    <p class="leer">Noch kein Wunsch festgehalten.</p>
  {% endif %}
  <form hx-post="/ui/bewohner/{{ person.id }}/wuensche"
        hx-target="#wuensche-block" hx-swap="outerHTML">
    <label for="wunsch">Was wünscht sich diese Person?</label>
    <input type="text" id="wunsch" name="wunsch"
           placeholder="Zum Beispiel: einmal wieder ans Meer">
    <button type="submit" class="btn">Wunsch festhalten</button>
  </form>
</div>
```

Zusätzlich in `bewohner_detail.html` den Wünsche-Abschnitt ersetzen durch
`{% include "_wuensche.html" %}`.

**Gestaltungsregeln (gelten für jede Seite):**
- Template beginnt mit `{% extends "base.html" %}` und füllt `{% block content %}`
- Deutsche Beschriftungen, freundlich und einfach — Zielgruppe sind Pflegekräfte,
  keine Entwickler. Keine Fachbegriffe wie "Entity", "Submit", "ID".
- Vorhandene CSS-Klassen nutzen (style.css): `card`, `person-list`, `person-card`,
  `avatar`, `biografie`, `wunsch-liste`, `btn`, `btn-secondary`, `hinweis`,
  `erfolg`, `leer`, `lead`, `muted`
- Kein `<style>` und kein `<script>` im Template — kein Inline-CSS, kein Inline-JS
- Niemals echte Personendaten in Beispielen
