import pytest

from apps.api.main import app

_pfade = {r.path for r in app.routes}
if "/ui/bewohner/{resident_id}/wuensche" not in _pfade:
    pytest.skip("T017 noch nicht umgesetzt (/ui/bewohner/{resident_id}/wuensche fehlt)", allow_module_level=True)


async def _anlegen(client):
    r = await client.post("/v1/residents", json={"name": "Maria Bergmann"})
    return r.json()["id"]


async def test_wunsch_wird_gespeichert(client):
    rid = await _anlegen(client)
    r = await client.post(
        f"/ui/bewohner/{rid}/wuensche", data={"wunsch": "Sonntags Kuchen essen"}
    )
    assert r.status_code == 200
    assert "Sonntags Kuchen essen" in r.text
    detail = await client.get(f"/v1/residents/{rid}")
    assert "Sonntags Kuchen essen" in detail.json()["wuensche"]


async def test_mehrere_wuensche_bleiben_erhalten(client):
    rid = await _anlegen(client)
    await client.post(f"/ui/bewohner/{rid}/wuensche", data={"wunsch": "Erster Wunsch"})
    r = await client.post(f"/ui/bewohner/{rid}/wuensche", data={"wunsch": "Zweiter Wunsch"})
    assert "Erster Wunsch" in r.text and "Zweiter Wunsch" in r.text


async def test_leerer_wunsch_aendert_nichts(client):
    rid = await _anlegen(client)
    await client.post(f"/ui/bewohner/{rid}/wuensche", data={"wunsch": "  "})
    detail = await client.get(f"/v1/residents/{rid}")
    assert detail.json()["wuensche"] == []


async def test_antwort_ist_fragment(client):
    rid = await _anlegen(client)
    r = await client.post(f"/ui/bewohner/{rid}/wuensche", data={"wunsch": "Test"})
    assert "<!DOCTYPE" not in r.text
