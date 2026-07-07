"""T012: /healthz prüft die Datenbank-Verbindung mit."""
import pytest

from apps.api.routes import health

if not getattr(health, "HEALTHZ_CHECKS_DB", False):
    pytest.skip("T012 noch nicht umgesetzt (HEALTHZ_CHECKS_DB fehlt)", allow_module_level=True)


async def test_healthz_mit_db_status(client):
    r = await client.get("/healthz")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert data.get("db") == "ok", "healthz muss DB-Status mitliefern (SELECT 1)"
