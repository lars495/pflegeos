"""T003: POST + GET /v1/residents."""
import pytest

pytest.importorskip("apps.api.routes.residents", reason="T003 noch nicht umgesetzt")


async def test_post_erstellt_resident(client):
    r = await client.post("/v1/residents", json={"name": "Max Mustermann"})
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["name"] == "Max Mustermann"
    assert data["id"]


async def test_post_ohne_name_422(client):
    r = await client.post("/v1/residents", json={})
    assert r.status_code == 422


async def test_get_liste(client):
    await client.post("/v1/residents", json={"name": "Max Mustermann"})
    await client.post("/v1/residents", json={"name": "Erika Musterfrau"})
    r = await client.get("/v1/residents")
    assert r.status_code == 200
    namen = {x["name"] for x in r.json()}
    assert {"Max Mustermann", "Erika Musterfrau"} <= namen
