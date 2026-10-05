"""T020: Beobachtungs-Modell (Stop-and-Watch)."""
import pytest

mod = pytest.importorskip("apps.api.models.beobachtung", reason="T020 noch nicht umgesetzt")


def test_tabelle_und_felder():
    B = mod.Beobachtung
    assert B.__tablename__ == "beobachtungen"
    cols = {c.name for c in B.__table__.columns}
    assert {"id", "resident_id", "author", "kategorie", "notiz", "created_at"} <= cols


async def test_persistenz(db_session):
    b = mod.Beobachtung(resident_id="r1", author="km", kategorie="isst weniger")
    db_session.add(b)
    await db_session.commit()
    await db_session.refresh(b)
    assert b.id and b.created_at is not None
    assert b.notiz == ""
