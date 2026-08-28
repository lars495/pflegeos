import pytest

from apps.api.main import app

_pfade = {r.path for r in app.routes}
if "/ui/bewohner/{resident_id}/biografie" not in _pfade:
    pytest.skip("T016 noch nicht umgesetzt (/ui/bewohner/{resident_id}/biografie fehlt)", allow_module_level=True)


async def _anlegen(client):
    r = await client.post("/v1/residents", json={"name": "Maria Bergmann"})
    return r.json()["id"]


async def test_bearbeiten_formular(client):
    rid = await _anlegen(client)
    r = await client.get(f"/ui/bewohner/{rid}/biografie")
    assert r.status_code == 200
    assert "<textarea" in r.text


async def test_speichern_uebernimmt_text(client):
    rid = await _anlegen(client)
    r = await client.post(
        f"/ui/bewohner/{rid}/biografie",
        data={"biografie": "Hat zwei Toechter grossgezogen."},
    )
    assert r.status_code == 200
    assert "Hat zwei Toechter grossgezogen." in r.text
    detail = await client.get(f"/v1/residents/{rid}")
    assert detail.json()["biografie"] == "Hat zwei Toechter grossgezogen."


async def test_antwort_ist_fragment_kein_vollbild(client):
    """HTMX tauscht nur den Abschnitt aus — kein <html> im Fragment."""
    rid = await _anlegen(client)
    r = await client.post(f"/ui/bewohner/{rid}/biografie", data={"biografie": "Kurz."})
    assert "<!DOCTYPE" not in r.text and "<html" not in r.text
