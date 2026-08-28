import pytest

from apps.api.main import app

_pfade = {r.path for r in app.routes}
if "/ui/reflexion/meine" not in _pfade:
    pytest.skip("T019 noch nicht umgesetzt (/ui/reflexion/meine fehlt)", allow_module_level=True)


async def _schreiben(client, author, gut):
    await client.post("/v1/reflections", json={"author": author, "gut": gut})


async def test_seite_rendert(client):
    r = await client.get("/ui/reflexion/meine", params={"author": "km"})
    assert r.status_code == 200


async def test_nur_eigene_sichtbar(client):
    await _schreiben(client, "km", "Meine eigene Notiz")
    await _schreiben(client, "andere", "Fremde Notiz")
    r = await client.get("/ui/reflexion/meine", params={"author": "km"})
    assert "Meine eigene Notiz" in r.text
    assert "Fremde Notiz" not in r.text, "Reflexionen anderer duerfen NIE sichtbar sein"


async def test_ohne_kuerzel_kein_datenleck(client):
    await _schreiben(client, "km", "Geheime Notiz")
    r = await client.get("/ui/reflexion/meine")
    assert "Geheime Notiz" not in r.text


async def test_leerer_zustand(client):
    r = await client.get("/ui/reflexion/meine", params={"author": "niemand"})
    assert r.status_code == 200
    assert "noch keine" in r.text.lower() or "leer" in r.text.lower()
