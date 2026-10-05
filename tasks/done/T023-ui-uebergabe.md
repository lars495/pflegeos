---
id: T023
title: Übergabeansicht — die Person als roter Faden
roadmap_item: Recherche 2026-10-05 — Übergabeansicht mit Biografie als roter Faden
depends_on:
- T022
target_files:
- apps/api/templates/uebergabe.html
- apps/api/templates/base.html
- apps/api/web.py
context_files:
- apps/api/web.py
- apps/api/templates/base.html
- apps/api/templates/_beobachtungen.html
- apps/api/models/resident.py
- apps/api/models/beobachtung.py
- tests/task_tests/test_t023_ui_uebergabe.py
test_command: pytest -q tests/task_tests/test_t023_ui_uebergabe.py
max_attempts: 3
attempts_used: 1
completed_at: '2026-10-05'
---

Eine Übergabeseite unter `/ui/uebergabe`. Die Recherche fand kaum Evidenz dafür,
wie eine gute Übergabe im Pflegeheim aussieht — aber den klaren Wunsch, sie bei
der Person beginnen zu lassen statt bei der Problemliste. **Reihenfolge je Person:
Name/Zimmer → Wünsche → Biografie-Auszug → Beobachtungen der letzten 24 Stunden.**

**In `apps/api/web.py`** (komplett neu ausgeben, alles behalten):
```python
import datetime as dt

@router.get("/ui/uebergabe", response_class=HTMLResponse)
async def ui_uebergabe(request: Request, session: AsyncSession = Depends(get_session)):
    personen = (await session.execute(select(Resident).order_by(Resident.zimmer, Resident.name))).scalars().all()
    seit = dt.datetime.utcnow() - dt.timedelta(hours=24)
    beob = (await session.execute(
        select(Beobachtung).where(Beobachtung.created_at >= seit)
        .order_by(Beobachtung.created_at.desc()))).scalars().all()
    je_person: dict[str, list] = {}
    for b in beob:
        je_person.setdefault(b.resident_id, []).append(b)
    return templates.TemplateResponse(request, "uebergabe.html",
        {"personen": personen, "beobachtungen": je_person})
```

**In `apps/api/templates/uebergabe.html`** (`extends "base.html"`):
- Überschrift „Übergabe", darunter `<p class="lead">Wer ist heute wie da?</p>`
- Keine Personen: `<p class="leer">Noch niemand angelegt.</p>`
- Je Person eine `<div class="card">` in genau dieser Reihenfolge:
  1. `<h2>` mit Name, dahinter in `<span class="muted">` „Zimmer …" falls vorhanden
  2. Wünsche als `<ul class="wunsch-liste">` (nur wenn vorhanden)
  3. Biografie gekürzt: `<p class="biografie">{{ p.biografie|truncate(200) }}</p>` (nur wenn vorhanden)
  4. „Seit gestern:" — die Beobachtungen aus `beobachtungen.get(p.id, [])`
     mit Kategorie fett und Notiz; sonst `<p class="muted">Nichts Besonderes gemeldet.</p>`

**In `apps/api/templates/base.html`:** in der Hauptnavigation nach dem Link
„Bewohner:innen" einen Link `<a href="/ui/uebergabe">Übergabe</a>` einfügen.
Sonst nichts an base.html ändern.

**Gestaltungsregeln (gelten für jede Seite):**
- Template beginnt mit `{% extends "base.html" %}` und füllt `{% block content %}`
- Deutsche Beschriftungen, freundlich und einfach — Zielgruppe sind Pflegekräfte,
  keine Entwickler. Keine Fachbegriffe wie "Entity", "Submit", "ID".
- Vorhandene CSS-Klassen nutzen (style.css): `card`, `person-list`, `person-card`,
  `avatar`, `biografie`, `wunsch-liste`, `btn`, `btn-secondary`, `hinweis`,
  `erfolg`, `leer`, `lead`, `muted`
- Kein `<style>` und kein `<script>` im Template — kein Inline-CSS, kein Inline-JS
- Niemals echte Personendaten in Beispielen
