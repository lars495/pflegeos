---
id: T041
title: Übergabe-Block pro Bewohner:in anzeigen (Biografie, Wünsche, Wohlbefinden)
roadmap_item: Recherche 2026-10-29 — Wunsch- und Biografie-Block in der Übergabeansicht
depends_on:
- T040
- T033
- T022
- T005
target_files:
- apps/api/ui/uebergabe_profil.py
- apps/api/templates/uebergabe_profil.html
- apps/api/web.py
context_files:
- apps/api/web.py
- apps/api/ui/notizen.py
- apps/api/ui/bewohner.py
- apps/api/models/resident.py
- apps/api/models/beobachtung.py
- apps/api/models/uebergabe_notiz.py
- apps/api/models/uebergabe_profil.py
- tests/task_tests/test_t041_ui_uebergabe_block.py
test_command: pytest -q tests/task_tests/test_t041_ui_uebergabe_block.py
max_attempts: 3
attempts_used: 0
---

Neue Seite `GET /ui/bewohner/{resident_id}/uebergabe`: die Übergabeansicht **einer** Person.
Die Person steht oben (Biografie, Wünsche, Wohlbefinden), danach erst die Auffälligkeiten
und die freigegebenen Notizen. Die Felder werden aus dem Bewohnerprofil vorbefüllt.
Die Seite **schreibt nichts** in die Datenbank (die Pflegekraft entscheidet; Bearbeiten folgt in T042).

**Neuer Bereich** — drei Dateien:

1. `apps/api/ui/uebergabe_profil.py` (neu, eigener `router = APIRouter()`)
2. `apps/api/templates/uebergabe_profil.html` (neu)
3. `apps/api/web.py` — **komplett ausgeben, nur zwei Änderungen**: `uebergabe_profil` in den
   Import `from apps.api.ui import ...` aufnehmen und ans Ende der Liste `BEREICHE` anhängen.
   Alles andere unverändert lassen.

## apps/api/ui/uebergabe_profil.py

Imports im Stil von `apps/api/ui/notizen.py` (`APIRouter, Depends, HTTPException, Request`,
`HTMLResponse`, `select`, `AsyncSession`, `get_session`, `templates` aus `apps.api.ui.common`)
sowie `Resident`, `Beobachtung`, `UebergabeNotiz`, `UebergabeProfil`.
Wie die Biografie und die Wünsche einer Person geladen werden, steht in
`apps/api/models/resident.py` und `apps/api/ui/bewohner.py` — **dasselbe Feld und dieselbe
Abfrage verwenden, nichts neu erfinden.**

Hilfsfunktionen (exakt diese Namen):

```python
def _norm(text) -> str:
    """None → ''; '\\r\\n' → '\\n'; strip()."""

def _zeilen(text: str) -> list[str]:
    """Nicht-leere, gestrippte Zeilen: [z.strip() for z in text.splitlines() if z.strip()]"""

async def vorbefuellung(session, person) -> dict[str, str]:
    """Texte aus dem Bewohnerprofil. Schlüssel: 'biografie', 'wuensche', 'wohlbefinden'. Jeder Wert ist _norm()-normalisiert."""
```
`vorbefuellung`:
- `biografie`: das Biografie-Feld der Person. Ist es ein Text → `_norm`. Ist es eine Liste → die
  Einträge (als Text, leere weglassen) mit `"\n"` verbinden. Fehlt der Wert → `""`.
