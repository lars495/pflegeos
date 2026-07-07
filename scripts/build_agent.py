"""PflegeOS Build Agent — autonomer täglicher Task-Bau.

Verwendung:
  python scripts/build_agent.py                # voller Lauf
  python scripts/build_agent.py --dry-run      # zeigt Task + Plan, schreibt nichts
  python scripts/build_agent.py --no-push      # committet lokal, pusht nicht

Arbeitsweise (Task-System, siehe tasks/README.md):
  1. Wählt die niedrigste offene Task aus tasks/open/, deren depends_on
     alle in tasks/done/ liegen
  2. Prompt = Task-Beschreibung + vollständige context_files
  3. LLM antwortet im FILE-Block-Format (kein JSON-escaping von Code!)
  4. Schreiben nur in target_files erlaubt
  5. Task-Test läuft im API-Container; rot → Fehlerlog zurück ans Modell,
     bis zu 3 Versuche; letzter Versuch eskaliert auf Hermes 4 405B
  6. Grün → Task nach done/, Commit, Push. Rot nach allen Versuchen →
     attempts_used hochzählen, ggf. nach blocked/ verschieben
  7. tasks/open/ leer → Report "Backlog leer"

Sicherheits-Grenzen:
  - max $1.10/Tag (über BudgetGuard)
  - geschützte Dateien (PRINCIPLES.md, LICENSE, etc.) werden nie editiert
  - Schreiben ausschließlich in die target_files der gewählten Task
"""

from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml

# Stelle sicher, dass das Repo-Root im sys.path ist
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from packages.llm.budget_guard import BudgetExceeded, BudgetGuard  # noqa: E402
from packages.llm.openrouter_client import ModelChoice, OpenRouterClient  # noqa: E402


# ────────────────────────────────────────────────────────────────────
# Konfiguration
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

# Pfad-Präfixe, in denen der Agent operieren darf (Defense in Depth —
# primär gilt: nur target_files der Task)
ALLOWED_PREFIXES: tuple[str, ...] = (
    "apps/",
    "packages/",
    "scripts/",
    "tests/",
    "reports/",
)

TASKS_OPEN = ROOT / "tasks" / "open"
TASKS_DONE = ROOT / "tasks" / "done"
TASKS_BLOCKED = ROOT / "tasks" / "blocked"

MAX_ATTEMPTS_PER_RUN = 3
ESCALATION_MODEL = "nousresearch/hermes-4-405b"  # letzter Versuch, wenn Budget reicht


# ────────────────────────────────────────────────────────────────────
# Task-Loader
# ────────────────────────────────────────────────────────────────────

@dataclass
class Task:
    id: str
    title: str
    path: Path
    body: str
    roadmap_item: str = ""
    depends_on: list[str] = field(default_factory=list)
    target_files: list[str] = field(default_factory=list)
    context_files: list[str] = field(default_factory=list)
    test_command: str = ""
    max_attempts: int = 3
    attempts_used: int = 0
    frontmatter: dict = field(default_factory=dict)


def parse_task(path: Path) -> Task | None:
    text = path.read_text()
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.DOTALL)
    if not m:
        print(f"[tasks] {path.name}: kein Frontmatter — übersprungen")
        return None
    try:
        fm = yaml.safe_load(m.group(1))
    except yaml.YAMLError as e:
        print(f"[tasks] {path.name}: Frontmatter-Fehler {e} — übersprungen")
        return None
    return Task(
        id=str(fm.get("id", path.stem)),
        title=str(fm.get("title", path.stem)),
        path=path,
        body=m.group(2).strip(),
        roadmap_item=str(fm.get("roadmap_item", "")),
        depends_on=[str(d) for d in (fm.get("depends_on") or [])],
        target_files=[str(t) for t in (fm.get("target_files") or [])],
        context_files=[str(c) for c in (fm.get("context_files") or [])],
        test_command=str(fm.get("test_command", "")),
        max_attempts=int(fm.get("max_attempts", 3)),
        attempts_used=int(fm.get("attempts_used", 0)),
        frontmatter=fm,
    )


