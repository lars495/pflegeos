---
id: T042
title: Übergabe-Block bearbeiten (eigene Fassung statt Profiländerung)
roadmap_item: Recherche 2026-10-29 — Wunsch- und Biografie-Block in der Übergabeansicht
depends_on:
- T041
- T040
- T007
target_files:
- apps/api/ui/uebergabe_profil.py
- apps/api/templates/uebergabe_profil.html
context_files:
- apps/api/ui/uebergabe_profil.py
- apps/api/templates/uebergabe_profil.html
- apps/api/ui/notizen.py
- apps/api/models/uebergabe_profil.py
- apps/api/audit.py
- tests/task_tests/test_t042_ui_uebergabe_block_bearbeiten.py
test_command: pytest -q tests/task_tests/test_t042_ui_uebergabe_block_bearbeiten.py
max_attempts: 3
attempts_used: 1
completed_at: '2026-11-04'
---

Die Pflegekraft kann den Übergabe-Block anpassen. Gespeichert wird **nur** in
`UebergabeProfil` (T040) — das Bewohnerprofil und die Wünsche bleiben unverändert.
Die Pflegekraft entscheidet; nichts wird automatisch übernommen.

Beide Dateien komplett ausgeben, Bestehendes unverändert lassen, nur ergänzen.

## apps/api/ui/uebergabe_profil.py

Zusätzliche Imports: `Form` (fastapi), `RedirectResponse` (fastapi.responses),
`from apps.api.audit import log_action`, `import datetime as dt`.
(`UebergabeProfil` ist bereits importiert.)

Neue Route:

```python
@router.post("/ui/bewohner/{resident_id}/uebergabe", response_class=HTMLResponse)
async def ui_uebergabe_profil_speichern(
    resident_id: str, request: Request,
    author: str = Form(""), biografie: str = Form(""),
    wuensche: str = Form(""), wohlbefinden: str = Form(""),
    session: AsyncSession = Depends(get_session),
):
```
Ablauf:
1. Person laden (`session.get(Resident, resident_id)`); fehlt sie: `HTTPException(404, "Bewohner:in nicht gefunden")`.
2. Ist `author.strip()` leer: **nichts speichern**, `return await _seite(request, session, person,
   fehler="Bitte trage dein Kürzel ein, dann wird gespeichert.", status_code=422)`.
3. Die drei Texte mit `_norm()` normalisieren (Browser schicken `\r\n`).
4. `vor = await vorbefuellung(session, person)`. Für `biografie` und `wuensche`: ist der normalisierte
   Text **gleich** `vor[feld]`, wird `None` gespeichert (= weiter live aus dem Profil), sonst der Text
   (auch `""` — bewusstes Leeren ist erlaubt). Für `wohlbefinden`: ist der Text gleich `vor["wohlbefinden"]`
   (meist leer), wird `None` gespeichert, sonst der Text.
5. Vorhandene `UebergabeProfil`-Zeile der Person laden (`select ... where resident_id == resident_id`)
   und aktualisieren, sonst neu anlegen (`session.add`) — nie eine zweite Zeile.
   `bearbeitet_von = author.strip()`, `updated_at = dt.datetime.utcnow()`.
6. `await log_action(session, actor=author.strip(), action="uebergabe_profil.bearbeitet",
   resource_type="resident", resource_id=resident_id)` — **ohne** die Texte im Audit-Eintrag.
   Damit lässt sich die Nutzung des Blocks nur gezählt, aggregiert auswerten (die I-PASS-Hypothese
   soll geprüft werden, ohne Pflegekräfte zu überwachen).
7. `await session.commit()`, dann `return RedirectResponse(f"/ui/bewohner/{resident_id}/uebergabe", status_code=303)`.

## apps/api/templates/uebergabe_profil.html

Am **Ende** der Karte einfügen: nach dem Notizen-Abschnitt (Schritt 9) und **vor** dem
„Zum Profil"-Link (Schritt 10):

```jinja
<h2>Für die Übergabe anpassen</h2>
<p class="muted">Das Profil selbst bleibt unverändert. Nur die Übergabe zeigt deine Fassung.</p>
<form method="post" action="/ui/bewohner/{{ person.id }}/uebergabe">
  <label for="author">Dein Kürzel</label>
  <input type="text" id="author" name="author" placeholder="Dein Kürzel">
  <label for="biografie">Wer ich bin</label>
  <textarea id="biografie" name="biografie">{{ texte.biografie }}</textarea>
  <label for="wuensche">Das wünsche ich mir</label>
  <textarea id="wuensche" name="wuensche">{{ texte.wuensche }}</textarea>
  <label for="wohlbefinden">Wie es mir heute geht</label>
  <textarea id="wohlbefinden" name="wohlbefinden">{{ texte.wohlbefinden }}</textarea>
  <button type="submit" class="btn">Für die Übergabe speichern</button>
</form>
```
Das Formular nutzt bewusst normales POST mit Weiterleitung (kein JavaScript, kein HTMX nötig).

*Hinweis für Menschen (nicht für den Agenten):* Die neuen Routen
`GET`/`POST /ui/bewohner/{resident_id}/uebergabe` gehören anschließend in
`tests/test_routen_bestand.py`.
