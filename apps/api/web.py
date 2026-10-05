"""Pflege-Oberfläche — servergerendertes HTML mit Jinja2 + HTMX.

Bewusst kein JavaScript-Framework: Die Zielgruppe sind Pflegekräfte an
alten Bildschirmen und Tablets. HTMX liegt lokal unter /static/.

Aufbau: Eine Datei pro Bereich unter apps/api/ui/ (bewohner, beobachtung,
notizen, reflexion, uebergabe, team, start). Diese Datei sammelt nur die
Router ein. Grund (LEARNINGS L11): Als alles in einer Datei lag, musste das
Modell für jede kleine Änderung ~500 Zeilen neu ausgeben — und veränderte
dabei nebenbei Dinge, um die es nie ging.

Neuer Bereich: Datei apps/api/ui/<bereich>.py mit eigenem `router` anlegen
und hier in BEREICHE eintragen.
"""

from __future__ import annotations

from fastapi import APIRouter

from apps.api.ui import beobachtung, bewohner, notizen, reflexion, start, team, uebergabe
from apps.api.ui.beobachtung import BEOBACHTUNG_KATEGORIEN  # noqa: F401 — von Tests genutzt
from apps.api.ui.common import initialen, templates  # noqa: F401
from apps.api.ui.team import TEAM_MINDESTANZAHL  # noqa: F401

# Reihenfolge: bewohner vor allen anderen /ui/bewohner/{id}/... ist unkritisch,
# weil diese Pfade mehr Segmente haben; innerhalb von bewohner.py steht /neu vor /{id}.
BEREICHE = [start, bewohner, beobachtung, notizen, reflexion, uebergabe, team]

router = APIRouter()
for bereich in BEREICHE:
    router.include_router(bereich.router)
