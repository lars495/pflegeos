"""T009: Reflexions-Endpoints. Privat per Default — nur eigene sichtbar."""
import pytest

pytest.importorskip("apps.api.routes.reflections", reason="T009 noch nicht umgesetzt")


async def test_post_reflexion(client):
    r = await client.post("/v1/reflections", json={
        "author": "pflegekraft-km",
        "gut": "Musik hat heute geholfen.",
        "schwierig": "Herr M. wollte das Zimmer nicht verlassen.",
        "mitnehmen": "Morgen frueh gleich Musik anmachen.",
    })
    assert r.status_code == 201, r.text
    assert r.json()["nur_fuer_mich"] is True


async def test_get_nur_eigene(client):
    await client.post("/v1/reflections", json={"author": "km", "gut": "a"})
    await client.post("/v1/reflections", json={"author": "km", "gut": "b"})
    await client.post("/v1/reflections", json={"author": "andere", "gut": "c"})

    r = await client.get("/v1/reflections", params={"author": "km"})
    assert r.status_code == 200
    assert len(r.json()) == 2
    assert all(x["author"] == "km" for x in r.json())


async def test_get_ohne_author_422(client):
    r = await client.get("/v1/reflections")
    assert r.status_code == 422, "author ist Pflicht-Query-Parameter"
