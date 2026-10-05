"""T031: Modell UebergabeNotiz."""
import pytest
mod = pytest.importorskip("apps.api.models.uebergabe_notiz", reason="T031 noch nicht umgesetzt")


def test_tabelle():
    assert mod.UebergabeNotiz.__tablename__ == "uebergabe_notizen"
    assert {"id", "resident_id", "author", "text", "status", "freigegeben_at", "created_at"} <= {c.name for c in mod.UebergabeNotiz.__table__.columns}


async def test_persistenz(db_session):
    o = mod.UebergabeNotiz(resident_id="r1", author="km", text="Hat gut geschlafen")
    db_session.add(o)
    await db_session.commit()
    await db_session.refresh(o)
    assert o.id and o.created_at is not None
    assert o.status == "entwurf"
    assert o.freigegeben_at is None

