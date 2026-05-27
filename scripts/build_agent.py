"""PflegeOS Build Agent — autonomer täglicher Feature-Bau.

Verwendung:
  python scripts/build_agent.py                # voller Lauf
  python scripts/build_agent.py --dry-run      # plant, schreibt aber keine Datei
  python scripts/build_agent.py --max-calls 1  # nur ein LLM-Call (debug)

Verhalten:
  1. Lädt Kontext: PRINCIPLES, AGENT_INSTRUCTIONS, ROADMAP, CHANGELOG, legal_requirements
  2. Wählt offenes Feature mit höchstem Score aus aktueller Phase
  3. Ruft OpenRouter (Deepseek-V3 als Default, billiger Fallback bei Budgetdruck)
  4. Wendet Datei-Änderungen an (geschützt durch Allow-/Deny-List)
  5. Führt Tests aus (pytest + compliance check)
  6. Bei grün: commit + push + daily report
  7. Bei rot: revert + report mit Fehler-Begründung

Sicherheits-Grenzen:
  - max $1.10/Tag (über BudgetGuard)
  - max N LLM-Calls/Lauf (Default 3)
  - geschützte Dateien (PRINCIPLES.md, LICENSE, etc.) werden nie editiert
"""

from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Stelle sicher, dass das Repo-Root im sys.path ist
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from packages.llm.budget_guard import BudgetExceeded, BudgetGuard  # noqa: E402
from packages.llm.openrouter_client import ModelChoice, OpenRouterClient  # noqa: E402


# ────────────────────────────────────────────────────────────────────
# Konfiguration — Allow-/Deny-Listen
# ────────────────────────────────────────────────────────────────────

# Dateien, die der Agent NIEMALS verändern darf
PROTECTED_PATHS: set[str] = {
    "PRINCIPLES.md",
    "AGENT_INSTRUCTIONS.md",
    "LICENSE",
    "NOTICE",
    "infra/.env",
    "infra/.env.example",
    "scripts/build_agent.py",  # der Agent darf sich nicht selbst editieren
}

# Pfad-Präfixe, in denen der Agent operieren darf
ALLOWED_PREFIXES: tuple[str, ...] = (
    "apps/",
    "packages/",
    "scripts/",
    "tests/",
    "infra/",
    "contributions/",
    "reports/",
    "ROADMAP.md",
    "CHANGELOG.md",
    "legal_requirements.yaml",
    "README.md",
    "ARCHITECTURE.md",
    "CONVENTIONS.md",
    "Makefile",
)


# ────────────────────────────────────────────────────────────────────
# Roadmap-Parser
# ────────────────────────────────────────────────────────────────────

@dataclass
class RoadmapItem:
    phase: str
    status: str  # ⏳ | 🔨 | ✅ | ⛔ | ❌
    title: str
    pz: int
    emp: int
    com: int
    eff: int
    kom: int
    score: int

    @property
    def is_open(self) -> bool:
        return self.status in {"⏳", "🔨"}


def parse_roadmap() -> list[RoadmapItem]:
    """Sehr defensiv: liest ROADMAP.md und extrahiert Tabellen-Zeilen."""
    text = (ROOT / "ROADMAP.md").read_text()
    items: list[RoadmapItem] = []
    current_phase = "unknown"

    # Tabellen-Zeile: | ⏳ | Feature | 5 | 3 | 4 | 2 | 3 | **27** |
    row_re = re.compile(
        r"^\|\s*([⏳🔨✅⛔❌])\s*\|\s*(.+?)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*\**(\d+)\**\s*\|"
    )

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("## Phase"):
            current_phase = stripped.lstrip("# ").strip()
        m = row_re.match(line)
        if not m:
            continue
        status, title, pz, emp, com, eff, kom, score = m.groups()
        items.append(
            RoadmapItem(
                phase=current_phase,
                status=status,
                title=title,
                pz=int(pz),
                emp=int(emp),
                com=int(com),
                eff=int(eff),
                kom=int(kom),
                score=int(score),
            )
        )
    return items


def select_feature(items: list[RoadmapItem]) -> RoadmapItem | None:
    """Wählt offenes Feature mit höchstem Score in der frühesten Phase."""
    opens = [i for i in items if i.is_open]
    if not opens:
        return None
    # Sortierung: erst nach Phase (erster zuerst), dann nach Score absteigend
    opens.sort(key=lambda i: (i.phase, -i.score))
    return opens[0]


# ────────────────────────────────────────────────────────────────────
# Kontext-Loader
# ────────────────────────────────────────────────────────────────────

