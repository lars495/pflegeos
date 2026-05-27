"""Monatlicher KI-Jurist.

Läuft am 1. jeden Monats. Eigener Budget-Topf (`pot="legal"`).

Aufgaben:
  1. Crawlt offizielle Quellen für neue/geänderte Anforderungen
  2. Liest aktuelles legal_requirements.yaml
  3. Prüft Codebase auf Erfüllung
  4. Schreibt reports/legal/YYYY-MM.md
  5. Schreibt GitHub-Issues für Gaps (via gh CLI)

Crawl-Quellen sind absichtlich konservativ — nur öffentliche, stabile Endpunkte.
Tieferes Scraping kommt mit Phase 5.
"""

from __future__ import annotations

import asyncio
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

import httpx
import yaml

from packages.llm.budget_guard import BudgetExceeded, BudgetGuard
from packages.llm.openrouter_client import ModelChoice, OpenRouterClient


ROOT = Path(__file__).resolve().parents[1]
REQS_FILE = ROOT / "legal_requirements.yaml"
REPORT_DIR = ROOT / "reports" / "legal"

# Quellen: öffentlich, stabil, ohne Auth
SOURCES = {
    "gesetze-im-internet": "https://www.gesetze-im-internet.de/",
    "bundesanzeiger": "https://www.bundesanzeiger.de/pub/de/amtlicher-teil",
    "md-bund": "https://md-bund.de/themen/pflegequalitaet.html",
    "dnqp": "https://www.dnqp.de/expertenstandards-und-auditinstrumente/",
}


def _load_requirements() -> dict:
    with REQS_FILE.open() as f:
        return yaml.safe_load(f)


def _save_requirements(data: dict) -> None:
    with REQS_FILE.open("w") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)


async def _fetch_source(client: httpx.AsyncClient, name: str, url: str) -> tuple[str, str]:
    try:
        r = await client.get(url, timeout=20.0, follow_redirects=True)
        return name, r.text[:50_000]  # cap pro Quelle
    except Exception as e:  # pragma: no cover
        return name, f"<<FETCH ERROR: {e}>>"


async def _gather_sources() -> dict[str, str]:
    async with httpx.AsyncClient(headers={"User-Agent": "PflegeOS-LegalBot/1.0"}) as c:
        results = await asyncio.gather(*[
            _fetch_source(c, name, url) for name, url in SOURCES.items()
        ])
    return dict(results)


def _build_prompt(reqs: dict, sources: dict[str, str]) -> str:
    return f"""Du bist Compliance-Reviewer für eine Pflegesoftware in Deutschland.

AKTUELLE ANFORDERUNGEN (legal_requirements.yaml):
{yaml.safe_dump(reqs, allow_unicode=True, sort_keys=False)}

QUELLEN-AUSZÜGE (gekürzt):
{json.dumps({k: v[:5000] for k, v in sources.items()}, ensure_ascii=False, indent=2)}

AUFGABEN — antworte als JSON mit folgender Struktur:
{{
  "new_requirements": [
    {{"id": "...", "title": "...", "source_url": "...", "summary": "...",
      "severity": "critical|high|medium|low", "affects": ["Modul1", "Modul2"]}}
  ],
  "updates_to_existing": [
    {{"id": "BESTEHENDE_ID", "change_summary": "..."}}
  ],
  "review_notes": "Allgemeine Anmerkungen, keine Empfehlungen zum Code"
}}

Prinzipien:
- Quellen, die du nicht hast, NICHT erfinden
- Bei Unsicherheit weglassen
- Nur tatsächlich neu oder geändert seit Status quo
- Sprache: deutsch, präzise, juristisch sauber
"""


