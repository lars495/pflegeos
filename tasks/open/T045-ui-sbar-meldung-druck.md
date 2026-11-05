---
id: T045
title: Druck- und Faxansicht der SBAR-Meldung und Einstieg im Profil
roadmap_item: Recherche 2026-10-29 — SBAR-Vorlage für die Meldung an Ärzt:innen
depends_on:
  - T044
target_files:
  - apps/api/ui/sbar_meldung.py
  - apps/api/templates/sbar_druck.html
  - apps/api/templates/bewohner_detail.html
context_files:
  - apps/api/ui/sbar_meldung.py
  - apps/api/templates/bewohner_detail.html
  - apps/api/models/sbar_meldung.py
  - tests/task_tests/test_t045_ui_sbar_meldung_druck.py
test_command: pytest -q tests/task_tests/test_t045_ui_sbar_meldung_druck.py
max_attempts: 3
attempts_used: 0
---

Eine **gespeicherte** SBAR-Meldung lässt sich als schlichte Seite zum Drucken oder
Faxen öffnen. Außerdem bekommt das Bewohner-Profil den Einstieg zur Vorlage.

## `apps/api/ui/sbar_meldung.py`
(komplett neu ausgeben, bestehende Routen aus T044 unverändert lassen). Neue Route:

```python
@router.get("/ui/sbar-meldung/{meldung_id}/druck", response_class=HTMLResponse)
async def ui_sbar_meldung_druck(meldung_id: str, request: Request, an: str = "", session: AsyncSession = Depends(get_session)):
```
- `SbarMeldung` per `session.get` laden, sonst 404 („Meldung nicht gefunden“).
- `Resident` per `session.get(Resident, meldung.resident_id)` laden, sonst 404.
- `templates.TemplateResponse(request, "sbar_druck.html", {"meldung": meldung, "person": person, "an": an.strip()})`.
- Nur lesen: nichts ändern, nichts speichern.

## `apps/api/templates/sbar_druck.html`
Eigenständige, farb- und bildlose Seite (**kein** `extends`), damit sie sich sauber
drucken und faxen lässt: `<!doctype html><html lang="de">`, `<head>` mit
`<meta charset="utf-8">` und `<title>SBAR-Meldung</title>`. Kein `<style>`, kein
`<script>`, kein `style=`-Attribut, keine Bilder, keine HTMX-Attribute.

Inhalt im `<body>` in dieser Reihenfolge, Autoescaping bleibt an:
1. `<h1>Meldung an Ärzt:in (SBAR)</h1>`
2. Ist `an` nicht leer: `<p>An: {{ an }}</p>`
3. `<p>` mit dem Namen der Person, dazu `, Zimmer <zimmer>` falls gesetzt und
   `, geb. am <geburtsdatum>` falls gesetzt
4. `<p>Erstellt am {{ meldung.created_at.strftime("%d.%m.%Y %H:%M") }} von {{ meldung.author }}</p>`
5. Vier Abschnitte, je `<h2>` und darunter ein `<p>`, genau diese Überschriften:
   **Situation**, **Hintergrund**, **Einschätzung**, **Empfehlung** (Inhalt jeweils aus
   `meldung.situation`, `.hintergrund`, `.einschaetzung`, `.empfehlung`).
   Zeilenumbrüche bleiben erhalten, **ohne** `|safe`:
   `{% for zeile in text.splitlines() %}{{ zeile }}<br>{% endfor %}`
6. `<p>Zum Drucken oder Faxen im Browser „Drucken“ wählen (Strg + P).</p>`
7. `<p><a href="/ui/bewohner/{{ person.id }}">Zurück zum Profil</a></p>`

Es werden nur Name, Zimmer, Geburtsdatum und die gespeicherten SBAR-Texte gezeigt —
keine Biografie, keine Wünsche, keine weiteren Profildaten (Datensparsamkeit).

## `apps/api/templates/bewohner_detail.html`
Direkt nach dem Link „Mir ist etwas aufgefallen“ einfügen, sonst nichts ändern:
```jinja
  <p><a href="/ui/bewohner/{{ person.id }}/sbar-meldung" class="btn-secondary">Meldung an Ärzt:in vorbereiten</a></p>
```
