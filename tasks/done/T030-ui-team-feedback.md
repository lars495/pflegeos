---
id: T030
title: Anonymes Team-Feedback zur Übergabe
roadmap_item: Recherche 2026-10-05 — Team-Reflexion zur Übergabe (anonym)
depends_on:
- T029
- T028
target_files:
- apps/api/templates/team.html
- apps/api/templates/base.html
- apps/api/web.py
context_files:
- apps/api/web.py
- apps/api/templates/base.html
- apps/api/templates/reflexion.html
- apps/api/models/team_feedback.py
- tests/task_tests/test_t030_ui_team_feedback.py
test_command: pytest -q tests/task_tests/test_t030_ui_team_feedback.py
max_attempts: 3
attempts_used: 2
completed_at: '2026-10-05'
---

Eine Seite `/ui/team`, auf der das Team anonym zur Übergabe Rückmeldung gibt —
und gemeinsam sieht, was die anderen geschrieben haben. Damit Antworten in kleinen
Teams nicht zuordenbar sind: **Anzeige erst ab einer Mindestanzahl, ohne Datum und
ohne Uhrzeit, in zufälliger Reihenfolge.**

**In `apps/api/web.py`** (komplett neu ausgeben, alles behalten):
```python
import random
from apps.api.models.team_feedback import TeamFeedback
TEAM_MINDESTANZAHL = 3

@router.get("/ui/team", response_class=HTMLResponse)
async def ui_team(request: Request, session: AsyncSession = Depends(get_session)):
    alle = (await session.execute(select(TeamFeedback))).scalars().all()
    sichtbar = list(alle) if len(alle) >= TEAM_MINDESTANZAHL else []
    random.shuffle(sichtbar)
    return templates.TemplateResponse(request, "team.html", {
        "antworten": sichtbar, "anzahl": len(alle), "mindestanzahl": TEAM_MINDESTANZAHL})

@router.post("/ui/team")
async def ui_team_speichern(gefehlt: str = Form(""), unnoetig: str = Form(""), hilft: str = Form(""),
                            session: AsyncSession = Depends(get_session)):
    if gefehlt.strip() or unnoetig.strip() or hilft.strip():
        session.add(TeamFeedback(gefehlt=gefehlt.strip(), unnoetig=unnoetig.strip(), hilft=hilft.strip()))
        await session.commit()
    return RedirectResponse("/ui/team", status_code=303)
```

**`apps/api/templates/team.html`** (extends base): Überschrift „Unsere Übergabe —
was können wir besser machen?", Kasten `<p class="erfolg">Anonym: Hier wird kein
Name und kein Kürzel gespeichert.</p>`. Formular (`method="post"`) mit drei
textareas: `gefehlt` („Was hat in der Übergabe gefehlt?"), `unnoetig` („Was war
unnötig?"), `hilft` („Was würde uns helfen?"), Knopf „Anonym abgeben". Darunter
Abschnitt „Was das Team sagt": Wenn `antworten` leer: `<p class="muted">Sichtbar
ab {{ mindestanzahl }} Antworten (bisher {{ anzahl }}), damit niemand zuordenbar ist.</p>`.
Sonst je Antwort eine `<div class="card">` mit den nicht-leeren Feldern. **Niemals
`created_at` anzeigen.**

**In `base.html`:** Navigationslink `<a href="/ui/team">Team</a>` nach „Meine Reflexion". Sonst nichts ändern.

**Gestaltungsregeln (gelten für jede Seite):**
- Template beginnt mit `{% extends "base.html" %}` und füllt `{% block content %}`
- Deutsche Beschriftungen, freundlich und einfach — Zielgruppe sind Pflegekräfte,
  keine Entwickler. Keine Fachbegriffe wie "Entity", "Submit", "ID".
- Vorhandene CSS-Klassen nutzen (style.css): `card`, `person-list`, `person-card`,
  `avatar`, `biografie`, `wunsch-liste`, `btn`, `btn-secondary`, `hinweis`,
  `erfolg`, `leer`, `lead`, `muted`
- Kein `<style>` und kein `<script>` im Template — kein Inline-CSS, kein Inline-JS
- Niemals echte Personendaten in Beispielen