def load_context() -> dict[str, str]:
    files_to_load = [
        "PRINCIPLES.md",
        "AGENT_INSTRUCTIONS.md",
        "ROADMAP.md",
        "CHANGELOG.md",
        "CONVENTIONS.md",
        "legal_requirements.yaml",
    ]
    return {f: (ROOT / f).read_text() for f in files_to_load if (ROOT / f).exists()}


def list_repo_tree() -> str:
    """Liefert Pfad-Liste aller versionierten Dateien (max 300 Einträge)."""
    out = subprocess.check_output(
        ["git", "-C", str(ROOT), "ls-files"], text=True
    )
    paths = sorted(out.strip().splitlines())
    return "\n".join(paths[:300])


# ────────────────────────────────────────────────────────────────────
# LLM-Interaktion
# ────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """Du bist der PflegeOS Build-Agent.

Du baust eine deutsche Pflegesoftware autonom weiter. Die drei Säulen aus
PRINCIPLES.md sind verbindlich. Dein Auftrag heute: ein konkretes Feature
aus ROADMAP.md vorantreiben.

Antworte AUSSCHLIESSLICH als valides JSON mit folgender Struktur:

{
  "feature_title": "string — exakt der Titel aus ROADMAP",
  "plan": "string — 2-4 Sätze: was du tust und warum (deutsch)",
  "files": [
    {
      "path": "string — relativ zum Repo-Root",
      "operation": "create" | "update" | "delete",
      "content": "string — vollständiger neuer Dateiinhalt (bei delete leer)",
      "rationale": "string — kurze Begründung (deutsch)"
    }
  ],
  "tests_to_run": ["pytest -q tests/", "..."],
  "changelog_entry": "string — pflegekraftverständlich, 2-4 Sätze (deutsch)",
  "roadmap_status_update": "✅" | "🔨" | "⏳",
  "next_focus": "string — was morgen wahrscheinlich kommt (deutsch)"
}