async def main() -> int:
    today = dt.date.today()
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_file = REPORT_DIR / f"{today.strftime('%Y-%m')}.md"

    print(f"[legal-audit] start {today}")

    guard = BudgetGuard()
    client = OpenRouterClient()

    # Budget-Check vorab — Sonnet ist teurer
    if guard.is_exhausted(pot="legal"):
        print("[legal-audit] Monatsbudget bereits aufgebraucht — Abbruch")
        return 1

    reqs = _load_requirements()
    sources = await _gather_sources()
    prompt = _build_prompt(reqs, sources)

    # Schätzung: ~30k Prompt-Tokens, ~5k Completion → ~$0.20 mit Sonnet
    est = OpenRouterClient.estimate_cost(ModelChoice.LEGAL, 30_000, 5_000)
    try:
        guard.reserve(est, pot="legal")
    except BudgetExceeded as e:
        print(f"[legal-audit] Budget-Reservierung scheitert: {e}")
        return 1

    response = await client.chat(
        messages=[
            {"role": "system", "content": "Du bist Compliance-Reviewer für deutsche Pflegesoftware. Antworte ausschließlich als valides JSON."},
            {"role": "user", "content": prompt},
        ],
        model=ModelChoice.LEGAL,
        max_tokens=4_000,
        temperature=0.0,
    )
    guard.commit(response.cost_usd or est, pot="legal")

    # JSON parsen
    try:
        result = json.loads(response.text)
    except json.JSONDecodeError:
        # Versuche das erste JSON-Objekt zu extrahieren
        start, end = response.text.find("{"), response.text.rfind("}")
        result = json.loads(response.text[start : end + 1]) if start >= 0 else {}

    # Report schreiben
    with report_file.open("w") as f:
        f.write(f"# Legal Audit — {today.strftime('%B %Y')}\n\n")
        f.write(f"Modell: `{response.model}` · Kosten: ${response.cost_usd:.4f}\n\n")
        f.write("## Neue Anforderungen\n\n")
        for r in result.get("new_requirements", []):
            f.write(f"- **{r.get('id')}** ({r.get('severity')}): {r.get('title')}\n")
            f.write(f"  - Quelle: {r.get('source_url')}\n")
            f.write(f"  - Betrifft: {', '.join(r.get('affects', []))}\n")
            f.write(f"  - {r.get('summary')}\n\n")
        f.write("## Änderungen an bestehenden Anforderungen\n\n")
        for u in result.get("updates_to_existing", []):
            f.write(f"- **{u.get('id')}**: {u.get('change_summary')}\n")
        f.write("\n## Anmerkungen\n\n")
        f.write(result.get("review_notes", "—") + "\n")

    # Issues anlegen
    for r in result.get("new_requirements", []):
        title = f"[legal] {r.get('id')}: {r.get('title')}"
        body = (
            f"Quelle: {r.get('source_url')}\n\n"
            f"Severity: {r.get('severity')}\n\n"
            f"Zusammenfassung: {r.get('summary')}\n\n"
            f"Betrifft: {', '.join(r.get('affects', []))}\n"
        )
        try:
            subprocess.run(
                ["gh", "issue", "create", "--title", title, "--body", body, "--label", "legal"],
                check=False,
                cwd=ROOT,
            )
        except FileNotFoundError:
            print("[legal-audit] gh CLI fehlt — Issues nicht erstellt")

    # Anforderungen mergen
    existing_ids = {r["id"] for r in reqs["requirements"]}
    for r in result.get("new_requirements", []):
        if r.get("id") and r["id"] not in existing_ids:
            reqs["requirements"].append(
                {
                    "id": r["id"],
                    "title": r.get("title"),
                    "source_url": r.get("source_url"),
                    "summary": r.get("summary"),
                    "affects": r.get("affects", []),
                    "implemented_in": [],
                    "test_files": [],
                    "status": "gap",
                    "severity": r.get("severity", "medium"),
                    "last_verified": None,
                }
            )
    reqs["last_audit"] = today.isoformat()
    _save_requirements(reqs)

    print(f"[legal-audit] done → {report_file}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
