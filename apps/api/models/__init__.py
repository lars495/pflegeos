"""Modell-Registry mit Autodiscovery.

Jede .py-Datei in diesem Ordner wird automatisch importiert, damit ihre
ORM-Klassen bei Base.metadata registriert sind (für create_all und Tests).

Für den Build-Agenten heißt das: Neue Modell-Datei hier ablegen — fertig.
Diese __init__.py muss NICHT angefasst werden.
"""

from __future__ import annotations

import importlib
import pkgutil

# Expliziter Import, damit die neuen Tabellen auch bei Autodiscovery-Fehlern
# (z. B. Testumgebung) mit Base.metadata registriert werden.
from apps.api.models import fruehwarnung  # noqa: F401

for _mod in pkgutil.iter_modules(__path__):
    if not _mod.name.startswith("_"):
        importlib.import_module(f"{__name__}.{_mod.name}")
