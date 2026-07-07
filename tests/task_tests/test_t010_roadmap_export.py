"""T010: Roadmap-Export als JSON für die öffentliche Website."""
import json

import pytest

export_mod = pytest.importorskip(
    "scripts.roadmap_export", reason="T010 noch nicht umgesetzt"
)


def test_export_struktur(tmp_path):
    out = tmp_path / "roadmap-status.json"
    result = export_mod.export_roadmap(out_path=str(out))

    assert out.exists(), "JSON-Datei muss geschrieben werden"
    data = json.loads(out.read_text())
    assert data == result

    assert "generated_at" in data
    assert "phases" in data
    assert len(data["phases"]) >= 5, "ROADMAP.md hat 5 Phasen"

    phase1 = data["phases"][0]
    assert "name" in phase1
    assert "items" in phase1
    assert len(phase1["items"]) >= 3

    item = phase1["items"][0]
    for key in ("status", "title", "score"):
        assert key in item, f"Item braucht Feld {key}"
    assert isinstance(item["score"], int)
