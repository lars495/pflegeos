"""T007: Audit-Helper + automatisches Logging bei Resident-Änderungen."""
import pytest
from sqlalchemy import select

audit_mod = pytest.importorskip("apps.api.models.audit", reason="T006 noch nicht umgesetzt")
pytest.importorskip("apps.api.audit", reason="T007 noch nicht umgesetzt")
pytest.importorskip("apps.api.routes.residents", reason="T003 noch nicht umgesetzt")


async def test_create_erzeugt_audit_eintrag(client, db_session):
    r = await client.post("/v1/residents", json={"name": "Max Mustermann"})
    assert r.status_code == 201
    rid = r.json()["id"]

    rows = (await db_session.execute(select(audit_mod.AuditLog))).scalars().all()
    actions = {(e.action, e.resource_id) for e in rows}
    assert ("resident.created", rid) in actions


async def test_patch_erzeugt_audit_eintrag(client, db_session):
    r = await client.post("/v1/residents", json={"name": "Max Mustermann"})
    rid = r.json()["id"]
    await client.patch(f"/v1/residents/{rid}", json={"zimmer": "214"})

    rows = (await db_session.execute(select(audit_mod.AuditLog))).scalars().all()
    actions = {(e.action, e.resource_id) for e in rows}
    assert ("resident.updated", rid) in actions