- `wuensche`: **alle** Wünsche der Person (nicht filtern, auch keine als „unerfüllbar" oder
  „erledigt" ausblenden), die Wunsch-Texte mit `"\n"` verbunden, in der Reihenfolge wie im Profil.
- `wohlbefinden`: gibt es im Resident-Modell ein Feld, dessen Name `wohlbefinden` oder `stimmung`
  enthält, dessen Text; sonst `""`.

```python
async def _texte(session, person) -> dict[str, str]:
    """Wirksame Texte: je Schlüssel der Wert aus UebergabeProfil (Zeile mit resident_id == person.id),
    wenn er nicht None ist (auch '' zählt!), sonst der Wert aus vorbefuellung()."""

async def _seite(request, session, person, fehler=None, status_code=200):
    ...
```
`_seite` lädt:
- `texte = await _texte(session, person)`
- `beobachtungen`: die letzten 10 `Beobachtung` dieser Person, `created_at` absteigend
- `notizen`: die letzten 10 `UebergabeNotiz` dieser Person mit `status == "freigegeben"`, `created_at` absteigend

und gibt zurück:
```python
templates.TemplateResponse(request, "uebergabe_profil.html", {
    "person": person, "fehler": fehler, "texte": texte,
    "biografie_zeilen": _zeilen(texte["biografie"]),
    "wuensche_zeilen": _zeilen(texte["wuensche"]),
    "wohlbefinden_zeilen": _zeilen(texte["wohlbefinden"]),
    "beobachtungen": beobachtungen, "notizen": notizen,
}, status_code=status_code)
```

Route:
```python
@router.get("/ui/bewohner/{resident_id}/uebergabe", response_class=HTMLResponse)
async def ui_uebergabe_profil(resident_id: str, request: Request, session: AsyncSession = Depends(get_session)):
```
Person laden (`session.get(Resident, resident_id)`); fehlt sie: `HTTPException(404, "Bewohner:in nicht gefunden")`;
sonst `return await _seite(request, session, person)`.
Alle Abfragen **strikt nach `resident_id` der Person** — keine Daten anderer Personen.

## apps/api/templates/uebergabe_profil.html

`{% extends "base.html" %}`, `{% block title %}PflegeOS — Übergabe {{ person.name }}{% endblock %}`,
Inhalt in `{% block content %}`. Reihenfolge exakt:

1. `<div class="card">` — darin `<span class="avatar">{{ person.name|initialen }}</span>` und `<h1>{{ person.name }}</h1>`.
2. Bei `fehler`: `<p class="hinweis">{{ fehler }}</p>`.
3. `<p class="muted">Vorbefüllt aus dem Profil. Die Pflegekraft entscheidet, was in der Übergabe steht.</p>`
4. `<p class="muted">Hypothese: Diese Übergabe-Struktur ist an I-PASS angelehnt, in der Langzeitpflege aber nicht belegt. Wir prüfen gemeinsam, ob sie hilft.</p>`
5. `<h2>Wer ich bin</h2>` — dann `biografie_zeilen` als `<ul class="wunsch-liste"><li>…</li></ul>`;
   leer: `<p class="leer">Noch nichts eingetragen.</p>`
6. `<h2>Das wünsche ich mir</h2>` — `wuensche_zeilen` genauso.
7. `<h2>Wie es mir heute geht</h2>` — `wohlbefinden_zeilen` genauso.
8. `<h2>Auffälligkeiten</h2>` — je Beobachtung eine `<div class="card">` mit
   `{{ b.kategorie }}: {{ b.notiz }}` und `<span class="muted">{{ b.author }}</span>`;
   leer: `<p class="leer">Nichts gemeldet.</p>`
9. `<h2>Notizen aus der letzten Schicht</h2>` — je Notiz eine `<div class="card">` mit
   `{{ n.text }}` und `<span class="muted">{{ n.author }}</span>`;
   leer: `<p class="leer">Keine freigegebenen Notizen.</p>`
10. `<p><a href="/ui/bewohner/{{ person.id }}" class="btn-secondary">Zum Profil</a></p>`, dann `</div>`.

Alle Ausgaben normal per `{{ … }}` (Auto-Escaping nicht abschalten, kein `|safe`).

**Gestaltungsregeln:** Deutsche, einfache Beschriftungen; nur vorhandene CSS-Klassen
(`card`, `avatar`, `wunsch-liste`, `btn`, `btn-secondary`, `hinweis`, `leer`, `muted`);
kein `<style>`, kein `<script>`, kein Inline-CSS/JS; keine echten Personendaten in Beispielen.

*Bewusst nicht Teil dieser Task:* Bearbeiten (T042) und ein Link vom Profil auf diese Seite.
