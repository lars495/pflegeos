"""T005: Wünsche-Endpoints — Wünsche werden nie vergessen (PZ-Kernfeature)."""
import pytest

pytest.importorskip("apps.api.routes.residents", reason="T003 noch nicht umgesetzt")

from apps.api.main import app  # noqa: E402

if "/v1/residents/{resident_id}/wuensche" not in {r.path for r in app.routes}:
    pytest.skip("T005 noch nicht umgesetzt (Wünsche-Route fehlt)", allow_module_level=True)


async def _neu(client):
    r = await client.post("/v1/residents", json={"name": "Max Mustermann"})
    return r.json()["id"]


async def test_wunsch_hinzufuegen(client):
    rid = await _neu(client)
    r = await client.post(
        f"/v1/residents/{rid}/wuensche",
        json={"wunsch": "Einmal wieder ans Meer, am liebsten Sylt."},
    )
    assert r.status_code == 200, r.text
    assert "Einmal wieder ans Meer, am liebsten Sylt." in r.json()


async def test_wuensche_sammeln_sich(client):
    rid = await _neu(client)
    await client.post(f"/v1/residents/{rid}/wuensche", json={"wunsch": "Kaffee vor dem Waschen"})
    await client.post(f"/v1/residents/{rid}/wuensche", json={"wunsch": "Volkslieder am Nachmittag"})
    r = await client.get(f"/v1/residents/{rid}/wuensche")
    assert r.status_code == 200
    assert len(r.json()) == 2


async def test_wunsch_unbekannter_resident_404(client):
    r = await client.post("/v1/residents/nope/wuensche", json={"wunsch": "x"})
    assert r.status_code == 404
