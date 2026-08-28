---
id: T019
title: Meine Reflexionen ansehen
roadmap_item: Reflexions-Tool (60-Sek nach Schicht)
depends_on: [T018]
target_files:
  - apps/api/templates/reflexion_meine.html
  - apps/api/web.py
context_files:
  - apps/api/web.py
  - apps/api/templates/reflexion.html
  - apps/api/models/reflection.py
  - tests/task_tests/test_t019_ui_meine_reflexionen.py
test_command: pytest -q tests/task_tests/test_t019_ui_meine_reflexionen.py
max_attempts: 3
attempts_used: 0
---

Die eigenen Reflexionen unter `/ui/reflexion/meine?author=KÜRZEL`.

**Sicherheitsregel (nicht verhandelbar):** Es dürfen ausschließlich Einträge des
angefragten Kürzels erscheinen. Ohne `author` werden **keine** Einträge gezeigt —
niemals alle. Reflexionen anderer Pflegekräfte sind tabu.

**ACHTUNG Reihenfolge:** Diese Route muss in `web.py` **vor** einer eventuellen
Route `/ui/reflexion/{...}` stehen.

**In `apps/api/web.py`** (komplett neu ausgeben, bestehende Routen behalten):

```python
@router.get("/ui/reflexion/meine", response_class=HTMLResponse)
async def ui_meine_reflexionen(
    request: Request, author: str = "", session: AsyncSession = Depends(get_session)
):
    eintraege = []
    if author.strip():
        result = await session.execute(
            select(Reflection)
            .where(Reflection.author == author.strip())
            .order_by(Reflection.created_at.desc())
        )
        eintraege = result.scalars().all()
    return templates.TemplateResponse(
        request, "reflexion_meine.html", {"eintraege": eintraege, "author": author}
    )
```

**In `apps/api/templates/reflexion_meine.html`:**
- Überschrift „Meine Reflexionen"
- Sind keine Einträge da: `<p class="leer">Noch keine Reflexionen.</p>`
  (das Wort „noch keine" muss vorkommen)
- Sonst je Eintrag eine `<div class="card">` mit den Abschnitten
  „Gut lief", „Schwierig war", „Ich nehme mit" — leere Felder weglassen
- Link zurück auf `/ui/reflexion` („Neue Reflexion schreiben", `class="btn"`)

**Gestaltungsregeln (gelten für jede Seite):**
- Template beginnt mit `{% extends "base.html" %}` und füllt `{% block content %}`
- Deutsche Beschriftungen, freundlich und einfach — Zielgruppe sind Pflegekräfte,
  keine Entwickler. Keine Fachbegriffe wie "Entity", "Submit", "ID".
- Vorhandene CSS-Klassen nutzen (style.css): `card`, `person-list`, `person-card`,
  `avatar`, `biografie`, `wunsch-liste`, `btn`, `btn-secondary`, `hinweis`,
  `erfolg`, `leer`, `lead`, `muted`
- Kein `<style>` und kein `<script>` im Template — kein Inline-CSS, kein Inline-JS
- Niemals echte Personendaten in Beispielen
