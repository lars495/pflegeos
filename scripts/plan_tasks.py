"""Task-Planer: holt sich selbst sinnvolle neue Tasks, wenn der Backlog leer ist.

Läuft im täglichen Ablauf VOR dem Build-Agenten (daily_agent.sh).

Ablauf:
  1. tasks/open/ nicht leer → nichts zu tun
  2. Beste Idee aus ideas/inbox/ wählen (höchster Score; Quellen: monatliche
     Recherche und angenommene Community-Beiträge)
  3. Ein starkes Modell (Rolle PLANNING) zerlegt sie in 2–4 Tasks MIT fertigen
     Tests — im Format von tasks/README.md, mit dem echten Code als Kontext
  4. Harte, deterministische Prüfungen (Gates), bevor irgendetwas übernommen wird:
       - nur erlaubte Pfade, fortlaufende IDs, gültiges Frontmatter
       - target_files nur unter apps/api/, keine geschützten Dateien, max. 3
       - jede Task hat ihren eigenen Test, Tests kompilieren
       - Gesamtsuite bleibt grün (neue Tests müssen sich vor dem Bau überspringen)
       - kein neuer Test ist schon vor dem Bau grün (sonst prüft er nichts)
  5. Gates rot → eine Reparaturrunde mit den Fehlern; danach Verwerfen und die
     Idee wird zurückgestellt (planungsversuche++), nie halbfertig übernommen
  6. Grün → Idee nach ideas/accepted/, Commit

Warum nicht einfach blind generieren: L4/L9/L11 — die Fehler entstehen beim
Zuschnitt. Die Gates sind die Stelle, an der ein Mensch sonst hinschauen würde.

Verwendung:
  python3 scripts/plan_tasks.py            # voller Lauf (nur wenn Backlog leer)
  python3 scripts/plan_tasks.py --dry-run  # plant und prüft, übernimmt nichts
"""

from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import re
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from packages.llm.budget_guard import BudgetExceeded, BudgetGuard  # noqa: E402
from packages.llm.openrouter_client import ModelChoice, OpenRouterClient  # noqa: E402
from scripts.build_agent import PROTECTED_PATHS, _wrap_for_container, parse_task  # noqa: E402

TASKS = ROOT / "tasks"
OPEN, DONE, BLOCKED = TASKS / "open", TASKS / "done", TASKS / "blocked"
IDEAS_INBOX, IDEAS_ACCEPTED = ROOT / "ideas" / "inbox", ROOT / "ideas" / "accepted"
TESTS = ROOT / "tests" / "task_tests"
MAX_PLANUNGSVERSUCHE = 2

SYSTEM = """Du zerlegst eine Idee für PflegeOS in kleine, präzise Arbeitspakete (Tasks)
für ein günstiges Programmiermodell. Du schreibst NICHT die Implementierung —
du schreibst Task-Beschreibungen und die fertigen Tests, die die Spezifikation SIND.

Halte dich exakt an tasks/README.md (unten). Wichtigste Regeln:
- 2 bis 4 Tasks. Jede Task ändert max. 3 Dateien (target_files).
- Neue Daten nur in NEUEN Modell-Dateien/Tabellen (keine Migrationen bestehender Tabellen).
- Oberfläche: eine Datei pro Bereich unter apps/api/ui/. Neuer Bereich = neue Datei
  + Eintrag in BEREICHE in apps/api/web.py (dann web.py als target_file).
  Jede Datei, die die Task ändern oder einbinden muss, steht in target_files (L9).
- Jeder Test überspringt sich, solange die Task nicht gebaut ist
  (pytest.importorskip bzw. Prüfung auf die Route, wie in den Beispielen).
- Tests prüfen auch die Prinzipien (Person zuerst, Pflegekraft entscheidet,
  Privatsphäre), nicht nur die Technik. Fixtures: `client`, `db_session`.
- Gib Signaturen, Feldnamen, Routen und Template-Namen exakt vor.
- Keine Auth-, Krypto- oder Migrations-Tasks. Kein JavaScript außer HTMX-Attributen.

ANTWORTFORMAT, exakt:
===FILE: tasks/open/T0NN-kurzer-slug.md===
<komplette Task-Datei mit YAML-Frontmatter>
===END===
===FILE: tests/task_tests/test_t0NN_kurzer_slug.py===
<kompletter Test>
===END===
(für jede Task beide Dateien; IDs fortlaufend ab der vorgegebenen Start-ID;
depends_on darf auf erledigte Tasks und auf die eigenen neuen verweisen)"""

