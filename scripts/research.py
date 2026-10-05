"""Monatlicher Recherche-Lauf: Was macht gute Pflegesoftware aus — international?

Läuft am 15. jedes Monats (Cron). Ein Modell mit Websuche recherchiert zu einem
wechselnden Schwerpunkt, schreibt einen öffentlichen Bericht mit Quellen und
leitet daraus Ideen ab, die gegen die drei Prinzipien bewertet sind.

Die Ideen landen NICHT direkt im Task-Backlog, sondern in ideas/inbox/ —
eine öffentliche Zwischenstufe. Erst die Zerlegung in Tasks mit fertigen Tests
macht daraus Arbeit für den Build-Agenten (L4, L9: genau dort entstehen Fehler).

Verwendung:
  python3 scripts/research.py                  # Schwerpunkt nach Monat rotierend
  python3 scripts/research.py --thema "..."    # eigener Schwerpunkt
  python3 scripts/research.py --no-push
"""

from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from packages.llm.budget_guard import BudgetExceeded, BudgetGuard  # noqa: E402
from packages.llm.openrouter_client import ModelChoice, OpenRouterClient  # noqa: E402

REPORTS = ROOT / "reports" / "research"
IDEAS = ROOT / "ideas" / "inbox"

# Rotierende Schwerpunkte — einer pro Monat, damit die Recherche in die Tiefe geht
THEMEN = [
    "Personenzentrierte Pflegedokumentation: Wie dokumentieren Länder wie die Niederlande (Buurtzorg, Omaha-System), Skandinavien und Neuseeland Biografie, Wünsche und Lebensqualität statt nur Defizite?",
    "Dokumentationsaufwand in der Langzeitpflege: Was zeigt Forschung zu Zeitanteilen, Entbürokratisierung (z.B. Strukturmodell/SIS in Deutschland) und Software, die Doku tatsächlich reduziert?",
    "Software für Menschen mit Demenz und ihre Angehörigen: Welche digitalen Ansätze (Biografiearbeit, Erinnerungsalben, Wunsch-Tracking, mutmaßlicher Wille) gelten international als gut belegt?",
    "Pflegekräfte als Gestalter: Beispiele für Pflegesoftware, die partizipativ mit Pflegenden entwickelt wurde, und was dabei anders lief (Co-Design, Nurse-led Informatics).",
    "Übergaben und Kommunikation im Team: Sprachbasierte Dokumentation, strukturierte Übergaben (SBAR, I-PASS) und ihr Nutzen in der stationären Langzeitpflege.",
    "Offene Standards und Interoperabilität in der Pflege: FHIR-Profile für Pflege, ePflegebericht, Datenportabilität und Open-Source-Pflegesoftware weltweit.",
]

SYSTEM = """Du bist Recherche-Assistent eines offenen Experiments: Eine KI baut eine
personenzentrierte Software für die stationäre Langzeitpflege in Deutschland.

Die drei unverhandelbaren Prinzipien:
1. Personenzentrierung — Bewohner:innen sind Menschen mit Biografie, keine Fälle.
2. Empowerment — Pflegekräfte gestalten, KI dient ihnen. Kein KI-Output wird ohne
   ihre Bestätigung Teil der Doku. Keine Überwachung von Pflegekräften.
3. Offenheit — Open Source, öffentliche Begründungen.

Recherchiere international mit der Websuche. Nenne nur Quellen, die du tatsächlich
gefunden hast, mit URL. Unterscheide klar zwischen belegter Evidenz und Einzelbeispiel.
Keine Marketingaussagen von Herstellern ungeprüft übernehmen.

Antwortformat (Markdown):

## Kernerkenntnisse
(4-7 Punkte, je mit Quelle)
## Gute Beispiele international
(3-5 Beispiele: was, wo, warum gut, Quelle)
## Was das für PflegeOS bedeutet
(kurz)
## Quellen
(nummerierte Liste mit URLs)"""

IDEEN_SYSTEM = """Leite aus dem Recherchebericht 3 bis 6 Ideen für PflegeOS ab.
Antworte NUR mit einem JSON-Array:
[{"titel": "...", "beschreibung": "2-4 Sätze, konkret umsetzbar als kleines Feature",
  "inspiration": "woher (mit Quellen-Nr. aus dem Bericht)", "pz": 0-5, "emp": 0-5, "kom": 0-5,
  "prinzipien_check": "ein Satz: warum passt das zu den Prinzipien, oder welches Risiko"}]
pz = Personenzentrierung, emp = Empowerment, kom = Komplexität (5 = sehr aufwendig).
Bevorzuge kleine, sichtbare Features, die auf dem bestehenden Stand aufbauen:
Bewohnerprofil mit Biografie und Wünschen, Reflexions-Tool für Pflegekräfte,
Audit-Log, servergerenderte Oberfläche."""


def _slug(s: str) -> str:
    s = s.lower()
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        s = s.replace(a, b)
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:50]


async def run(thema: str) -> tuple[str, list[dict], float]:
    guard = BudgetGuard()
    client = OpenRouterClient(timeout_s=300.0)
    est = OpenRouterClient.estimate_cost(ModelChoice.RESEARCH, 30_000, 6_000) + 0.05
    guard.reserve(est, pot="research")
    resp = await client.chat(
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": f"Schwerpunkt dieser Recherche:\n\n{thema}"},
        ],
        model=ModelChoice.RESEARCH,
        max_tokens=12_000,
        temperature=0.3,
        # OpenRouter-Websuche, für jedes Modell verfügbar
        extra={"plugins": [{"id": "web", "max_results": 8}]},
    )
    guard.commit(resp.cost_usd or est, pot="research")

    bericht = resp.text.strip()
    ideen, cost2 = await ideen_ableiten(client, guard, bericht)
    return bericht, ideen, (resp.cost_usd or 0) + cost2


