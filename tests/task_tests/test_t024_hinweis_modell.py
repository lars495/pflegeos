"""T024: Modell PersonHinweis."""
import pytest
mod = pytest.importorskip("apps.api.models.hinweis", reason="T024 noch nicht umgesetzt")


def test_tabelle():
    assert mod.PersonHinweis.__tablename__ == "person_hinweise"
    assert {"id", "resident_id", "text", "created_at"} <= {c.name for c in mod.PersonHinweis.__table__.columns}


async def test_persistenz(db_session):
    o = mod.PersonHinweis(resident_id="r1", text="Bitte nicht vor Besuch besprechen")
    db_session.add(o)
    await db_session.commit()
    await db_session.refresh(o)
    assert o.id and o.created_at is not None

