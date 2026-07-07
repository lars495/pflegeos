"""T006: AuditLog-ORM-Modell (Compliance: DSGVO Art. 32, MD-QPR)."""
import pytest

audit_mod = pytest.importorskip(
    "apps.api.models.audit", reason="T006 noch nicht umgesetzt"
)


def test_klasse_und_tabelle():
    assert audit_mod.AuditLog.__tablename__ == "audit_log"


def test_felder():
    cols = {c.name for c in audit_mod.AuditLog.__table__.columns}
    required = {"id", "timestamp", "actor", "action", "resource_type", "resource_id", "details"}
    fehlend = required - cols
    assert not fehlend, f"Fehlende Spalten: {fehlend}"


async def test_persistenz(db_session):
    e = audit_mod.AuditLog(
        actor="system",
        action="resident.created",
        resource_type="resident",
        resource_id="abc123",
    )
    db_session.add(e)
    await db_session.commit()
    await db_session.refresh(e)
    assert e.id
    assert e.timestamp is not None
    assert e.details == {}, "details muss Default {} haben"
