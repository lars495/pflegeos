---
id: T035
title: Frühwarnkarte ausfüllen und Fragen anpassen
roadmap_item: Recherche 2026-10-29 — Stop-and-Watch-Frühwarnkarte für alle Qualifikationsstufen
depends_on:
- T034
target_files:
- apps/api/ui/fruehwarnung.py
- apps/api/templates/fruehwarnung_neu.html
- apps/api/web.py
context_files:
- apps/api/web.py
- apps/api/ui/notizen.py
- apps/api/ui/common.py
- apps/api/models/fruehwarnung.py
- apps/api/audit.py
- apps/api/templates/sbar.html
- tests/task_tests/test_t035_ui_fruehwarnung_melden.py
test_command: pytest -q tests/task_tests/test_t035_ui_fruehwarnung_melden.py
max_attempts: 3
attempts_used: 1
completed_at: '2026-10-29'
---

Eine kurze Karte mit Ja-Fragen (Kästchen zum Ankreuzen) und einem Freitext, die jede Person im
Team — auch Pflegehilfskräfte — direkt am Bewohnerprofil ausfüllen kann. Die Fragen sind ein
Vorschlag; das Team kann sie ein- und ausschalten und eigene ergänzen.

Prinzipien: Person zuerst (Name und Avatar oben), Pflegekräfte entscheiden (aus einer Meldung
wird nichts automatisch abgeleitet), Privatsphäre (der Audit-Eintrag enthält keinen Inhalt),
gleichwertige Stimme (keine Rolle, keine Punktzahl, keine Ampel).

## Neue Datei `apps/api/ui/fruehwarnung.py`

Muster: `apps/api/ui/notizen.py`. Eigener `router = APIRouter()`. Importe u. a.
`json`, `uuid`, `select`, `AsyncSession`, `get_session`, `log_action`, `Resident`,
`templates` aus `apps.api.ui.common` sowie
`FruehwarnFrage, FruehwarnMeldung, standardfragen_sicherstellen` aus `apps.api.models.fruehwarnung`.

Hilfsfunktion:
```python
async def _seite(request, session, person, erfolg="", hinweistext=""):
    await standardfragen_sicherstellen(session)
    fragen = (await session.execute(select(FruehwarnFrage)
        .order_by(FruehwarnFrage.position, FruehwarnFrage.id))).scalars().all()
    return templates.TemplateResponse(request, "fruehwarnung_neu.html",
        {"person": person, "fragen": fragen, "erfolg": erfolg, "hinweistext": hinweistext})
```
`fragen` enthält **alle** Fragen (aktive und ausgeschaltete); das Template unterscheidet.

Routen (Person jeweils mit `session.get(Resident, resident_id)` laden, sonst
`HTTPException(404, "Bewohner:in nicht gefunden")`):

1. `GET /ui/bewohner/{resident_id}/fruehwarnung` → `_seite(...)`.
2. `POST /ui/bewohner/{resident_id}/fruehwarnung` mit
   `author: str = Form("")`, `ja: list[str] = Form(default=[])`, `freitext: str = Form("")`:
   - `author.strip()` leer → nichts speichern, `_seite(..., hinweistext="Bitte trag dein Kürzel ein.")`.
   - Zuerst `standardfragen_sicherstellen(session)`. Ausgewählt = **aktive** `FruehwarnFrage`n,
     deren `id` in `ja` steht, in der Reihenfolge `position`. Unbekannte oder ausgeschaltete IDs
     werden ignoriert.
   - Ist Ausgewählt leer **und** `freitext.strip()` leer → nichts speichern,
     `_seite(..., hinweistext="Bitte kreuze etwas an oder schreib auf, was dir aufgefallen ist.")`.
   - Sonst: `FruehwarnMeldung(resident_id=resident_id, author=author.strip(),
     auffaelligkeiten=json.dumps([f.text for f in ausgewaehlt], ensure_ascii=False),
     freitext=freitext.strip())` speichern. Dann
     `log_action(session, actor=author.strip(), action="fruehwarnung.gemeldet", resource_type="resident", resource_id=resident_id)`.
     **Der Audit-Eintrag enthält keinen Inhalt der Meldung** (Privatsphäre). Dann commit und
     `_seite(..., erfolg="Danke! Deine Meldung ist gespeichert und erscheint in der nächsten Übergabe.")`.
   - Aus der Meldung wird **nichts automatisch** abgeleitet (keine Beobachtung, keine Notiz,
     keine Eskalation). Was daraus folgt, entscheidet das Team.
