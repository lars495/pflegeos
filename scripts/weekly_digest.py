"""Wöchentlicher Digest — LinkedIn-Entwurf aus den Tagesberichten.

Läuft freitags 07:00 Berlin (Cron), nach dem nächtlichen Agenten-Lauf.
Sammelt die Daily Reports der letzten 7 Tage und verdichtet sie zu einem
LinkedIn-Entwurf, den der Betreiber kopiert, glättet und postet.

Der Entwurf wird von Hermes geschrieben — die KI fasst ihre eigene Woche
zusammen. Fällt der LLM-Call aus (kein Key, Budget, Fehler), entsteht
ein nüchterner Template-Digest. Beides landet in reports/weekly/.

Verwendung:
  python3 scripts/weekly_digest.py            # voller Lauf + git push
  python3 scripts/weekly_digest.py --no-llm   # nur Template (Test)
  python3 scripts/weekly_digest.py --no-push  # nicht committen/pushen
"""

from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import re
import subprocess
import sys
from pathlib import Path

WOCHENTAGE = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DAILY = ROOT / "reports" / "daily"
WEEKLY = ROOT / "reports" / "weekly"


# ────────────────────────────────────────────────────────────────────
# Tagesberichte einsammeln
# ────────────────────────────────────────────────────────────────────

def collect_week(end: dt.date) -> list[dict]:
    """Liest die Reports der letzten 7 Tage (end-6 … end)."""
    days = []
    for i in range(6, -1, -1):
        day = end - dt.timedelta(days=i)
        p = DAILY / f"{day.isoformat()}.md"
        if not p.exists():
            continue
        md = p.read_text()

        title = "Tagesbericht"
        for line in md.splitlines():
            if line.startswith("## "):
                title = line.lstrip("# ").strip()
                break

        cost = 0.0
        m = re.search(r"\| LLM-Kosten \| \$([\d.]+)", md)
        if m:
            cost = float(m.group(1))

        status = "✅" if "✅" in md else ("⛔" if "⛔" in md else "·")
        days.append({"date": day, "title": title, "status": status, "cost": cost, "md": md})
    return days


def summarize(days: list[dict]) -> dict:
    total_cost = sum(d["cost"] for d in days)
    ok = [d for d in days if d["status"] == "✅"]
    fail = [d for d in days if d["status"] == "⛔"]
    return {
        "total_cost": total_cost,
        "n_days": len(days),
        "n_ok": len(ok),
        "n_fail": len(fail),
    }


# ────────────────────────────────────────────────────────────────────
# LinkedIn-Entwurf
# ────────────────────────────────────────────────────────────────────

def _week_table(days: list[dict]) -> str:
    rows = ["| Tag | Status | Aufgabe | Kosten |", "|---|---|---|---|"]
    for d in days:
        rows.append(
            f"| {WOCHENTAGE[d['date'].weekday()]} {d['date'].strftime('%d.%m.')} | {d['status']} | {d['title']} | ${d['cost']:.4f} |"
        )
    return "\n".join(rows)


def template_draft(days: list[dict], stats: dict, end: dt.date) -> str:
    """Nüchterner Fallback ohne LLM."""
    day_n = (end - dt.date(2026, 5, 26)).days + 1
    lines = [
        f"Woche im PflegeOS-Experiment (Tag {day_n - 6}–{day_n}) 🤖",
        "",
        f"Die KI hat diese Woche an {stats['n_days']} Tagen gearbeitet: "
        f"{stats['n_ok']}× erfolgreich, {stats['n_fail']}× gescheitert.",
        "",
    ]
    for d in days:
        lines.append(f"• {WOCHENTAGE[d['date'].weekday()]}: {d['status']} {d['title']}")
    lines += [
        "",
        f"Gesamtkosten der Woche: {stats['total_cost']:.2f} $ (Budget wäre 7,70 $ gewesen).",
        "",
        "Das Experiment: Eine KI mit offenen Modellen baut täglich an einer",
        "personenzentrierten Pflegesoftware — max. 1 €/Tag, alles Open Source,",
        "jeder Fehlschlag öffentlich.",
        "",
        "👉 github.com/lars495/pflegeos",
        "",
        "#Pflege #KI #OpenSource #PflegeOS",
    ]
    return "\n".join(lines)


LLM_SYSTEM = """Du schreibst den wöchentlichen LinkedIn-Post für das PflegeOS-Experiment —
aus der Ich-Perspektive des menschlichen Betreibers (Pflegewissenschaftler), NICHT der KI.

Das Experiment: Eine KI (Hermes 4, offene Gewichte) baut täglich an einer
personenzentrierten Pflegesoftware. Max. 1 €/Tag, alles Open Source, jeder
Fehlschlag öffentlich. Kernbotschaft des Projekts: 'So würde man ein echtes
Produkt NICHT bauen — aber man lernt enorm viel dabei.'

Stil-Regeln:
- Deutsch, LinkedIn-tauglich: 800–1400 Zeichen, kurze Absätze, max. 2 Emojis
- Beginne mit der stärksten Geschichte der Woche (ein Scheitern ist oft die
  beste Geschichte), nicht mit einer Aufzählung
- Konkrete Zahlen nennen (Kosten! Der Kontrast winziger Beträge ist die Pointe)
- Ehrlich, selbstironisch erlaubt, kein Marketing-Sprech, keine Superlative
- Ende: Verweis auf github.com/lars495/pflegeos + 3-4 Hashtags
- Gib NUR den Post-Text aus, sonst nichts."""


