"""T027: Modell SbarNotiz."""
import pytest
mod = pytest.importorskip("apps.api.models.sbar", reason="T027 noch nicht umgesetzt")


def test_tabelle():
    assert mod.SbarNotiz.__tablename__ == "sbar_notizen"
    assert {"id", "resident_id", "author", "situation", "hintergrund", "einschaetzung", "empfehlung", "created_at"} <= {c.name for c in mod.SbarNotiz.__table__.columns}


async def test_persistenz(db_session):
    o = mod.SbarNotiz(resident_id="r1", author="km", situation="isst weniger")
    db_session.add(o)
    await db_session.commit()
    await db_session.refresh(o)
    assert o.id and o.created_at is not None
    assert o.empfehlung == ""

