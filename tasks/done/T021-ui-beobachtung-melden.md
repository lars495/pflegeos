---
id: T021
title: Beobachtung melden (Formular)
roadmap_item: Recherche 2026-10-05 — Stop-and-Watch-Karte im Bewohnerprofil
depends_on:
- T020
target_files:
- apps/api/templates/beobachtung_neu.html
- apps/api/web.py
context_files:
- apps/api/web.py
- apps/api/templates/bewohner_neu.html
- apps/api/models/beobachtung.py
- apps/api/audit.py
- tests/task_tests/test_t021_ui_beobachtung_melden.py
test_command: pytest -q tests/task_tests/test_t021_ui_beobachtung_melden.py
max_attempts: 3
attempts_used: 1
completed_at: '2026-10-05'
---

Ein kurzes Formular, mit dem jede Person im Team eine Veränderung melden kann —
in wenigen Sekunden, ohne Fachsprache.

**In `apps/api/web.py`** (komplett neu ausgeben, alle bestehenden Routen behalten):

1. Auf Modulebene eine Konstante (genau diese Texte):
```python
BEOBACHTUNG_KATEGORIEN = [
    "wirkt anders als sonst",
    "isst oder trinkt weniger",
    "braucht mehr Hilfe als sonst",
    "ist unruhiger oder ängstlicher",
    "schläft mehr oder ist schläfrig",
    "hat Schmerzen geäußert",
    "freut sich über etwas Besonderes",
]
```
(Die letzte Kategorie ist Absicht: Auch Gutes ist eine Beobachtung.)

2. Imports: `from apps.api.models.beobachtung import Beobachtung` und
   `from apps.api.audit import log_action`

3. Zwei Routen — **vor** der Route `/ui/bewohner/{resident_id}` einfügen:
```python
@router.get("/ui/bewohner/{resident_id}/beobachtung", response_class=HTMLResponse)
async def ui_beobachtung_formular(resident_id: str, request: Request,
                                  session: AsyncSession = Depends(get_session)):
    person = await session.get(Resident, resident_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Bewohner:in nicht gefunden")
    return templates.TemplateResponse(request, "beobachtung_neu.html",
        {"person": person, "kategorien": BEOBACHTUNG_KATEGORIEN})

@router.post("/ui/bewohner/{resident_id}/beobachtung")
async def ui_beobachtung_speichern(resident_id: str, request: Request,
        author: str = Form(""), kategorie: str = Form(""), notiz: str = Form(""),
        session: AsyncSession = Depends(get_session)):
    person = await session.get(Resident, resident_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Bewohner:in nicht gefunden")
    if not author.strip() or kategorie not in BEOBACHTUNG_KATEGORIEN:
        return templates.TemplateResponse(request, "beobachtung_neu.html",
            {"person": person, "kategorien": BEOBACHTUNG_KATEGORIEN,
             "fehler": "Bitte Kürzel und eine Beobachtung auswählen."})
    b = Beobachtung(resident_id=resident_id, author=author.strip(),
                    kategorie=kategorie, notiz=notiz.strip())
    session.add(b)
    await session.flush()
    await log_action(session, actor=author.strip(), action="beobachtung.created",
                     resource_type="resident", resource_id=resident_id)
    await session.commit()
    return RedirectResponse(f"/ui/bewohner/{resident_id}", status_code=303)
```

**In `apps/api/templates/beobachtung_neu.html`:**
- Überschrift „Mir ist etwas aufgefallen" und darunter `{{ person.name }}`
- Bei `fehler`: `<p class="hinweis">{{ fehler }}</p>`
- `<form method="post">` mit: Feld `author` (Text, Beschriftung „Dein Kürzel"),
  je Kategorie ein Radio-Button `name="kategorie" value="{{ k }}"` mit `<label>`
  und dem Kategorietext, Feld `notiz` (textarea, „Möchtest du etwas ergänzen? (freiwillig)")
- Knopf „Beobachtung weitergeben" (`class="btn"`), Link zurück auf `/ui/bewohner/{{ person.id }}`

**Gestaltungsregeln (gelten für jede Seite):**
- Template beginnt mit `{% extends "base.html" %}` und füllt `{% block content %}`
- Deutsche Beschriftungen, freundlich und einfach — Zielgruppe sind Pflegekräfte,
  keine Entwickler. Keine Fachbegriffe wie "Entity", "Submit", "ID".
- Vorhandene CSS-Klassen nutzen (style.css): `card`, `person-list`, `person-card`,
  `avatar`, `biografie`, `wunsch-liste`, `btn`, `btn-secondary`, `hinweis`,
  `erfolg`, `leer`, `lead`, `muted`
- Kein `<style>` und kein `<script>` im Template — kein Inline-CSS, kein Inline-JS
- Niemals echte Personendaten in Beispielen
