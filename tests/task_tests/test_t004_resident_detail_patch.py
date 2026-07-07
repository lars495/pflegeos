"""T004: GET /v1/residents/{id} + PATCH (Teilupdate, v.a. Biografie)."""
import pytest

residents = pytest.importorskip(
    "apps.api.routes.residents", reason="T003/T004 noch nicht umgesetzt"
)

from apps.api.main import app  # noqa: E402

if "/v1/residents/{resident_id}" not in {r.path for r in app.routes}:
    pytest.skip("T004 noch nicht umgesetzt (Detail-Route fehlt)", allow_module_level=True)


async def _neu(client, name="Max Mustermann"):
    r = await client.post("/v1/residents", json={"name": name})
    assert r.status_code == 201
    return r.json()["id"]


async def test_get_einzeln(client):
    rid = await _neu(client)
    r = await client.get(f"/v1/residents/{rid}")
    assert r.status_code == 200
    assert r.json()["id"] == rid


async def test_get_unbekannt_404(client):
    r = await client.get("/v1/residents/gibt-es-nicht")
    assert r.status_code == 404


async def test_patch_biografie(client):
    rid = await _neu(client)
    r = await client.patch(
        f"/v1/residents/{rid}",
        json={"biografie": "30 Jahre Grundschullehrerin in Freiburg."},
    )
    assert r.status_code == 200, r.text
    assert r.json()["biografie"] == "30 Jahre Grundschullehrerin in Freiburg."
    # Name bleibt unangetastet (Teilupdate!)
    assert r.json()["name"] == "Max Mustermann"


async def test_patch_unbekannt_404(client):
    r = await client.patch("/v1/residents/nope", json={"zimmer": "214"})
    assert r.status_code == 404
