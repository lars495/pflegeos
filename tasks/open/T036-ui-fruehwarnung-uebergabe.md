---
id: T036
title: Frühwarnungen in der Übergabe zeigen und im Profil verlinken
roadmap_item: Recherche 2026-10-29 — Stop-and-Watch-Frühwarnkarte für alle Qualifikationsstufen
depends_on:
  - T034
  - T035
target_files:
  - apps/api/ui/uebergabe.py
  - apps/api/templates/uebergabe.html
  - apps/api/templates/bewohner_detail.html
context_files:
  - apps/api/ui/uebergabe.py
  - apps/api/templates/uebergabe.html
  - apps/api/templates/bewohner_detail.html
  - apps/api/models/fruehwarnung.py
  - apps/api/ui/notizen.py
  - tests/task_tests/test_t036_ui_fruehwarnung_uebergabe.py
test_command: pytest -q tests/task_tests/test_t036_ui_fruehwarnung_uebergabe.py
max_attempts: 3
attempts_used: 0
---

Die Meldungen der Frühwarnkarte (T035) erscheinen in der Übergabeansicht der nächsten Schicht.
Im Bewohnerprofil gibt es einen Link zur Karte, damit sie jede Person direkt dort erreicht.
**Alles Bestehende in den drei Dateien behalten**, nur ergänzen (bestehende Abschnitte,
Kontextvariablen und Texte nicht verändern). Schau dir an, wie T033 die Notizen in die
Übergabe eingebaut hat, und nutze dasselbe Muster.

## `apps/api/ui/uebergabe.py`
In der bestehenden Route für `GET /ui/uebergabe` zusätzlich laden:
```python
grenze = datetime.utcnow() - timedelta(hours=48)
zeilen = (await session.execute(
    select(FruehwarnMeldung, Resident)
    .join(Resident, Resident.id == FruehwarnMeldung.resident_id)
    .where(FruehwarnMeldung.created_at >= grenze)
    .order_by(FruehwarnMeldung.created_at.desc()))).all()
fruehwarnungen = [(m, p) for m, p in zeilen]
```
und als Kontextvariable `fruehwarnungen` ans Template übergeben (Liste von Tupeln
`(meldung, person)`). Import: `from apps.api.models.fruehwarnung import FruehwarnMeldung`
(und `datetime`, `timedelta`, `Resident`, `select`, falls noch nicht importiert; die
Schreibweise an die vorhandenen Importe der Datei anpassen).
Die Reihenfolge richtet sich **nur nach der Zeit**, nicht nach Autor, Rolle oder Anzahl der
Auffälligkeiten. Es gibt keine Punktzahl und keine Ampel.

## `apps/api/templates/uebergabe.html`
Neuer eigener Abschnitt innerhalb des `content`-Blocks (am Ende, vor dem schließenden
`{% endblock %}`):
```jinja
<h2>Frühwarnungen der letzten 48 Stunden</h2>
<p class="muted">Das sind Hinweise zum genaueren Hinschauen, keine Diagnosen. Ihr entscheidet im Team, was daraus folgt.</p>
{% if fruehwarnungen %}
  {% for m, p in fruehwarnungen %}
    <div class="card">
      <strong>{{ p.name }}</strong>
      {% if m.auffaelligkeiten_liste() %}
        <ul>{% for a in m.auffaelligkeiten_liste() %}<li>{{ a }}</li>{% endfor %}</ul>
      {% endif %}
      {% if m.freitext %}<p>{{ m.freitext }}</p>{% endif %}
      <p class="muted">gemeldet von {{ m.author }}, {{ m.created_at.strftime("%d.%m. %H:%M") }}</p>
      <a href="/ui/bewohner/{{ p.id }}" class="btn-secondary">Zum Profil</a>
    </div>
  {% endfor %}
{% else %}
  <p class="leer">Keine Frühwarnungen in den letzten 48 Stunden.</p>
{% endif %}
```

## `apps/api/templates/bewohner_detail.html`
Nach dem Block „Notizen für die Übergabe" (`{% include "_notizen.html" %}`) und vor dem
„Zurück zur Liste"-Link einfügen:
```jinja
  <p><a href="/ui/bewohner/{{ person.id }}/fruehwarnung" class="btn-secondary">Mir ist etwas aufgefallen</a></p>
```

**Gestaltungsregeln:** Kein `<style>`, kein `<script>`, kein Inline-CSS/JS. Nur vorhandene
CSS-Klassen. Deutsche, freundliche Beschriftungen.
