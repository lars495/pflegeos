---
id: T044
title: SBAR-Vorlage aus Frühwarnung erzeugen, bearbeiten und nach Bestätigung speichern
roadmap_item: Recherche 2026-10-29 — SBAR-Vorlage für die Meldung an Ärzt:innen
depends_on:
- T043
- T036
target_files:
- apps/api/ui/sbar_meldung.py
- apps/api/templates/sbar_meldung.html
- apps/api/web.py
context_files:
- apps/api/web.py
- apps/api/ui/notizen.py
- apps/api/models/sbar_meldung.py
- apps/api/models/fruehwarnung.py
- apps/api/models/resident.py
- apps/api/audit.py
- tests/task_tests/test_t044_ui_sbar_meldung_vorlage.py
test_command: pytest -q tests/task_tests/test_t044_ui_sbar_meldung_vorlage.py
max_attempts: 3
attempts_used: 2
---

Aus einer Frühwarnung („Mir ist etwas aufgefallen“, Stop-and-Watch) erzeugt die
Pflegekraft mit einem Klick eine SBAR-Vorlage (Situation, Hintergrund, Einschätzung,
Empfehlung) für die Meldung an eine Ärzt:in. Die Vorlage ist vorbefüllt und von Hand
änderbar. **Gespeichert wird erst nach ausdrücklicher Bestätigung** durch die Pflegekraft.

Das ist ein neuer Bereich: neue Datei `apps/api/ui/sbar_meldung.py` mit eigenem
`router = APIRouter()` (Muster: `apps/api/ui/notizen.py`). Die bestehende Seite
`/ui/bewohner/{resident_id}/sbar` und ihre Dateien bleiben unberührt.

**In `apps/api/web.py`** (komplett neu ausgeben, alles andere unverändert lassen):
`sbar_meldung` in den Import `from apps.api.ui import ...` aufnehmen und am Ende der
Liste `BEREICHE` anhängen.

## Routen (Parameter heißt immer `resident_id`)

### `GET /ui/bewohner/{resident_id}/sbar-meldung`
Optionaler Query-Parameter `fruehwarnung_id: str = ""`. **Speichert nie etwas.**
- Person laden (`session.get(Resident, resident_id)`), sonst 404.
- Die letzten 5 Frühwarnungen dieser Person laden (Klasse in
  `apps/api/models/fruehwarnung.py` nachlesen; `where resident_id == resident_id`;
  absteigend nach `created_at`, falls die Spalte existiert; unabhängig vom Status).
- Wurde `fruehwarnung_id` angegeben und gehört sie zu einer dieser Frühwarnungen
  **derselben Person**, dient sie als Quelle. Unbekannte Ids und Frühwarnungen
  **anderer Personen** werden still ignoriert (kein Fehler, nichts wird vorbefüllt).
- Hilfsfunktion `_texte(fw) -> list[str]`: alle Spalten der Frühwarnung vom Typ
  `String`/`Text` (über `type(fw).__table__.columns`), **ohne** `id` und `resident_id`,
  nur nicht-leere Werte, in Spaltenreihenfolge.
- Vorbefüllung (`form`-Dict):
  - `situation`: bei Quelle `"\n".join(_texte(fw))`, sonst `""`
  - `hintergrund`: `"<name>"`, dazu `", Zimmer <zimmer>"` falls Zimmer gesetzt, dazu
    `", geb. am <geburtsdatum>"` falls gesetzt. Hat `Resident` ein Biografie-Textfeld
    (siehe `models/resident.py`) mit Inhalt, folgt eine zweite Zeile
    `"Biografie: <erste 300 Zeichen>"`; sonst entfällt sie.
  - `einschaetzung`: **immer `""`** — die Einschätzung trifft die Pflegekraft.
  - `empfehlung`: **immer `""`** — die Empfehlung trifft die Pflegekraft.
  - `author`: `""`, `fruehwarnung_id`: die verwendete Id oder `""`.
- Liste für die Auswahl: je Frühwarnung `{"id": fw.id, "label": " – ".join(_texte(fw))[:80]}`.