FILE_RE = re.compile(r"===FILE:\s*(.+?)\s*===\n(.*?)\n===END===", re.S)


# ─── Auswahl ────────────────────────────────────────────────────────

def _fm(path: Path) -> tuple[dict, str]:
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", path.read_text(), re.S)
    return (yaml.safe_load(m.group(1)) or {}, m.group(2)) if m else ({}, path.read_text())


def waehle_idee() -> Path | None:
    kandidaten = []
    for p in sorted(IDEAS_INBOX.glob("*.md")):
        fm, _ = _fm(p)
        if int(fm.get("planungsversuche", 0)) >= MAX_PLANUNGSVERSUCHE:
            continue
        kandidaten.append((int(fm.get("score", 0)), p))
    return max(kandidaten)[1] if kandidaten else None


def naechste_id() -> int:
    ids = [int(m.group(1)) for d in (OPEN, DONE, BLOCKED) if d.exists()
           for p in d.glob("T*.md") if (m := re.match(r"T(\d+)", p.name))]
    return max(ids, default=0) + 1


# ─── Kontext ────────────────────────────────────────────────────────

def _datei(rel: str, limit: int = 6000) -> str:
    p = ROOT / rel
    return f"\n## {rel}\n```\n{p.read_text()[:limit]}\n```\n" if p.exists() else ""


def kontext(idee: Path, start_id: int) -> str:
    teile = [f"# Die Idee\n\n{idee.read_text()}\n",
             f"\n# Start-ID für neue Tasks: T{start_id:03d}\n",
             "\n# Erledigte Tasks\n" + "\n".join(sorted(p.stem for p in DONE.glob("T*.md")))]
    teile.append("\n# Repo-Struktur (apps/api)\n" + "\n".join(
        str(p.relative_to(ROOT)) for p in sorted((ROOT / "apps/api").rglob("*"))
        if p.is_file() and "__pycache__" not in p.parts and p.suffix in (".py", ".html")))
    for rel in ("tasks/README.md", "apps/api/web.py", "apps/api/ui/common.py",
                "apps/api/ui/notizen.py", "apps/api/models/beobachtung.py",
                "apps/api/templates/_notizen.html", "apps/api/templates/bewohner_detail.html",
                "tests/conftest.py", "tests/test_routen_bestand.py"):
        teile.append(_datei(rel))
    # Ein vollständiges Beispiel-Paar aus Task + Test als Vorlage
    beispiel = sorted(DONE.glob("T032-*.md"))
    if beispiel:
        teile.append("\n# Beispiel einer guten Task (T032)\n" + _datei(str(beispiel[0].relative_to(ROOT)), 8000))
        teile.append(_datei("tests/task_tests/test_t032_ui_notiz_freigabe.py"))
    teile.append(_datei("PRINCIPLES.md", 4000))
    return "".join(teile)


# ─── Gates ──────────────────────────────────────────────────────────

