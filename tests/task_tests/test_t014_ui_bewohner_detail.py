import pytest

from apps.api.main import app

_pfade = {r.path for r in app.routes}
if "/ui/bewohner/{resident_id}" not in _pfade:
    pytest.skip("T014 noch nicht umgesetzt (/ui/bewohner/{resident_id} fehlt)", allow_module_level=True)


async def _anlegen(client, **rest):
    r = await client.post("/v1/residents", json={"name": "Maria Bergmann", **rest})
    return r.json()["id"]


async def test_detail_rendert(client):
    rid = await _anlegen(client)
    r = await client.get(f"/ui/bewohner/{rid}")
    assert r.status_code == 200
    assert "Maria Bergmann" in r.text


async def test_unbekannt_gibt_404(client):
    r = await client.get("/ui/bewohner/gibt-es-nicht")
    assert r.status_code == 404


async def test_biografie_wird_angezeigt(client):
    rid = await _anlegen(client, biografie="War 30 Jahre Grundschullehrerin in Freiburg.")
    r = await client.get(f"/ui/bewohner/{rid}")
    assert "Grundschullehrerin" in r.text
    assert "biografie" in r.text, "Biografie braucht die CSS-Klasse 'biografie'"


async def test_wuensche_werden_angezeigt(client):
    rid = await _anlegen(client)
    await client.post(f"/v1/residents/{rid}/wuensche", json={"wunsch": "Einmal wieder ans Meer"})
    r = await client.get(f"/ui/bewohner/{rid}")
    assert "Einmal wieder ans Meer" in r.text
