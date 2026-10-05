"""Gemeinsame Bausteine aller Pflege-Seiten: Template-Engine und Filter."""

from __future__ import annotations

from pathlib import Path

from fastapi.templating import Jinja2Templates

TEMPLATE_DIR = Path(__file__).resolve().parents[1] / "templates"
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))


def initialen(name: str) -> str:
    """'Maria Lieselotte Bergmann' → 'MB' (für den Avatar-Kreis)."""
    teile = [t for t in name.split() if t]
    if not teile:
        return "?"
    if len(teile) == 1:
        return teile[0][:2].upper()
    return (teile[0][0] + teile[-1][0]).upper()

templates.env.filters["initialen"] = initialen