REGELN (hart):
- Niemals diese Dateien editieren: PRINCIPLES.md, AGENT_INSTRUCTIONS.md, LICENSE, NOTICE, infra/.env, scripts/build_agent.py
- Niemals Patientendaten in Beispielen verwenden — wenn nötig synthetisch: "Max Mustermann"
- Code-Stil: Python ruff-konform, TypeScript prettier-konform, deutsch in UI-Strings
- Tests: jede neue Funktion braucht einen Test (TDD)
- a11y: bei Frontend-Änderungen Mindest-Schriftgröße 18px, Kontraste prüfen
- Kein KI-Output darf ohne Pflegekraft-Bestätigung Pflegedoku werden
- Bei Konflikt Effizienz vs. Personenzentrierung → Personenzentrierung gewinnt
- Bleibe in deinem Scope: ein Feature pro Lauf, keine Mega-PRs
"""


def user_prompt(context: dict[str, str], tree: str, feature: RoadmapItem) -> str:
    parts = ["# Kontext aus dem Repo\n"]
    for name, content in context.items():
        # Kappe lange Dateien defensiv
        if len(content) > 12_000:
            content = content[:12_000] + "\n... [gekürzt]"
        parts.append(f"\n## {name}\n\n{content}\n")

    parts.append("\n## Repo-Dateibaum (Auszug)\n\n" + tree + "\n")
    parts.append(f"\n## Heute zu bauen\n\n**{feature.title}** ({feature.phase})\n\nScore: {feature.score} (PZ={feature.pz}, EMP={feature.emp}, COM={feature.com}, EFF={feature.eff}, KOM={feature.kom})\n")
    parts.append("\nBau es. Antworte als JSON.\n")
    return "".join(parts)


async def call_llm(
    client: OpenRouterClient,
    guard: BudgetGuard,
    messages: list[dict[str, str]],
    max_tokens: int = 8_000,
) -> dict[str, Any]:
    # Schätzung: prompt ~15-20k token, completion ~5-8k
    prompt_tokens_est = sum(len(m["content"]) // 3 for m in messages)
    model = ModelChoice.BUILD_CHEAP if guard.should_downshift() else ModelChoice.BUILD_PRIMARY
    est = OpenRouterClient.estimate_cost(model, prompt_tokens_est, max_tokens)
    guard.reserve(est)

    resp = await client.chat(
        messages=messages,
        model=model,
        max_tokens=max_tokens,
        temperature=0.2,
    )
    guard.commit(resp.cost_usd or est)
    print(f"[llm] model={resp.model} cost=${resp.cost_usd:.4f} tokens={resp.prompt_tokens}+{resp.completion_tokens}")

    text = resp.text
    # JSON-Extraktion: tolerant gegenüber Code-Fences und Vor-/Nachgeplauder
    if "```" in text:
        # Erstes ```json oder ``` Block
        m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if m:
            text = m.group(1)
    if not text.strip().startswith("{"):
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            text = text[start : end + 1]
    return json.loads(text)


# ────────────────────────────────────────────────────────────────────
# Datei-Anwendung (mit Schutz)
# ────────────────────────────────────────────────────────────────────

def is_path_allowed(rel: str) -> tuple[bool, str]:
    if rel in PROTECTED_PATHS:
        return False, f"PROTECTED: {rel}"
    if not any(rel == p or rel.startswith(p) for p in ALLOWED_PREFIXES):
        return False, f"OUT_OF_SCOPE: {rel}"
    if ".." in rel.split("/") or rel.startswith("/"):
        return False, f"INVALID_PATH: {rel}"
    return True, "ok"


def apply_files(files: list[dict[str, Any]], dry_run: bool = False) -> list[str]:
    """Wendet Dateiänderungen an. Gibt Liste tatsächlich geänderter Pfade zurück."""
    changed: list[str] = []
    for f in files:
        path = f.get("path", "").strip()
        op = f.get("operation", "update")
        content = f.get("content", "")

        ok, reason = is_path_allowed(path)
        if not ok:
            print(f"[skip] {reason}")
            continue

        full = ROOT / path
        if op == "delete":
            if full.exists():
                if not dry_run:
                    full.unlink()
                print(f"[del]  {path}")
                changed.append(path)
        elif op in ("create", "update"):
            if dry_run:
                print(f"[dry]  would {op} {path} ({len(content)} chars)")
                continue
            full.parent.mkdir(parents=True, exist_ok=True)
            full.write_text(content)
            print(f"[{op[:3]}]  {path}")
            changed.append(path)
        else:
            print(f"[skip] unknown op '{op}' for {path}")
    return changed


# ────────────────────────────────────────────────────────────────────
# Tests + Commit
# ────────────────────────────────────────────────────────────────────

def run_tests(commands: list[str]) -> tuple[bool, str]:
    log: list[str] = []
    for cmd in commands:
        log.append(f"$ {cmd}")
        try:
            result = subprocess.run(
                cmd, shell=True, cwd=ROOT, capture_output=True, text=True, timeout=300
            )
        except subprocess.TimeoutExpired:
            log.append(f"  TIMEOUT after 300s")
            return False, "\n".join(log)
        log.append(result.stdout[-3000:] if result.stdout else "")
        if result.returncode != 0:
            log.append(result.stderr[-3000:] if result.stderr else "")
            log.append(f"[FAIL] exit {result.returncode}")
            return False, "\n".join(log)
        log.append("[ok]")
    return True, "\n".join(log)


def git_status() -> str:
    return subprocess.check_output(["git", "-C", str(ROOT), "status", "--short"], text=True)


def git_revert_all() -> None:
    subprocess.run(["git", "-C", str(ROOT), "checkout", "--", "."], check=False)
    subprocess.run(["git", "-C", str(ROOT), "clean", "-fd"], check=False)


def git_commit_push(message: str) -> bool:
    subprocess.run(["git", "-C", str(ROOT), "add", "-A"], check=True)
    r = subprocess.run(
        ["git", "-C", str(ROOT), "commit", "-m", message],
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        if "nothing to commit" in (r.stdout + r.stderr).lower():
            print("[git] nichts zu committen")
            return False
        print(f"[git] commit failed: {r.stderr}")
        return False
    p = subprocess.run(["git", "-C", str(ROOT), "push"], capture_output=True, text=True)
    if p.returncode != 0:
        print(f"[git] push failed: {p.stderr}")
        return False
    return True


# ────────────────────────────────────────────────────────────────────
# Daily Report
# ────────────────────────────────────────────────────────────────────

def write_daily_report(
    feature: RoadmapItem,
    plan: dict[str, Any],
    success: bool,
    test_log: str,
    cost_usd: float,
) -> Path:
    today = dt.date.today().isoformat()
    p = ROOT / "reports" / "daily" / f"{today}.md"
    p.parent.mkdir(parents=True, exist_ok=True)

    icon = "✅" if success else "⛔"
    body = f"""# Tag — {today}

## Heute gebaut: {feature.title}

**Status:** {icon} {'erfolgreich' if success else 'abgebrochen'} · **Phase:** {feature.phase}

### Was geplant war
{plan.get('plan', '—')}

