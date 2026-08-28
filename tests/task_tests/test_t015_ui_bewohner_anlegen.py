import pytest

from apps.api.main import app

_pfade = {r.path for r in app.routes}
if "/ui/bewohner/neu" not in _pfade:
    pytest.skip("T015 noch nicht umgesetzt (/ui/bewohner/neu fehlt)", allow_module_level=True)


async def test_formular_wird_angezeigt(client):
    r = await client.get("/ui/bewohner/neu")
    assert r.status_code == 200
    assert "<form" in r.text
    assert 'name="name"' in r.text


async def test_anlegen_legt_person_an(client):
    r = await client.post(
        "/ui/bewohner/neu",
        data={"name": "Erika Musterfrau", "zimmer": "108"},
        follow_redirects=False,
    )
    assert r.status_code in (302, 303), "Nach dem Anlegen muss weitergeleitet werden"
    liste = await client.get("/v1/residents")
    assert any(x["name"] == "Erika Musterfrau" for x in liste.json())


async def test_leerer_name_wird_abgelehnt(client):
    r = await client.post("/ui/bewohner/neu", data={"name": "   "}, follow_redirects=False)
    assert r.status_code == 200, "Bei Fehler das Formular erneut zeigen, nicht abstürzen"
    liste = await client.get("/v1/residents")
    assert liste.json() == []