def done_task_ids() -> set[str]:
    if not TASKS_DONE.exists():
        return set()
    return {p.name.split("-")[0] for p in TASKS_DONE.glob("T*.md")}


def select_task() -> Task | None:
    """Niedrigste offene Task-ID, deren Abhängigkeiten erledigt sind."""
    if not TASKS_OPEN.exists():
        return None
    done = done_task_ids()
    for path in sorted(TASKS_OPEN.glob("T*.md")):
        task = parse_task(path)
        if task is None:
            continue
        missing = [d for d in task.depends_on if d not in done]
        if missing:
            print(f"[tasks] {task.id} wartet auf {missing}")
            continue
        return task
    return None


def update_task_frontmatter(task: Task, **updates) -> None:
    """Schreibt geänderte Frontmatter-Werte zurück in die Task-Datei."""
    fm = dict(task.frontmatter)
    fm.update(updates)
    body = task.path.read_text()
    m = re.match(r"^---\n.*?\n---\n(.*)$", body, re.DOTALL)
    rest = m.group(1) if m else task.body
    new = "---\n" + yaml.safe_dump(fm, allow_unicode=True, sort_keys=False) + "---\n" + rest
    task.path.write_text(new)


# ────────────────────────────────────────────────────────────────────
# Prompts — FILE-Block-Format statt JSON (robuster für kleine Modelle)
# ────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """Du bist der PflegeOS Build-Agent — du baust eine deutsche \
Pflegesoftware, Task für Task.

Du bekommst EINE klar umrissene Aufgabe mit allen nötigen Dateien als Kontext.
Der zugehörige Test existiert bereits — deine Aufgabe ist erfüllt, wenn er grün wird.

ANTWORTFORMAT (exakt einhalten, kein JSON, keine Erklärungen außerhalb der Marker):

===PLAN===
2-3 Sätze auf Deutsch: was du tust.
===FILE: pfad/zur/datei.py===
<vollständiger Dateiinhalt — komplette Datei, kein Diff, keine Auslassungen>
===END===
===CHANGELOG===
2 Sätze auf Deutsch, für Pflegekräfte verständlich (keine Tech-Begriffe).
===DONE===

Bei mehreren Dateien: mehrere FILE/END-Blöcke hintereinander.

