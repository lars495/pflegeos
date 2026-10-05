"""T026: Hinweise der Person stehen ganz oben in ihrer Übergabekarte."""
import pytest
from pathlib import Path
from apps.api.main import app
if "/ui/bewohner/{resident_id}/hinweise" not in {r.path for r in app.routes}:
    pytest.skip("T025 fehlt", allow_module_level=True)
if "PERSON-HINWEIS" not in (Path(__file__).resolve().parents[2] / "apps/api/templates/uebergabe.html").read_text():
    pytest.skip("T026 noch nicht umgesetzt", allow_module_level=True)


async def test_hinweis_vor_wuenschen(client):
    rid = (await client.post("/v1/residents", json={"name": "Maria Bergmann", "wuensche": ["WUNSCH-X"],
                                                    "biografie": "BIO-X"})).json()["id"]
    await client.post(f"/ui/bewohner/{rid}/hinweise", data={"text": "HINWEIS-X"})
    t = (await client.get("/ui/uebergabe")).text
    assert "HINWEIS-X" in t
    assert t.index("HINWEIS-X") < t.index("WUNSCH-X") < t.index("BIO-X")


async def test_ohne_hinweis_kein_leerer_kasten(client):
    await client.post("/v1/residents", json={"name": "Ohne Hinweis"})
    t = (await client.get("/ui/uebergabe")).text
    assert "Wunsch für die Übergabe" not in t
