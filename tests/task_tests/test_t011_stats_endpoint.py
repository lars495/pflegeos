"""T011: Öffentliche Statistik — Transparenz ohne Personenbezug."""
import pytest

pytest.importorskip("apps.api.routes.stats", reason="T011 noch nicht umgesetzt")
pytest.importorskip("apps.api.routes.residents", reason="T003 noch nicht umgesetzt")


async def test_stats_struktur(client):
    r = await client.get("/v1/stats")
    assert r.status_code == 200
    data = r.json()
    for key in ("residents", "reflections", "version"):
        assert key in data
    assert isinstance(data["residents"], int)


async def test_stats_zaehlt(client):
    await client.post("/v1/residents", json={"name": "Max Mustermann"})
    r = await client.get("/v1/stats")
    assert r.json()["residents"] == 1
