"""a11y-Check: WCAG 2.1 AA Scan auf Care-App.

Heutiger Stand: Stub. Erste echte Implementierung mit axe-core und Playwright
folgt sobald die Care-App tatsächlich UI hat (Phase 1).
"""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CARE_APP = ROOT / "apps" / "care-app"


def main() -> int:
    # Sobald die Care-App ein lauffähiges Frontend hat, hier:
    #   - npx @axe-core/cli http://localhost:3000 --tags wcag2a,wcag2aa
    #   - relevante Routen durchgehen
    #   - Bei Verstößen exit 1
    if not any(p.suffix in {".svelte", ".html"} for p in CARE_APP.rglob("*")):
        print("[a11y] noch kein Care-App-UI vorhanden — übersprungen (Phase 0)")
        return 0

    print("[a11y] TODO: axe-core Integration steht noch aus")
    return 0


if __name__ == "__main__":
    sys.exit(main())
