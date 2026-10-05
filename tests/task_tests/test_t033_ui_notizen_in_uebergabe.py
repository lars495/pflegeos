"""T033: Nur freigegebene Notizen erscheinen in der Übergabe."""
import pytest
from pathlib import Path
from apps.api.main import app
if "/ui/notizen/{notiz_id}/freigeben" not in {r.path for r in app.routes}:
    pytest.skip("T032 fehlt", allow_module_level=True)
if "UEBERGABE-NOTIZEN" not in (Path(__file__).resolve().parents[2] / "apps/api/templates/uebergabe.html").read_text():
    pytest.skip("T033 noch nicht umgesetzt", allow_module_level=True)
from sqlalchemy import select  # noqa: E402


async def test_nur_freigegebene(client, db_session):
    from apps.api.models.uebergabe_notiz import UebergabeNotiz
    rid = (await client.post("/v1/residents", json={"name": "Maria Bergmann"})).json()["id"]
    await client.post(f"/ui/bewohner/{rid}/notizen", data={"author": "km", "text": "ENTWURF-TEXT"})
    await client.post(f"/ui/bewohner/{rid}/notizen", data={"author": "km", "text": "FREI-TEXT"})
    frei = [n for n in (await db_session.execute(select(UebergabeNotiz))).scalars() if n.text == "FREI-TEXT"][0]
    await client.post(f"/ui/notizen/{frei.id}/freigeben")
    t = (await client.get("/ui/uebergabe")).text
    assert "FREI-TEXT" in t
    assert "ENTWURF-TEXT" not in t, "Entwürfe dürfen NIE in der Übergabe erscheinen"