def _pytest(args: str) -> tuple[int, str]:
    r = subprocess.run(_wrap_for_container(f"pytest -q {args}"), shell=True, cwd=ROOT,
                       capture_output=True, text=True, timeout=600)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def pruefe(files: dict[str, str], start_id: int) -> list[str]:
    fehler: list[str] = []
    tasks = {p: c for p, c in files.items() if p.startswith("tasks/open/")}
    tests = {p: c for p, c in files.items() if p.startswith("tests/task_tests/")}
    for p in files:
        if not (re.fullmatch(r"tasks/open/T\d{3}-[a-z0-9-]+\.md", p)
                or re.fullmatch(r"tests/task_tests/test_t\d{3}_[a-z0-9_]+\.py", p)):
            fehler.append(f"Unerlaubter Pfad: {p}")
    if not 2 <= len(tasks) <= 4:
        fehler.append(f"{len(tasks)} Tasks — erlaubt sind 2 bis 4")
    erwartet = {f"T{start_id + i:03d}" for i in range(len(tasks))}
    gefunden = set()
    for p, c in tasks.items():
        m = re.match(r"^---\n(.*?)\n---\n", c, re.S)
        if not m:
            fehler.append(f"{p}: kein Frontmatter")
            continue
        try:
            fm = yaml.safe_load(m.group(1))
        except yaml.YAMLError as e:
            fehler.append(f"{p}: YAML-Fehler {e}")
            continue
        tid = str(fm.get("id", ""))
        gefunden.add(tid)
        if not p.split("/")[-1].startswith(tid + "-"):
            fehler.append(f"{p}: Dateiname passt nicht zu id {tid}")
        targets = fm.get("target_files") or []
        if not 1 <= len(targets) <= 3:
            fehler.append(f"{tid}: {len(targets)} target_files (1–3 erlaubt)")
        for t in targets:
            if t in PROTECTED_PATHS or not t.startswith("apps/api/") or t in ("apps/api/main.py", "apps/api/db.py"):
                fehler.append(f"{tid}: target_file nicht erlaubt: {t}")
        cmd = str(fm.get("test_command", ""))
        test_pfad = cmd.replace("pytest -q", "").strip()
        if test_pfad not in tests:
            fehler.append(f"{tid}: test_command zeigt nicht auf eine mitgelieferte Testdatei ({cmd})")
        for c in fm.get("context_files") or []:
            if not (ROOT / c).exists() and c not in files and c not in targets:
                fehler.append(f"{tid}: context_file existiert nicht: {c}")
    if gefunden != erwartet:
        fehler.append(f"IDs {sorted(gefunden)} — erwartet fortlaufend {sorted(erwartet)}")
    for p, c in tests.items():
        try:
            compile(c, p, "exec")
        except SyntaxError as e:
            fehler.append(f"{p}: SyntaxError Zeile {e.lineno}: {e.msg}")
    return fehler


def pruefe_im_container(files: dict[str, str]) -> list[str]:
    """Schreibt die Dateien probeweise und prüft das Verhalten der Suite."""
    fehler = []
    code, out = _pytest("tests/")
    if code != 0:
        fehler.append("Gesamtsuite rot mit den neuen Tests (sie müssen sich vor dem Bau "
                      "überspringen):\n" + "\n".join(l for l in out.splitlines()
                                                    if l.startswith(("FAILED", "ERROR", "E ")))[-3000:])
    for p in (p for p in files if p.startswith("tests/")):
        _, out = _pytest(p)
        if re.search(r"\d+ passed", out):
            fehler.append(f"{p}: ist schon VOR dem Bau grün — der Test prüft nichts Neues")
    return fehler


# ─── LLM ────────────────────────────────────────────────────────────

async def plane(messages: list[dict]) -> tuple[str, float]:
    guard, client = BudgetGuard(), OpenRouterClient(timeout_s=300.0)
    est = OpenRouterClient.estimate_cost(ModelChoice.PLANNING, 40_000, 12_000)
    guard.reserve(est, pot="planning")
    resp = await client.chat(messages=messages, model=ModelChoice.PLANNING,
                             max_tokens=16_000, temperature=0.2)
    guard.commit(resp.cost_usd or est, pot="planning")
    return resp.text, resp.cost_usd or 0


def schreibe(files: dict[str, str]) -> None:
    for rel, c in files.items():
        p = ROOT / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(c if c.endswith("\n") else c + "\n")


