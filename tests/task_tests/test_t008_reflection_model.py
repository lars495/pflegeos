"""T008: Reflexions-ORM-Modell — für Pflegekräfte, nicht für die Akte."""
import pytest

refl_mod = pytest.importorskip(
    "apps.api.models.reflection", reason="T008 noch nicht umgesetzt"
)


def test_klasse_und_tabelle():
    assert refl_mod.Reflection.__tablename__ == "reflections"


def test_felder():
    cols = {c.name for c in refl_mod.Reflection.__table__.columns}
    required = {"id", "author", "gut", "schwierig", "mitnehmen", "nur_fuer_mich", "created_at"}
    fehlend = required - cols
    assert not fehlend, f"Fehlende Spalten: {fehlend}"


async def test_persistenz_und_defaults(db_session):
    r = refl_mod.Reflection(author="pflegekraft-km", gut="Frau B. hat gelacht.")
    db_session.add(r)
    await db_session.commit()
    await db_session.refresh(r)
    assert r.id
    assert r.nur_fuer_mich is True, "Reflexionen sind per Default privat!"
    assert r.schwierig == ""
    assert r.created_at is not None