3. `POST /ui/bewohner/{resident_id}/fruehwarnung/fragen` mit `text: str = Form("")`:
   Zuerst `standardfragen_sicherstellen`. Ist `text.strip()` nicht leer, wird eine neue
   `FruehwarnFrage` angelegt: `schluessel="eigene_" + uuid.uuid4().hex[:8]`, `text=text.strip()`,
   `aktiv=True`, `position` = größte vorhandene Position + 1. Dann
   `log_action(session, actor="team", action="fruehwarnung.frage_geaendert", resource_type="resident", resource_id=resident_id)`
   und commit. Antwort in jedem Fall:
   `RedirectResponse(url=f"/ui/bewohner/{resident_id}/fruehwarnung", status_code=303)`.
4. `POST /ui/bewohner/{resident_id}/fruehwarnung/fragen/{frage_id}/umschalten`:
   Frage per `session.get(FruehwarnFrage, frage_id)` laden (404 `"Frage nicht gefunden"`),
   `aktiv = not aktiv`,
   `log_action(..., actor="team", action="fruehwarnung.frage_geaendert", resource_type="resident", resource_id=resident_id)`,
   commit, Redirect 303 wie oben.

## `apps/api/web.py`
Nur ergänzen: `fruehwarnung` in den Import `from apps.api.ui import ...` aufnehmen und
`fruehwarnung` am Ende der Liste `BEREICHE` anfügen. Alles andere unverändert lassen.

## `apps/api/templates/fruehwarnung_neu.html` (neu)
Beginnt mit `{% extends "base.html" %}`, füllt `{% block title %}` und `{% block content %}`.
Alles in einer `<div class="card">`:

- Kopf mit Person zuerst: `<span class="avatar">{{ person.name|initialen }}</span>` und
  `<h1>{{ person.name }}</h1>`, darunter `<p class="lead">Mir ist etwas aufgefallen</p>`.
- `<p class="muted">Das ist ein Hinweis zum genaueren Hinschauen, keine Diagnose. Jede Stimme im Team zählt gleich. Was daraus folgt, entscheidet ihr gemeinsam.</p>`
- Wenn `erfolg`: `<p class="erfolg">{{ erfolg }}</p>`. Wenn `hinweistext`: `<p class="hinweis">{{ hinweistext }}</p>`.
- Formular `<form method="post" action="/ui/bewohner/{{ person.id }}/fruehwarnung">` (normales
  Formular, kein HTMX nötig):
  - `<label for="author">Dein Kürzel</label>` + `<input type="text" id="author" name="author">`
  - für jede Frage `f` mit `f.aktiv`:
    `<input type="checkbox" name="ja" value="{{ f.id }}" id="frage-{{ f.id }}">` und
    `<label for="frage-{{ f.id }}">{{ f.text }}</label>`
    (die `id="frage-…"` kommt **nur** bei aktiven Fragen und nur hier im Formular vor)
  - `<label for="freitext">Was ist dir sonst noch aufgefallen?</label>` +
    `<textarea id="freitext" name="freitext"></textarea>`
  - `<button type="submit" class="btn">Meldung speichern</button>`
- Abschnitt `<h2>Fragen anpassen</h2>` mit
  `<p class="muted">Diese Fragen sind ein Vorschlag. Ihr könnt sie als Team ändern.</p>`:
  - je Frage eine Zeile: Text, daneben „an" bzw. „aus", und ein kleines Formular
    `method="post" action="/ui/bewohner/{{ person.id }}/fruehwarnung/fragen/{{ f.id }}/umschalten"`
    mit Knopf „Ausschalten" (wenn aktiv) bzw. „Einschalten" (wenn nicht), Klasse `btn-secondary`.
  - Formular `method="post" action="/ui/bewohner/{{ person.id }}/fruehwarnung/fragen"` mit
    `<label for="neue-frage">Eigene Frage ergänzen</label>`,
    `<input type="text" id="neue-frage" name="text">` und Knopf „Frage hinzufügen".
- Unten `<p><a href="/ui/bewohner/{{ person.id }}" class="btn-secondary">Zurück zum Profil</a></p>`.
- Das Wort „gespeichert" darf auf der Seite **nur** in der Erfolgsmeldung vorkommen
  (der Knopf heißt „Meldung speichern").

**Hinweis zum Routenbestand:** Die neuen Pfade (GET und POST `/ui/bewohner/{resident_id}/fruehwarnung`,
POST `.../fruehwarnung/fragen`, POST `.../fruehwarnung/fragen/{frage_id}/umschalten`) trägt Lars nach dem
Merge in `tests/test_routen_bestand.py` ein (Dateilimit der Task). Diese Datei nicht ändern.

**Gestaltungsregeln:** Deutsche, freundliche Beschriftungen ohne Fachbegriffe. Nur vorhandene
CSS-Klassen (`card`, `avatar`, `btn`, `btn-secondary`, `hinweis`, `erfolg`, `lead`, `muted`).
Kein `<style>`, kein `<script>`, kein Inline-CSS/JS. Keine echten Personendaten in Beispielen.
