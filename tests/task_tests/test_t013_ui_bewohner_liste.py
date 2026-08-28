import pytest

from apps.api.main import app

_pfade = {r.path for r in app.routes}
if "/ui/bewohner" not in _pfade:
    pytest.skip("T013 noch nicht umgesetzt (/ui/bewohner fehlt)", allow_module_level=True)


async def _anlegen(client, name="Maria Bergmann", **rest):
    r = await client.post("/v1/residents", json={"name": name, **rest})
    return r.json()["id"]


async def test_liste_rendert(client):
    r = await client.get("/ui/bewohner")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]


async def test_leere_liste_freundlich(client):
    r = await client.get("/ui/bewohner")
    assert "noch niemand" in r.text.lower() or "keine" in r.text.lower()


async def test_namen_erscheinen(client):
    await _anlegen(client, "Maria Bergmann")
    await _anlegen(client, "Heinrich Vogt")
    r = await client.get("/ui/bewohner")
    assert "Maria Bergmann" in r.text
    assert "Heinrich Vogt" in r.text


async def test_zimmer_wird_gezeigt(client):
    await _anlegen(client, "Maria Bergmann", zimmer="214")
    r = await client.get("/ui/bewohner")
    assert "214" in r.text


async def test_verlinkt_auf_detailseite(client):
    rid = await _anlegen(client)
    r = await client.get("/ui/bewohner")
    assert f"/ui/bewohner/{rid}" in r.text
