"""Wöchentlicher Modell-Check (Montags 02:30 Berlin).

Prüft für jede Rolle in model_config.json, ob das eingetragene Modell bei
OpenRouter noch angeboten wird. Fehlt es, wird auf das erste verfügbare
Modell der Fallback-Kette umgestellt und das im Bericht vermerkt.

Hintergrund (L10): Bis Oktober 2026 suchte dieser Check nur nach *neueren*
Hermes-Versionen. Dass das aktive Modell eingestellt worden war, meldete er
wochenlang als "no update needed".

Der Check schlägt keine besseren Modelle automatisch vor — ein Modellwechsel
aus Qualitätsgründen ist eine bewusste Entscheidung und kein Cron-Job.
"""

from __future__ import annotations

import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
MODEL_CONFIG = ROOT / "packages" / "llm" / "model_config.json"
REPORT_DIR = ROOT / "reports" / "model-updates"


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True)


def _push_with_rebase() -> None:
    if _git("push").returncode == 0:
        return
    if _git("pull", "--rebase", "origin", "main").returncode != 0:
        _git("rebase", "--abort")
        print("[model-check] rebase fehlgeschlagen — Commit bleibt lokal")
        return
    _git("push")


def main() -> int:
    today = dt.date.today().isoformat()
    cfg = json.loads(MODEL_CONFIG.read_text())
    roles: dict[str, str] = cfg["roles"]
    fallbacks: dict[str, list[str]] = cfg.get("fallbacks", {})

    r = httpx.get("https://openrouter.ai/api/v1/models", timeout=30.0)
    r.raise_for_status()
    available = {m["id"]: m for m in r.json()["data"]}

    lines: list[str] = []
    changed = []
    for role, model in roles.items():
        if model in available:
            p = available[model].get("pricing", {})
            lines.append(
                f"| {role} | `{model}` | ✅ | "
                f"{float(p.get('prompt', 0)) * 1e6:.2f} / {float(p.get('completion', 0)) * 1e6:.2f} $ |"
            )
            continue
        replacement = next((m for m in fallbacks.get(role, []) if m in available), None)
        if replacement:
            roles[role] = replacement
            changed.append(f"{role}: `{model}` eingestellt → `{replacement}`")
            lines.append(f"| {role} | `{replacement}` | 🔁 ersetzt `{model}` | |")
        else:
            changed.append(f"{role}: `{model}` eingestellt, KEIN Fallback verfügbar")
            lines.append(f"| {role} | `{model}` | ⛔ nicht verfügbar | |")

    if changed:
        cfg["roles"] = roles
        cfg["set_at"] = today
        MODEL_CONFIG.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n")

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report = REPORT_DIR / f"{today}.md"
    status = "⚠️ Änderungen nötig gewesen" if changed else "✅ alle Modelle verfügbar"
    report.write_text(
        f"# Modell-Check — {today}\n\n**{status}**\n\n"
        + ("".join(f"- {c}\n" for c in changed) + "\n" if changed else "")
        + "| Rolle | Modell | Status | Preis/1M (in/out) |\n|---|---|---|---|\n"
        + "\n".join(lines)
        + "\n\n*Automatisch erstellt von check_model_updates.py*\n"
    )
    print(f"[model-check] {status}")
    for c in changed:
        print(f"[model-check] {c}")

    _git("add", str(report), str(MODEL_CONFIG))
    msg = f"chore(model): {len(changed)} Modell(e) ersetzt" if changed else f"docs(model): weekly check {today} — alle verfügbar"
    _git("commit", "-m", msg)
    _push_with_rebase()
    # Exit 1 bei Rolle ohne Fallback → taucht im Log auf
    return 1 if any("KEIN Fallback" in c for c in changed) else 0


if __name__ == "__main__":
    sys.exit(main())
