import pytest

from apps.api.main import app

if "/ui/uebergabe" not in {r.path for r in app.routes}:
    pytest.skip("T023 noch nicht umgesetzt", allow_module_level=True)


async def test_seite_rendert_leer(client):
    r = await client.get("/ui/uebergabe")
    assert r.status_code == 200
    assert "Übergabe" in r.text


async def test_biografie_vor_beobachtung(client):
    """Personenzentrierung: Die Übergabe beginnt bei der Person, nicht beim Problem."""
    from apps.api.web import BEOBACHTUNG_KATEGORIEN
    rid = (await client.post("/v1/residents", json={
        "name": "Maria Bergmann", "zimmer": "214",
        "biografie": "Lehrerin aus Freiburg.", "wuensche": ["Kaffee vor dem Waschen"]})).json()["id"]
    await client.post(f"/ui/bewohner/{rid}/beobachtung",
                      data={"author": "km", "kategorie": BEOBACHTUNG_KATEGORIEN[0], "notiz": "MARKER-NOTIZ"})
    t = (await client.get("/ui/uebergabe")).text
    for teil in ("Maria Bergmann", "214", "Lehrerin aus Freiburg", "Kaffee vor dem Waschen", "MARKER-NOTIZ"):
        assert teil in t, teil
    assert t.index("Lehrerin aus Freiburg") < t.index("MARKER-NOTIZ")
    assert t.index("Kaffee vor dem Waschen") < t.index("MARKER-NOTIZ")


async def test_lange_biografie_gekuerzt(client):
    await client.post("/v1/residents", json={"name": "X Y", "biografie": "A" * 500 + "ENDE"})
    t = (await client.get("/ui/uebergabe")).text
    assert "ENDE" not in t, "Biografie in der Übergabe auf ca. 200 Zeichen kürzen"


async def test_navigation_hat_uebergabe(client):
    t = (await client.get("/ui")).text
    assert 'href="/ui/uebergabe"' in t