def entferne(files: dict[str, str]) -> None:
    for rel in files:
        (ROOT / rel).unlink(missing_ok=True)


def git(*a: str) -> None:
    subprocess.run(["git", "-C", str(ROOT), *a], check=False)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    OPEN.mkdir(parents=True, exist_ok=True)
    if any(OPEN.glob("T*.md")):
        print("[plan] Backlog nicht leer — nichts zu planen")
        return 0
    idee = waehle_idee()
    if idee is None:
        print("[plan] Keine planbare Idee in ideas/inbox/ — wartet auf Recherche/Community")
        return 0

    start_id = naechste_id()
    print(f"[plan] Idee: {idee.name} → Tasks ab T{start_id:03d}")
    messages = [{"role": "system", "content": SYSTEM},
                {"role": "user", "content": kontext(idee, start_id)}]

    kosten, files, fehler = 0.0, {}, ["noch nicht geplant"]
    for runde in (1, 2):
        try:
            text, c = asyncio.run(plane(messages))
        except BudgetExceeded as e:
            print(f"[plan] Budget: {e}")
            return 0
        kosten += c
        files = {m.group(1).strip(): m.group(2) for m in FILE_RE.finditer(text)}
        fehler = pruefe(files, start_id)
        if not fehler:
            schreibe(files)
            fehler = pruefe_im_container(files)
            if fehler:
                entferne(files)
        print(f"[plan] Runde {runde}: {len(files)} Dateien, {len(fehler)} Fehler")
        if not fehler:
            break
        messages += [{"role": "assistant", "content": text[-20_000:]},
                     {"role": "user", "content": "Die Prüfung ist fehlgeschlagen. Behebe ALLE Punkte "
                      "und gib alle Dateien erneut vollständig aus:\n- " + "\n- ".join(fehler)}]

    fm, body = _fm(idee)
    if fehler:
        print("[plan] verworfen:\n  - " + "\n  - ".join(fehler))
        if not args.dry_run:
            fm["planungsversuche"] = int(fm.get("planungsversuche", 0)) + 1
            fm["letzter_planungsfehler"] = fehler[0][:300]
            idee.write_text("---\n" + yaml.safe_dump(fm, allow_unicode=True, sort_keys=False) + "---\n" + body)
            git("add", "-A", "--", "ideas/")
            git("commit", "-m", f"chore(plan): Planung für {idee.stem} verworfen (Kosten ${kosten:.3f})")
            git("push")
        return 0

    tids = sorted(p.split("/")[-1].split("-")[0] for p in files if p.startswith("tasks/"))
    print(f"[plan] ✅ {', '.join(tids)} geplant und geprüft (Kosten ${kosten:.3f})")
    if args.dry_run:
        entferne(files)
        return 0
    fm["status"] = f"angenommen — automatisch geplant als {tids[0]}–{tids[-1]} am {dt.date.today()}"
    IDEAS_ACCEPTED.mkdir(parents=True, exist_ok=True)
    ziel = IDEAS_ACCEPTED / idee.name
    ziel.write_text("---\n" + yaml.safe_dump(fm, allow_unicode=True, sort_keys=False) + "---\n" + body)
    idee.unlink()
    # gezielt nur diese drei Bereiche (Ideen können untracked aus dem Container kommen)
    git("add", "-A", "--", "ideas/", "tasks/open/", "tests/task_tests/")
    git("commit", "-m", f"feat(plan): {tids[0]}–{tids[-1]} automatisch aus Idee {idee.stem} geplant\n\n"
        f"Alle Gates grün. Kosten ${kosten:.3f}.\n\nCo-Authored-By: PflegeOS Planer <agent@pflegeos.de>")
    if subprocess.run(["git", "-C", str(ROOT), "push"], capture_output=True).returncode != 0:
        git("pull", "--rebase", "origin", "main")
        git("push")
    return 0


if __name__ == "__main__":
    sys.exit(main())