### `POST /ui/bewohner/{resident_id}/sbar-meldung`
Formularfelder, alle `Form("")`: `author`, `situation`, `hintergrund`, `einschaetzung`,
`empfehlung`, `fruehwarnung_id`, `bestaetigt`. Alle Werte mit `.strip()`.
Person laden, sonst 404. Dann in dieser Reihenfolge:
1. `bestaetigt != "ja"` → **nichts speichern**; Seite erneut rendern (Status 200) mit den
   eingegebenen Werten in `form` und `hinweis = "Bitte bestätige die Meldung, bevor sie gespeichert wird."`
2. `author` oder `situation` leer → nichts speichern; Seite erneut mit Werten und
   `hinweis = "Bitte trage dein Kürzel und die Situation ein."`
3. Sonst: `SbarMeldung` speichern (`fruehwarnung_id` leer → `None`), danach
   `log_action(session, actor=author, action="sbar_meldung.gespeichert", resource_type="resident", resource_id=resident_id)`,
   commit, Seite mit `gespeichert=<Meldung>` rendern (Status 200, kein Redirect).

## Template `apps/api/templates/sbar_meldung.html`
`{% extends "base.html" %}`, füllt `{% block content %}`. Kontext: `person`, `form`,
`fruehwarnungen`, `hinweis` (str oder None), `gespeichert` (Meldung oder None).
Kein `<style>`, kein `<script>`, kein Inline-CSS, kein HTMX nötig (normales Formular).
Texte freundlich und einfach, Autoescaping bleibt an.

Aufbau, **Person zuerst**: `<span class="avatar">{{ person.name|initialen }}</span>` und
`<h1>Meldung an Ärzt:in vorbereiten</h1>` mit dem Namen der Person darunter.

- Ist `gespeichert` gesetzt: `<div class="card erfolg">` mit dem Wort **Gespeichert**,
  Link `<a href="/ui/sbar-meldung/{{ gespeichert.id }}/druck" class="btn">Druck- oder Faxansicht öffnen</a>`
  und Link zurück zum Profil `/ui/bewohner/{{ person.id }}`. Kein Formular.
- Sonst:
  - Ist `hinweis` gesetzt: `<p class="hinweis">{{ hinweis }}</p>`.
  - `<p class="muted">Das ist ein Entwurf. Gespeichert wird erst, wenn du es bestätigst.</p>`
  - Gibt es `fruehwarnungen`: Überschrift „Aus einer Meldung vorbefüllen“ und je Eintrag
    `<a href="/ui/bewohner/{{ person.id }}/sbar-meldung?fruehwarnung_id={{ f.id }}">{{ f.label }}</a>`.
    Sonst `<p class="leer">Noch keine Meldungen „Mir ist etwas aufgefallen“.</p>`.
  - `<form method="post" action="/ui/bewohner/{{ person.id }}/sbar-meldung">` mit:
    - `<input type="hidden" name="fruehwarnung_id" value="{{ form.fruehwarnung_id }}">`
    - `<input type="text" name="author" value="{{ form.author }}" placeholder="Dein Kürzel">` mit Label „Dein Kürzel“
    - vier `<textarea>` mit **genau** den Namen `situation`, `hintergrund`, `einschaetzung`,
      `empfehlung` (Labels: „Situation – Was ist aufgefallen?“, „Hintergrund – Wer ist die Person?“,
      „Einschätzung – Was denkst du?“, „Empfehlung – Was schlägst du vor?“). Inhalt jeweils
      `{{ form.<name> }}` direkt zwischen `>` und `</textarea>`.
      Bei `einschaetzung` und `empfehlung` steht ein `placeholder` („Deine Einschätzung“ /
      „Dein Vorschlag“).
    - `<input type="checkbox" name="bestaetigt" value="ja" id="bestaetigt">` mit Label
      „Ich habe die Meldung geprüft und möchte sie speichern“
    - `<button type="submit" class="btn">Meldung speichern</button>`

Keine Auth, keine Änderung an bestehenden Tabellen.
