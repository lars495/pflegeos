# Conventions

> Kurz, verbindlich. Bei Konflikt mit `PRINCIPLES.md` gewinnt PRINCIPLES.

## Sprache

- **Code:** Englisch (Variablen, Klassen, Kommentare, Commits)
- **UI-Texte:** Deutsch (Pflegepersonal + Bewohner in Deutschland)
- **Doku-Dateien im Wurzelverzeichnis** (PRINCIPLES, ROADMAP, etc.): Deutsch
- **README, CONTRIBUTING:** zweisprachig DE/EN
- **API-Schemas, JSON-Keys:** englisch (`resident_id`, nicht `bewohner_id`)
- **Datenbank-Tabellen:** englisch im Singular (`resident`, `care_plan`, `contribution`)

## Code-Stil

### Python
- Python 3.12+
- Formatter: `ruff format`
- Linter: `ruff check` mit `pyproject.toml`-Konfig
- Type Hints: **verpflichtend** auf allen public APIs
- Tests: `pytest`, Naming `test_<unit>_<scenario>_<expected>.py`
- Async by default (FastAPI, asyncpg)
- Dependency-Pinning: `requirements.txt` mit Hashes oder `uv lock`

### TypeScript / SvelteKit
- TypeScript strict mode
- Formatter: `prettier`
- Linter: `eslint` mit `svelte-eslint`
- Komponenten in PascalCase, Stores in camelCase
- Keine `any` außer mit Begründung im Kommentar

### Allgemein
- Keine Geheimnisse im Repo (`.env` ist gitignored, `.env.example` mit Platzhaltern)
- Keine TODO-Kommentare ohne GitHub-Issue-Link
- Keine commented-out Code-Blöcke — wenn ungebraucht, löschen (git remembers)

## Commit-Format

```
<type>(<scope>): <subject>

<body — optional, ab 80 Zeichen wrappen>

<footer — Referenzen, Co-Authors>
```

**Types:**
- `feat` — neues Feature
- `fix` — Bugfix
- `refactor` — Umbau ohne Verhaltensänderung
- `test` — Tests
- `docs` — Doku
- `chore` — Build, CI, Deps
- `legal` — von Legal-Audit getrieben
- `community` — auf Community-Beitrag zurückgehend (mit Einsender im Footer)

**Beispiele:**
```
feat(care-plan): add four-voice canvas with conflict visualization

Implements PFL-12. Each contribution is tagged with role
(resident/family/nurse/ai) and conflicts are shown but not
auto-resolved (see PRINCIPLES.md §1).

Refs: #12
Community-By: M. Schulze <m.schulze@example.com>
```

**Agent-Commits:**
Der tägliche Agent committet mit `Author: PflegeOS Agent <agent@pflegeos.de>` und `Co-Authored-By: <name>` für Community-Beiträge.

## Pull-Request-Workflow

Für menschliche Mitwirkende (der Agent committet direkt auf `main`):

1. Fork → Feature-Branch (`feat/<short-desc>`)
2. PR mit Beschreibung, die explizit benennt:
   - Welche Säule(n) das Feature stärkt
   - Welche `legal_requirements.yaml`-IDs es berührt
   - Wie es getestet wurde (inkl. a11y)
3. Mindestens 1 Review, bevor Merge
4. CI muss grün sein (Tests + Compliance-Check + a11y)

## Tests

- **Jedes Feature braucht einen Test.** Kein Test → kein Deploy.
- **Integration > Unit** für UI-/Workflow-Features. Unit-Tests für reine Logik.
- **DB-Tests:** echte PostgreSQL via Testcontainer, keine Mocks. (Wegen pgvector-Verhalten.)
- **a11y-Tests:** `axe-core` automatisch in E2E-Suite.
- **Compliance-Tests:** automatisch aus `legal_requirements.yaml` generiert.

## Sicherheit

- Keine SQL-Strings konkatenieren — Parametrisierung erzwingen
- Keine `eval`, `exec` außer mit dreifacher Begründung im Code-Review
- Eingabe-Validierung mit Pydantic auf API-Ebene, nicht im Frontend (nur dort zusätzlich für UX)
- CSP strikt, kein `unsafe-inline`
- Cookies: HttpOnly, Secure, SameSite=Strict

## Patientendaten

- **Niemals in Logs.** Stattdessen: opaque IDs.
- **Niemals in Fehlermeldungen** an den Client. Server-Error → "Etwas ist schiefgelaufen, Bug-ID xyz" + Server-Side-Log.
- **Niemals in LLM-Prompts** ohne vorherige Anonymisierung (`packages/llm/anonymize.py`).

## Barrierefreiheit (WCAG 2.1 AA)

- Mindest-Schriftgröße: 18px (für Bewohner-UI: 22px)
- Kontrast: ≥ 4.5:1 normaler Text, ≥ 3:1 große Texte
- Tab-Navigation überall möglich
- Bildschirmleser-Tests mit VoiceOver/NVDA stichprobenartig
- Keine zeitkritischen Interaktionen ohne Pause/Verlängerungsoption

## CHANGELOG-Format

Für Pflegekräfte verständlich, nicht für Entwickler:

```
## 2026-05-27 — Tag 3

### Neu
- **Bewohner können jetzt ihren Tagesablauf selbst gestalten.** 
  In der App auf "Mein Tag" tippen. Sprachsteuerung möglich.

### Verbessert
- Schichtübergabe-Notiz lädt schneller (besonders auf älteren Tablets).

### Behoben
- Anmelden funktionierte nicht, wenn das Passwort ein Sonderzeichen enthielt.

### Hinter den Kulissen
- pgvector-Index für semantische Suche eingerichtet (Phase 3 Vorbereitung)
- Community-Beitrag von R. Becker umgesetzt: Stimmungs-Check 1-Klick-Variante
```