### Was passiert ist
"""
    if success:
        body += f"\n{plan.get('changelog_entry', '—')}\n"
    else:
        body += "\nDie Änderung schlug Tests nicht. Alle Dateien wurden zurückgesetzt. Auszug aus dem Testlog:\n\n```\n"
        body += test_log[-2000:]
        body += "\n```\n"

    body += f"""

### Zahlen heute
| | |
|---|---|
| LLM-Kosten | ${cost_usd:.4f} |
| Status | {'committed' if success else 'reverted'} |

### Was morgen wahrscheinlich kommt
{plan.get('next_focus', '—')}

---

*Dieser Eintrag wurde vom Build-Agent geschrieben. Korrekturen willkommen — als Community-Beitrag oder Pull Request.*
"""
    p.write_text(body)
    return p


# ────────────────────────────────────────────────────────────────────
# Main
# ────────────────────────────────────────────────────────────────────

async def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Nicht schreiben/committen")
    parser.add_argument("--max-calls", type=int, default=2, help="Max LLM-Calls pro Lauf")
    parser.add_argument("--no-push", action="store_true", help="Nicht pushen (lokal testen)")
    args = parser.parse_args(argv)

    print(f"[agent] start {dt.datetime.now().isoformat()}")

    # 1. Roadmap parsen, Feature wählen
    items = parse_roadmap()
    feature = select_feature(items)
    if feature is None:
        print("[agent] kein offenes Roadmap-Item — nichts zu tun")
        return 0
    print(f"[agent] feature: {feature.title} (score={feature.score}, {feature.phase})")

    # 2. Kontext laden
    context = load_context()
    tree = list_repo_tree()

    # 3. Budget-Guard initialisieren
    guard = BudgetGuard()
    if guard.is_exhausted():
        print("[agent] Tagesbudget aufgebraucht — Abbruch")
        return 0

    # 4. LLM-Call
    client = OpenRouterClient()
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt(context, tree, feature)},
    ]

    try:
        plan = await call_llm(client, guard, messages)
    except BudgetExceeded as e:
        print(f"[agent] budget exceeded: {e}")
        return 1
    except json.JSONDecodeError as e:
        print(f"[agent] LLM-Output war kein valides JSON: {e}")
        return 1

    print(f"[agent] plan: {plan.get('plan', '')[:200]}")
    print(f"[agent] {len(plan.get('files', []))} Dateien zu ändern")

    # 5. Anwenden
    changed = apply_files(plan.get("files", []), dry_run=args.dry_run)
    if args.dry_run:
        print("[agent] dry-run — fertig")
        return 0
    if not changed:
        print("[agent] keine Dateien geändert — kein Commit")
        return 0

    # 6. Tests
    test_commands = plan.get("tests_to_run") or ["pytest -q tests/"]
    print(f"[agent] tests: {test_commands}")
    success, test_log = run_tests(test_commands)
    print(f"[agent] tests {'ok' if success else 'FAIL'}")

    # 7. Daily Report immer schreiben
    state = guard.state()
    report_path = write_daily_report(feature, plan, success, test_log, state.spent_usd)
    print(f"[agent] daily report: {report_path}")

    # 8. Commit oder Revert
    if success:
        msg = (
            f"feat: {feature.title}\n\n"
            f"{plan.get('plan', '')}\n\n"
            f"Score {feature.score} ({feature.phase})\n"
            f"Co-Authored-By: PflegeOS Agent <agent@pflegeos.de>"
        )
        if args.no_push:
            subprocess.run(["git", "-C", str(ROOT), "add", "-A"], check=True)
            subprocess.run(["git", "-C", str(ROOT), "commit", "-m", msg], check=True)
            print("[agent] committed (no-push)")
        else:
            if git_commit_push(msg):
                print("[agent] committed + pushed")
            else:
                print("[agent] commit/push fehlgeschlagen")
                return 1
    else:
        print("[agent] tests rot — Dateien werden zurückgesetzt")
        git_revert_all()
        # Daily Report aber behalten (separater commit)
        subprocess.run(["git", "-C", str(ROOT), "add", str(report_path)], check=False)
        subprocess.run(
            ["git", "-C", str(ROOT), "commit", "-m", f"docs(daily): report {dt.date.today().isoformat()} (no feature shipped)"],
            check=False,
        )
        if not args.no_push:
            subprocess.run(["git", "-C", str(ROOT), "push"], check=False)

    print(f"[agent] done. budget: ${state.spent_usd:.4f}/${state.limit_usd:.2f}")
    return 0 if success else 2


if __name__ == "__main__":
    sys.exit(asyncio.run(main(sys.argv[1:])))
