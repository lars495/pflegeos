---
id: T032
title: Übergabe-Notiz schreiben und freigeben
roadmap_item: Recherche 2026-10-05 — Übergabe-Notiz mit Freigabe
depends_on:
- T031
- T030
target_files:
- apps/api/templates/_notizen.html
- apps/api/templates/bewohner_detail.html
- apps/api/web.py
context_files:
- apps/api/web.py
- apps/api/templates/bewohner_detail.html
- apps/api/templates/_wuensche.html
- apps/api/models/uebergabe_notiz.py
- apps/api/audit.py
- tests/task_tests/test_t032_ui_notiz_freigabe.py
test_command: pytest -q tests/task_tests/test_t032_ui_notiz_freigabe.py
max_attempts: 3
attempts_used: 2
completed_at: '2026-10-05'
---

Auf der Profilseite schreibt die Pflegekraft eine Notiz für die nächste Schicht.
Sie ist zunächst ein **Entwurf** und muss ausdrücklich **freigegeben** werden.
Ohne Seitenwechsel (HTMX), Muster wie `_wuensche.html`.

**In `apps/api/web.py`** (komplett neu ausgeben, alles behalten), Import
`from apps.api.models.uebergabe_notiz import UebergabeNotiz`. Hilfsfunktion:
```python
async def _notizen_fragment(request, session, person):
    notizen = (await session.execute(select(UebergabeNotiz)
        .where(UebergabeNotiz.resident_id == person.id)
        .order_by(UebergabeNotiz.created_at.desc()).limit(10))).scalars().all()
    return templates.TemplateResponse(request, "_notizen.html", {"person": person, "notizen": notizen})
```
- `POST /ui/bewohner/{resident_id}/notizen` (`author`, `text` als `Form("")`): Person laden (404);
  nur wenn beide nicht leer: `UebergabeNotiz` (status bleibt "entwurf") speichern; dann `_notizen_fragment`.
- `POST /ui/notizen/{notiz_id}/freigeben`: Notiz laden (`session.get`, 404 wenn fehlt);
  `status = "freigegeben"`, `freigegeben_at = datetime.utcnow()` (aus `datetime` importieren);
  `log_action(session, actor=notiz.author, action="notiz.freigegeben", resource_type="resident", resource_id=notiz.resident_id)`;
  commit; Person laden; `_notizen_fragment`.
- In `ui_bewohner_detail` ebenfalls `notizen` (gleiche Abfrage) mitgeben.

**`apps/api/templates/_notizen.html`** (kein extends), Wurzel `<div id="notizen-block">`:
je Notiz eine `<div class="card">` mit dem Text, `<span class="muted">` mit Kürzel,
und Status: bei "entwurf" das Wort **Entwurf** und ein Knopf
`<button hx-post="/ui/notizen/{{ n.id }}/freigeben" hx-target="#notizen-block" hx-swap="outerHTML">Freigeben</button>`;
bei "freigegeben" das Wort **Freigegeben**. Leer: `<p class="leer">Noch keine Notizen.</p>`.
Darunter Formular `hx-post="/ui/bewohner/{{ person.id }}/notizen" hx-target="#notizen-block" hx-swap="outerHTML"`
mit `author` (Text, „Dein Kürzel") und `text` (textarea, „Notiz für die nächste Schicht"), Knopf „Als Entwurf speichern".
Darunter `<p class="muted">Erst nach der Freigabe erscheint die Notiz in der Übergabe.</p>`.

**In `bewohner_detail.html`:** nach dem Beobachtungen-Block einfügen:
```jinja
  <h2>Notizen für die Übergabe</h2>
  {% include "_notizen.html" %}
```

**Gestaltungsregeln (gelten für jede Seite):**
- Template beginnt mit `{% extends "base.html" %}` und füllt `{% block content %}`
- Deutsche Beschriftungen, freundlich und einfach — Zielgruppe sind Pflegekräfte,
  keine Entwickler. Keine Fachbegriffe wie "Entity", "Submit", "ID".
- Vorhandene CSS-Klassen nutzen (style.css): `card`, `person-list`, `person-card`,
  `avatar`, `biografie`, `wunsch-liste`, `btn`, `btn-secondary`, `hinweis`,
  `erfolg`, `leer`, `lead`, `muted`
- Kein `<style>` und kein `<script>` im Template — kein Inline-CSS, kein Inline-JS
- Niemals echte Personendaten in Beispielen
