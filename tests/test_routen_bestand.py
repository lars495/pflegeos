"""Bestandsschutz: Jede einmal gebaute Route muss erhalten bleiben.

Hintergrund (L11): Task-Tests überspringen sich, wenn ihre Route fehlt —
gedacht für "noch nicht gebaut". Als T033 die Datei web.py neu schrieb und
dabei /ui/team entfernte, wurde das deshalb als Skip verbucht statt als Fehler.

Diese Liste wächst mit jeder erledigten Task. Was hier steht, darf nie fehlen.
"""

from apps.api.main import app

BESTAND = {
    ("GET", "/ui"),
    ("GET", "/ui/bewohner"),
    ("GET", "/ui/bewohner/neu"),
    ("POST", "/ui/bewohner/neu"),
    ("GET", "/ui/bewohner/{resident_id}"),
    ("GET", "/ui/bewohner/{resident_id}/biografie"),
    ("POST", "/ui/bewohner/{resident_id}/biografie"),
    ("POST", "/ui/bewohner/{resident_id}/wuensche"),
    ("POST", "/ui/bewohner/{resident_id}/hinweise"),
    ("GET", "/ui/bewohner/{resident_id}/beobachtung"),
    ("POST", "/ui/bewohner/{resident_id}/beobachtung"),
    ("GET", "/ui/bewohner/{resident_id}/sbar"),
    ("POST", "/ui/bewohner/{resident_id}/sbar"),
    ("POST", "/ui/bewohner/{resident_id}/notizen"),
    ("POST", "/ui/notizen/{notiz_id}/freigeben"),
    ("GET", "/ui/uebergabe"),
    ("GET", "/ui/reflexion"),
    ("POST", "/ui/reflexion"),
    ("GET", "/ui/reflexion/meine"),
    ("GET", "/ui/team"),
    ("POST", "/ui/team"),
    ("POST", "/v1/residents"),
    ("GET", "/v1/residents"),
    ("GET", "/v1/residents/{resident_id}"),
    ("PATCH", "/v1/residents/{resident_id}"),
    ("POST", "/v1/residents/{resident_id}/wuensche"),
    ("GET", "/v1/residents/{resident_id}/wuensche"),
    ("POST", "/v1/reflections"),
    ("GET", "/v1/reflections"),
    ("GET", "/v1/stats"),
    ("GET", "/healthz"),
}


def _vorhanden() -> set[tuple[str, str]]:
    out = set()
    for r in app.routes:
        for m in getattr(r, "methods", set()) or set():
            if m != "HEAD":
                out.add((m, r.path))
    return out


def test_keine_route_verschwunden():
    fehlend = BESTAND - _vorhanden()
    assert not fehlend, f"Bestehende Routen fehlen: {sorted(fehlend)}"