async def ideen_ableiten(client, guard, bericht: str) -> tuple[list[dict], float]:
    """Zweiter, kleiner Aufruf ohne Websuche — robuster als alles in einer Antwort."""
    est = OpenRouterClient.estimate_cost(ModelChoice.RESEARCH, 8_000, 2_500)
    guard.reserve(est, pot="research")
    resp = await client.chat(
        messages=[{"role": "system", "content": IDEEN_SYSTEM},
                  {"role": "user", "content": bericht}],
        model=ModelChoice.RESEARCH, max_tokens=3_000, temperature=0.3,
    )
    guard.commit(resp.cost_usd or est, pot="research")
    raw = resp.text
    raw = raw[raw.find("["): raw.rfind("]") + 1]
    try:
        return json.loads(raw), resp.cost_usd or 0
    except json.JSONDecodeError:
        print("[research] Ideen-JSON nicht lesbar")
        return [], resp.cost_usd or 0



def write_outputs(thema: str, bericht: str, ideen: list[dict], cost: float) -> list[Path]:
    today = dt.date.today().isoformat()
    REPORTS.mkdir(parents=True, exist_ok=True)
    IDEAS.mkdir(parents=True, exist_ok=True)

    report = REPORTS / f"{today}.md"
    report.write_text(
        f"# Recherche — {today}\n\n**Schwerpunkt:** {thema}\n\n"
        f"{bericht}\n\n---\n\n## Abgeleitete Ideen\n\n"
        + "".join(
            f"- **{i.get('titel', '?')}** (PZ {i.get('pz', '?')}, EMP {i.get('emp', '?')}, "
            f"Aufwand {i.get('kom', '?')}) → `ideas/inbox/{today}-{_slug(i.get('titel', 'idee'))}.md`\n"
            for i in ideen
        )
        + f"\n*Kosten: ${cost:.3f} · automatisch erstellt von research.py. "
        "Die Quellen bitte vor Verwendung prüfen — Modelle können sich irren.*\n"
    )
    written = [report]
    for i in ideen:
        score = 3 * int(i.get("pz", 0)) + 3 * int(i.get("emp", 0)) - 2 * int(i.get("kom", 0))
        p = IDEAS / f"{today}-{_slug(i.get('titel', 'idee'))}.md"
        p.write_text(
            f"---\ntitel: {json.dumps(i.get('titel', ''), ensure_ascii=False)}\n"
            f"quelle: research {today}\npz: {i.get('pz')}\nemp: {i.get('emp')}\n"
            f"kom: {i.get('kom')}\nscore: {score}\nstatus: neu\n---\n\n"
            f"{i.get('beschreibung', '')}\n\n**Inspiration:** {i.get('inspiration', '')}\n\n"
            f"**Prinzipien-Check:** {i.get('prinzipien_check', '')}\n"
        )
        written.append(p)
    return written


def git_commit_push(paths: list[Path], msg: str) -> None:
    subprocess.run(["git", "-C", str(ROOT), "add", *map(str, paths)], check=False)
    subprocess.run(["git", "-C", str(ROOT), "commit", "-m", msg], check=False)
    if subprocess.run(["git", "-C", str(ROOT), "push"], capture_output=True).returncode != 0:
        subprocess.run(["git", "-C", str(ROOT), "pull", "--rebase", "origin", "main"], check=False)
        subprocess.run(["git", "-C", str(ROOT), "push"], check=False)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--thema")
    ap.add_argument("--no-push", action="store_true")
    ap.add_argument("--ideen-aus", help="nur Ideen aus einem vorhandenen Bericht ableiten")
    args = ap.parse_args()

    if args.ideen_aus:
        src = Path(args.ideen_aus)
        text = src.read_text()
        thema = re.search(r"\*\*Schwerpunkt:\*\* (.*)", text).group(1)
        bericht = text.split("\n", 3)[3].split("\n---\n\n## Abgeleitete Ideen")[0]
        async def _nur_ideen():
            return await ideen_ableiten(OpenRouterClient(timeout_s=300.0), BudgetGuard(), bericht)
        ideen, cost = asyncio.run(_nur_ideen())
        written = write_outputs(thema, bericht.split("**Schwerpunkt:**")[-1].split("\n", 1)[-1].strip(), ideen, cost)
        print(f"[research] {len(ideen)} Ideen aus {src.name}")
        if not args.no_push:
            git_commit_push(written, f"docs(research): Ideen aus {src.name} — {len(ideen)} Ideen")
        return 0

    thema = args.thema or THEMEN[dt.date.today().month % len(THEMEN)]
    print(f"[research] Schwerpunkt: {thema[:90]}…")
    try:
        bericht, ideen, cost = asyncio.run(run(thema))
    except BudgetExceeded as e:
        print(f"[research] Budget: {e}")
        return 1
    written = write_outputs(thema, bericht, ideen, cost)
    print(f"[research] {len(ideen)} Ideen, Kosten ${cost:.3f}")
    for p in written:
        print(f"  → {p.relative_to(ROOT)}")
    if not args.no_push:
        git_commit_push(written, f"docs(research): {dt.date.today().isoformat()} — {len(ideen)} Ideen")
    return 0


if __name__ == "__main__":
    sys.exit(main())