async def llm_draft(days: list[dict], stats: dict, end: dt.date) -> str | None:
    try:
        from packages.llm.budget_guard import BudgetExceeded, BudgetGuard
        from packages.llm.openrouter_client import ModelChoice, OpenRouterClient
    except Exception as e:
        print(f"[digest] LLM-Module nicht ladbar: {e}")
        return None

    day_n = (end - dt.date(2026, 5, 26)).days + 1
    context = [f"Experiment-Tage {day_n - 6} bis {day_n}. Die Tagesberichte:\n"]
    for d in days:
        excerpt = d["md"][:2_500]
        context.append(f"\n--- {d['date'].isoformat()} ---\n{excerpt}\n")
    context.append(
        f"\nWochen-Zahlen: {stats['n_ok']} Erfolge, {stats['n_fail']} Fehlschläge, "
        f"Gesamtkosten ${stats['total_cost']:.2f} von möglichen $7.70.\n"
        "Schreibe jetzt den LinkedIn-Post."
    )

    guard = BudgetGuard()
    client = OpenRouterClient()
    est = OpenRouterClient.estimate_cost(ModelChoice.BUILD_PRIMARY, 8_000, 800)
    try:
        guard.reserve(est)
    except BudgetExceeded:
        print("[digest] Budget erschöpft — Template-Fallback")
        return None

    try:
        resp = await client.chat(
            messages=[
                {"role": "system", "content": LLM_SYSTEM},
                {"role": "user", "content": "".join(context)},
            ],
            model=ModelChoice.BUILD_PRIMARY,
            max_tokens=800,
            temperature=0.7,
        )
        guard.commit(resp.cost_usd or est)
        text = resp.text.strip()
        print(f"[digest] LLM-Entwurf ok (${resp.cost_usd:.4f})")
        return text if len(text) > 200 else None
    except Exception as e:
        print(f"[digest] LLM-Fehler: {e} — Template-Fallback")
        return None


# ────────────────────────────────────────────────────────────────────
# Git
# ────────────────────────────────────────────────────────────────────

def git_commit_push(path: Path, week: str) -> None:
    subprocess.run(["git", "-C", str(ROOT), "add", str(path)], check=False)
    subprocess.run(
        ["git", "-C", str(ROOT), "commit", "-m", f"docs(weekly): digest {week}"],
        check=False,
    )
    p = subprocess.run(["git", "-C", str(ROOT), "push"], capture_output=True, text=True)
    if p.returncode != 0:
        subprocess.run(["git", "-C", str(ROOT), "pull", "--rebase", "origin", "main"], check=False)
        subprocess.run(["git", "-C", str(ROOT), "push"], check=False)


# ────────────────────────────────────────────────────────────────────
# Main
# ────────────────────────────────────────────────────────────────────

async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=dt.date.today().isoformat())
    ap.add_argument("--no-llm", action="store_true")
    ap.add_argument("--no-push", action="store_true")
    args = ap.parse_args()

    end = dt.date.fromisoformat(args.date)
    days = collect_week(end)
    if not days:
        print("[digest] keine Tagesberichte in den letzten 7 Tagen — nichts zu tun")
        return 0

    stats = summarize(days)
    draft = None
    if not args.no_llm:
        draft = await llm_draft(days, stats, end)
    if draft is None:
        draft = template_draft(days, stats, end)
        source = "Template"
    else:
        source = "Hermes"

    year, week, _ = end.isocalendar()
    week_id = f"{year}-W{week:02d}"
    WEEKLY.mkdir(parents=True, exist_ok=True)
    out = WEEKLY / f"{week_id}.md"
    out.write_text(f"""# Wochen-Digest {week_id} ({days[0]['date'].isoformat()} – {end.isoformat()})

## LinkedIn-Entwurf (zum Kopieren und Glätten)

> Entwurf von: {source}. Bitte vor dem Posten in eigener Stimme prüfen.

```
{draft}
```

## Rohdaten der Woche

{_week_table(days)}

**Summe:** {stats['n_ok']}× ✅ · {stats['n_fail']}× ⛔ · Kosten ${stats['total_cost']:.4f}

---

*Automatisch erstellt von weekly_digest.py — freitags 07:00.*
""")
    print(f"[digest] geschrieben: {out}")

    if not args.no_push:
        git_commit_push(out, week_id)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