HARTE REGELN:
- Schreibe NUR die Dateien, die in der Aufgabe als target_files genannt sind
- Gib IMMER die komplette Datei aus — niemals "..." oder "# Rest unverändert"
- Halte dich exakt an vorgegebene Klassen-, Feld- und Pfadnamen
- Python: SQLAlchemy 2.0 (Mapped/mapped_column), Pydantic v2, async/await
- Keine echten Personendaten — synthetisch heißt "Max Mustermann"
- Deutsch in UI-Strings und Fehlermeldungen, Englisch im Code
"""


def build_user_prompt(task: Task) -> str:
    parts = [f"# Aufgabe {task.id}: {task.title}\n\n{task.body}\n"]
    parts.append(f"\n**target_files (nur diese schreiben):** {', '.join(task.target_files)}\n")
    parts.append("\n# Kontext-Dateien\n")
    for rel in task.context_files:
        p = ROOT / rel
        if not p.exists():
            parts.append(f"\n## {rel}\n\n(existiert noch nicht)\n")
            continue
        content = p.read_text()
        if len(content) > 15_000:
            content = content[:15_000] + "\n... [gekürzt]"
        parts.append(f"\n## {rel}\n\n```\n{content}\n```\n")
    # Prinzipien kompakt
    principles = (ROOT / "PRINCIPLES.md")
    if principles.exists():
        content = principles.read_text()[:4_000]
        parts.append(f"\n# Projekt-Prinzipien (verbindlich)\n\n{content}\n")
    parts.append("\nLos. Antworte exakt im vorgegebenen Format.\n")
    return "".join(parts)


def build_repair_prompt(task: Task, test_log: str) -> str:
    parts = [
        "Der Test ist noch ROT. Analysiere den Fehler und gib ALLE target_files "
        "erneut vollständig und korrigiert aus (gleiches Format wie zuvor).\n",
        f"\n# Testausgabe\n\n```\n{test_log[-6_000:]}\n```\n",
        "\n# Aktueller Stand deiner target_files\n",
    ]
    for rel in task.target_files:
        p = ROOT / rel
        content = p.read_text() if p.exists() else "(existiert nicht)"
        parts.append(f"\n## {rel}\n\n```\n{content[:12_000]}\n```\n")
    return "".join(parts)


# ────────────────────────────────────────────────────────────────────
# LLM-Antwort parsen
# ────────────────────────────────────────────────────────────────────

FILE_RE = re.compile(r"===FILE:\s*(.+?)\s*===\n(.*?)\n===END===", re.DOTALL)
PLAN_RE = re.compile(r"===PLAN===\n(.*?)\n===(?:FILE|CHANGELOG)", re.DOTALL)
CHANGELOG_RE = re.compile(r"===CHANGELOG===\n(.*?)\n===DONE===", re.DOTALL)


def parse_response(text: str) -> tuple[str, dict[str, str], str]:
    """Liefert (plan, {pfad: inhalt}, changelog)."""
    plan_m = PLAN_RE.search(text)
    plan = plan_m.group(1).strip() if plan_m else ""
    files = {m.group(1).strip(): m.group(2) for m in FILE_RE.finditer(text)}
    cl_m = CHANGELOG_RE.search(text)
    changelog = cl_m.group(1).strip() if cl_m else ""
    return plan, files, changelog


# ────────────────────────────────────────────────────────────────────
# LLM-Call
# ────────────────────────────────────────────────────────────────────

async def call_llm(
    client: OpenRouterClient,
    guard: BudgetGuard,
    messages: list[dict[str, str]],
    model: ModelChoice | str = ModelChoice.BUILD_PRIMARY,
    max_tokens: int = 8_000,
) -> str:
    prompt_tokens_est = sum(len(m["content"]) // 3 for m in messages)
    est = OpenRouterClient.estimate_cost(model, prompt_tokens_est, max_tokens)
    guard.reserve(est)
    resp = await client.chat(
        messages=messages,
        model=model,
        max_tokens=max_tokens,
        temperature=0.1,
    )
    guard.commit(resp.cost_usd or est)
    print(
        f"[llm] model={resp.model} cost=${resp.cost_usd:.4f} "
        f"tokens={resp.prompt_tokens}+{resp.completion_tokens}"
    )
    return resp.text


# ────────────────────────────────────────────────────────────────────
# Datei-Anwendung (mit Schutz)
# ────────────────────────────────────────────────────────────────────

def is_path_allowed(rel: str, task: Task) -> tuple[bool, str]:
    if rel in PROTECTED_PATHS:
        return False, f"PROTECTED: {rel}"
    if rel not in task.target_files:
        return False, f"NOT_IN_TARGET_FILES: {rel}"
    if not any(rel == p or rel.startswith(p) for p in ALLOWED_PREFIXES):
        return False, f"OUT_OF_SCOPE: {rel}"
    if ".." in rel.split("/") or rel.startswith("/"):
        return False, f"INVALID_PATH: {rel}"
    return True, "ok"


def apply_files(files: dict[str, str], task: Task, dry_run: bool = False) -> list[str]:
    changed: list[str] = []
    for rel, content in files.items():
        ok, reason = is_path_allowed(rel, task)
        if not ok:
            print(f"[skip] {reason}")
            continue
        if dry_run:
            print(f"[dry]  would write {rel} ({len(content)} chars)")
            continue
        full = ROOT / rel
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(content if content.endswith("\n") else content + "\n")
        print(f"[write] {rel}")
        changed.append(rel)
    return changed


# ────────────────────────────────────────────────────────────────────
# Tests
# ────────────────────────────────────────────────────────────────────

def _wrap_for_container(cmd: str) -> str:
    """Pytest/Make/Python-Calls automatisch in den API-Container routen."""
    prefixes_to_wrap = ("pytest", "python ", "python3 ", "ruff ", "make ")
    bare = cmd.strip()
    if any(bare.startswith(p) for p in prefixes_to_wrap):
        return (
            "docker compose -f infra/docker-compose.yml --env-file infra/.env "
            "exec -T api " + bare
        )
    return cmd


def run_task_test(task: Task) -> tuple[bool, str]:
    """Führt den Task-Test aus. Erfolg = exit 0 UND mindestens ein 'passed'
    (reine Skips zählen nicht — dann fehlt das Zielmodul noch)."""
    cmd = _wrap_for_container(task.test_command or "pytest -q tests/")
    log = [f"$ {cmd}"]
    try:
        result = subprocess.run(
            cmd, shell=True, cwd=ROOT, capture_output=True, text=True, timeout=300
        )
    except subprocess.TimeoutExpired:
        return False, "\n".join(log) + "\nTIMEOUT after 300s"
    out = (result.stdout or "") + "\n" + (result.stderr or "")
    log.append(out[-8_000:])
    if result.returncode != 0:
        log.append(f"[FAIL] exit {result.returncode}")
        return False, "\n".join(log)
    if not re.search(r"\d+ passed", out):
        log.append("[FAIL] Test lief, aber nichts ist 'passed' (nur Skips?)")
        return False, "\n".join(log)
    log.append("[ok]")
    return True, "\n".join(log)


# ────────────────────────────────────────────────────────────────────
# Git
# ────────────────────────────────────────────────────────────────────

def git_revert_all() -> None:
    subprocess.run(["git", "-C", str(ROOT), "checkout", "--", "."], check=False)
    subprocess.run(["git", "-C", str(ROOT), "clean", "-fd", "--exclude=logs"], check=False)


def git_push_with_rebase() -> bool:
    """Push mit Rebase-Retry — sonst stauen sich Commits still (siehe 06/2026)."""
    for attempt in (1, 2):
        p = subprocess.run(["git", "-C", str(ROOT), "push"], capture_output=True, text=True)
        if p.returncode == 0:
            return True
        print(f"[git] push fehlgeschlagen (Versuch {attempt}): {p.stderr.strip()}")
        rb = subprocess.run(
            ["git", "-C", str(ROOT), "pull", "--rebase", "origin", "main"],
            capture_output=True,
            text=True,
        )
        if rb.returncode != 0:
            subprocess.run(["git", "-C", str(ROOT), "rebase", "--abort"], check=False)
            print(f"[git] rebase fehlgeschlagen — Commit bleibt lokal: {rb.stderr.strip()}")
            return False
    print("[git] push auch nach Rebase fehlgeschlagen — Commit bleibt lokal!")
    return False


def git_commit(message: str) -> bool:
    subprocess.run(["git", "-C", str(ROOT), "add", "-A"], check=True)
    r = subprocess.run(
        ["git", "-C", str(ROOT), "commit", "-m", message],
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        if "nothing to commit" in (r.stdout + r.stderr).lower():
            print("[git] nichts zu committen")
        else:
            print(f"[git] commit failed: {r.stderr}")
        return False
    return True


# ────────────────────────────────────────────────────────────────────
# Daily Report
# ────────────────────────────────────────────────────────────────────

def write_daily_report(
    task: Task | None,
    plan: str,
    changelog: str,
    success: bool,
    test_log: str,
    cost_usd: float,
    attempts: int,
    escalated: bool,
) -> Path:
    today = dt.date.today().isoformat()
    p = ROOT / "reports" / "daily" / f"{today}.md"
    p.parent.mkdir(parents=True, exist_ok=True)

    if task is None:
        p.write_text(
            f"# Tag — {today}\n\n"
            "## Backlog leer\n\n"
            "Keine offene Task in tasks/open/. Es wird Nachschub aus der "
            "Roadmap gebraucht (monatliche Zerlegung, siehe tasks/README.md).\n"
        )
        return p

    icon = "✅" if success else "⛔"
    body = f"""# Tag — {today}

