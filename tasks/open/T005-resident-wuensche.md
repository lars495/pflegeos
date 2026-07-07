---
id: T005
title: Wünsche-Endpoints — Wünsche werden nie vergessen
roadmap_item: Bewohner-Profil mit Biografie (Lebensgeschichte, Beruf, Werte)
depends_on: [T004]
target_files:
  - apps/api/routes/residents.py
context_files:
  - apps/api/routes/residents.py
  - tests/task_tests/test_t005_resident_wuensche.py
test_command: pytest -q tests/task_tests/test_t005_resident_wuensche.py
max_attempts: 3
attempts_used: 0
---

Erweitere `apps/api/routes/residents.py` um Wünsche-Verwaltung. Wünsche der
Bewohner:innen sind ein Kernstück der Personenzentrierung — sie gehen nie verloren.

1. `POST /residents/{resident_id}/wuensche` — Body ist ein Pydantic-Modell
   `WunschIn` mit einem Feld `wunsch: str` (definiere es direkt in der Datei).
   Ablauf: Resident laden (404 wenn fehlt), dann:
   ```python
   obj.wuensche = [*obj.wuensche, payload.wunsch]
   ```
   (WICHTIG: neue Liste zuweisen, nicht `.append()` — sonst merkt
   SQLAlchemy die JSON-Änderung nicht!) Commit + refresh, Antwort: die
   komplette Wünsche-Liste `list[str]`, Status 200.
2. `GET /residents/{resident_id}/wuensche` → `list[str]` (404 wenn Resident fehlt).