## Task {task.id}: {task.title}

**Status:** {icon} {"erledigt" if success else "nicht geschafft"} · \
**Roadmap:** {task.roadmap_item or "—"} · **Versuche heute:** {attempts}\
{" · **Eskalation auf 405B**" if escalated else ""}

### Plan
{plan or "—"}

"""
    if success:
        body += f"### Für Pflegekräfte heißt das\n{changelog or '—'}\n"
    else:
        body += (
            "### Woran es scheiterte\n\nTest blieb rot. Auszug:\n\n```\n"
            + test_log[-2_000:]
            + "\n```\n"
        )
        if task.attempts_used + 1 >= task.max_attempts:
            body += (
                "\n⚠️ Task ist jetzt **blockiert** (max. Versuche erreicht) "
                "und wandert nach tasks/blocked/ — braucht menschliche Hilfe.\n"
            )

    body += f"""
### Zahlen heute
| | |
|---|---|
| LLM-Kosten | ${cost_usd:.4f} |
| Status | {"committed" if success else "reverted"} |

---

*Dieser Eintrag wurde vom Build-Agent geschrieben. Korrekturen willkommen —
als Community-Beitrag oder Pull Request.*
"""
    p.write_text(body)
    return p


# ────────────────────────────────────────────────────────────────────
# Main
# ────────────────────────────────────────────────────────────────────

async def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Nicht schreiben/committen")
    parser.add_argument("--no-push", action="store_true", help="Nicht pushen (lokal testen)")
    args = parser.parse_args(argv)

    print(f"[agent] start {dt.datetime.now().isoformat()}")

    guard = BudgetGuard()
    if guard.is_exhausted():
        print("[agent] Tagesbudget aufgebraucht — Abbruch")
        return 0

    # 1. Task wählen
    task = select_task()
    if task is None:
        print("[agent] Backlog leer — Report + Ende")
        if not args.dry_run:
            report = write_daily_report(None, "", "", False, "", 0.0, 0, False)
            git_commit(f"docs(daily): report {dt.date.today().isoformat()} (Backlog leer)")
            if not args.no_push:
                git_push_with_rebase()
            print(f"[agent] report: {report}")
        return 0

    print(f"[agent] task: {task.id} — {task.title} (Versuche bisher: {task.attempts_used})")

    # 2. Versuchs-Schleife
    client = OpenRouterClient()
    messages: list[dict[str, str]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt(task)},
    ]

    success = False
    escalated = False
    plan, changelog, test_log = "", "", ""
    attempts_this_run = 0

    for attempt in range(1, MAX_ATTEMPTS_PER_RUN + 1):
        attempts_this_run = attempt
        model: ModelChoice | str = ModelChoice.BUILD_PRIMARY
        if attempt == MAX_ATTEMPTS_PER_RUN:
            model = ESCALATION_MODEL  # letzter Versuch: großes Modell

        try:
            raw = await call_llm(client, guard, messages, model=model)
            if model == ESCALATION_MODEL:
                escalated = True
        except BudgetExceeded:
            if model == ESCALATION_MODEL:
                print("[agent] Budget reicht nicht für 405B — letzter Versuch mit 70B")
                try:
                    raw = await call_llm(client, guard, messages, model=ModelChoice.BUILD_PRIMARY)
                except BudgetExceeded as e:
                    print(f"[agent] budget exceeded: {e}")
                    break
            else:
                print("[agent] budget exceeded — Abbruch")
                break

        p, files, cl = parse_response(raw)
        plan = plan or p
        changelog = cl or changelog

        if not files:
            print(f"[agent] Versuch {attempt}: keine FILE-Blöcke gefunden")
            messages.append({"role": "assistant", "content": raw[-6_000:]})
            messages.append({
                "role": "user",
                "content": "Deine Antwort enthielt keine ===FILE:...===-Blöcke. "
                           "Antworte erneut, exakt im vorgegebenen Format.",
            })
            continue

        changed = apply_files(files, task, dry_run=args.dry_run)
        if args.dry_run:
            print(f"[agent] dry-run — Plan: {plan[:200]}")
            return 0
        if not changed:
            print(f"[agent] Versuch {attempt}: keine erlaubte Datei geschrieben")
            messages.append({"role": "assistant", "content": raw[-6_000:]})
            messages.append({
                "role": "user",
                "content": f"Du hast keine der erlaubten target_files geschrieben. "
                           f"Erlaubt sind NUR: {', '.join(task.target_files)}. Erneut.",
            })
            continue

        ok, test_log = run_task_test(task)
        print(f"[agent] Versuch {attempt}: Test {'GRÜN' if ok else 'rot'}")
        if ok:
            success = True
            break

        if attempt < MAX_ATTEMPTS_PER_RUN:
            messages.append({"role": "assistant", "content": raw[-6_000:]})
            messages.append({"role": "user", "content": build_repair_prompt(task, test_log)})

    # 3. Abschluss
    state = guard.state()

    if success:
        # Task-Datei nach done/ verschieben
        TASKS_DONE.mkdir(parents=True, exist_ok=True)
        update_task_frontmatter(
            task,
            attempts_used=task.attempts_used + attempts_this_run,
            completed_at=dt.date.today().isoformat(),
        )
        task.path.rename(TASKS_DONE / task.path.name)

        report = write_daily_report(
            task, plan, changelog, True, test_log, state.spent_usd, attempts_this_run, escalated
        )
        print(f"[agent] report: {report}")
        msg = (
            f"feat({task.id}): {task.title}\n\n"
            f"{plan}\n\n"
            f"Roadmap: {task.roadmap_item}\n"
            f"Co-Authored-By: PflegeOS Agent <agent@pflegeos.de>"
        )
        if git_commit(msg) and not args.no_push:
            git_push_with_rebase()
        print(f"[agent] done ✅ budget: ${state.spent_usd:.4f}/${state.limit_usd:.2f}")
        return 0

    # Fehlschlag: Code zurücksetzen, Task-Zähler erhöhen, ggf. blockieren
    print("[agent] alle Versuche rot — Dateien werden zurückgesetzt")
    git_revert_all()

    new_attempts = task.attempts_used + 1  # zählt Läufe, nicht Einzel-Versuche
    update_task_frontmatter(task, attempts_used=new_attempts)
    blocked = new_attempts >= task.max_attempts
    if blocked:
        TASKS_BLOCKED.mkdir(parents=True, exist_ok=True)
        task.path.rename(TASKS_BLOCKED / task.path.name)
        print(f"[agent] {task.id} → tasks/blocked/ (Hilfe nötig)")

    report = write_daily_report(
        task, plan, changelog, False, test_log, state.spent_usd, attempts_this_run, escalated
    )
    print(f"[agent] report: {report}")
    git_commit(
        f"docs(daily): report {dt.date.today().isoformat()} "
        f"({task.id} rot, Lauf {new_attempts}/{task.max_attempts}"
        f"{', blockiert' if blocked else ''})"
    )
    if not args.no_push:
        git_push_with_rebase()

    print(f"[agent] done ⛔ budget: ${state.spent_usd:.4f}/${state.limit_usd:.2f}")
    return 2


if __name__ == "__main__":
    sys.exit(asyncio.run(main(sys.argv[1:])))
