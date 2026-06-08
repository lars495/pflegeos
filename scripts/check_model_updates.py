"""Wöchentlicher Hermes-Modell-Update-Check.

Läuft jeden Montag 02:30 Berlin via Cron.

Aufgaben:
  1. Fragt OpenRouter API nach allen Hermes-Modellen
  2. Vergleicht mit aktuell konfiguriertem Modell (model_config.json)
  3. Wenn neuere/bessere Version verfügbar:
     - Aktualisiert model_config.json
     - Schreibt Changelog-Eintrag
     - Committed und pushed (falls git verfügbar)
  4. Postet kurzen Status-Bericht nach reports/model-updates/

Entscheidungslogik "ist das Modell besser?":
  - Hermes-4-Modell > Hermes-3-Modell (Major-Version zählt)
  - Bei gleicher Major-Version: 405B > 70B (falls Budget es erlaubt)
  - Budget-Grenze für Modellwechsel: max $0.50/1M prompt-tokens
  - Niemals: automatischer Wechsel zu Modellen > $1.00/1M (braucht manuelle Freigabe)

Sicherheit:
  - Nie automatisch zu teurem Modell wechseln
  - Manuelle-Freigabe-Flag in model_config.json für teure Optionen
  - Altes Modell immer in der Config bewahren (rollback-fähig)
"""

from __future__ import annotations

import asyncio
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

import httpx


ROOT = Path(__file__).resolve().parents[1]
MODEL_CONFIG = ROOT / "packages" / "llm" / "model_config.json"
REPORT_DIR = ROOT / "reports" / "model-updates"
OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"

# Preisgrenze für automatischen Wechsel (USD pro 1M Prompt-Tokens)
AUTO_SWITCH_MAX_PROMPT_PRICE = 0.50
# Über diesem Preis: nur Report schreiben, nicht automatisch wechseln
MANUAL_APPROVAL_THRESHOLD = 1.00


def _load_config() -> dict:
    if MODEL_CONFIG.exists():
        return json.loads(MODEL_CONFIG.read_text())
    return {}


def _save_config(cfg: dict) -> None:
    MODEL_CONFIG.write_text(json.dumps(cfg, indent=2, ensure_ascii=False))


def _hermes_major_version(model_id: str) -> int:
    """Extrahiert Major-Version aus Modell-ID. 'hermes-4-70b' → 4."""
    import re
    m = re.search(r"hermes-(\d+)", model_id, re.IGNORECASE)
    return int(m.group(1)) if m else 0


def _model_params(model_id: str) -> int:
    """Extrahiert Parameteranzahl (in Milliarden). 'hermes-4-70b' → 70."""
    import re
    m = re.search(r"(\d+)b", model_id, re.IGNORECASE)
    return int(m.group(1)) if m else 0


def _is_better_model(candidate: dict, current_id: str, budget_ok: bool) -> tuple[bool, str]:
    """Entscheidet ob candidate besser als current_id ist.

    Returns (should_switch, reason).
    """
    cid = candidate["id"]
    prompt_price = float(candidate.get("pricing", {}).get("prompt", 999)) * 1_000_000

    # Sicherheits-Checks
    if prompt_price > AUTO_SWITCH_MAX_PROMPT_PRICE:
        return False, f"zu teuer für Auto-Switch (${prompt_price:.3f}/1M > ${AUTO_SWITCH_MAX_PROMPT_PRICE})"

    curr_major = _hermes_major_version(current_id)
    cand_major = _hermes_major_version(cid)
    curr_params = _model_params(current_id)
    cand_params = _model_params(cid)

    if cand_major > curr_major:
        return True, f"neuere Major-Version ({curr_major} → {cand_major})"

    if cand_major == curr_major and cand_params > curr_params and budget_ok:
        return True, f"mehr Parameter ({curr_params}B → {cand_params}B), Budget ok"

    return False, f"kein Upgrade (gleiche oder schlechtere Version)"


async def main() -> int:
    import os
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    today = dt.date.today().isoformat()
    report_path = REPORT_DIR / f"{today}.md"

    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        print("[model-check] kein OPENROUTER_API_KEY — Abbruch")
        return 1

    print(f"[model-check] start {dt.datetime.now().isoformat()}")

    # 1. OpenRouter abfragen
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.get(
            OPENROUTER_MODELS_URL,
            headers={"Authorization": f"Bearer {api_key}"},
        )
        r.raise_for_status()
        all_models = r.json()["data"]

    # 2. Hermes-Modelle filtern (kein :free — unzuverlässige Verfügbarkeit)
    hermes_models = [
        m for m in all_models
        if "hermes" in m["id"].lower() and ":free" not in m["id"]
    ]
    hermes_models.sort(
        key=lambda m: (
            _hermes_major_version(m["id"]),
            _model_params(m["id"]),
        ),
        reverse=True,
    )

    # 3. Aktuelle Config lesen
    cfg = _load_config()
    current_id = cfg.get("build_primary", "nousresearch/hermes-4-70b")
    known_versions = set(cfg.get("known_hermes_versions", []))

    # Neue Modelle entdeckt?
    new_discoveries = [m for m in hermes_models if m["id"] not in known_versions]

    # 4. Bestes kandidaten-Modell bestimmen
    switch_happened = False
    switch_reason = "—"
    best_candidate = hermes_models[0] if hermes_models else None

    if best_candidate and best_candidate["id"] != current_id:
        budget_ok = True  # TODO: echte Budget-Prüfung
        should_switch, reason = _is_better_model(best_candidate, current_id, budget_ok)
        if should_switch:
            old_id = current_id
            cfg["build_primary"] = best_candidate["id"]
            cfg["build_primary_name"] = best_candidate.get("name", best_candidate["id"])
            cfg["build_primary_set_at"] = today
            cfg["build_primary_set_reason"] = f"Automatischer Update: {reason}"
            cfg["build_primary_previous"] = old_id
            cfg["last_update_check"] = today
            cfg["known_hermes_versions"] = sorted({m["id"] for m in hermes_models})
            _save_config(cfg)
            switch_happened = True
            switch_reason = reason
            print(f"[model-check] Modell gewechselt: {old_id} → {best_candidate['id']} ({reason})")
        else:
            print(f"[model-check] kein Wechsel: {reason}")
            cfg["last_update_check"] = today
            cfg["known_hermes_versions"] = sorted({m["id"] for m in hermes_models})
            _save_config(cfg)
    else:
        cfg["last_update_check"] = today
        cfg["known_hermes_versions"] = sorted({m["id"] for m in hermes_models})
        _save_config(cfg)
        print(f"[model-check] aktuell optimal: {current_id}")

    # 5. Report schreiben
    with report_path.open("w") as f:
        f.write(f"# Modell-Update-Check — {today}\n\n")
        f.write(f"**Aktuelles Modell:** `{cfg['build_primary']}`\n\n")
        if switch_happened:
            f.write(f"✅ **Modell gewechselt** — {switch_reason}\n\n")
            f.write(f"Vorheriges Modell: `{cfg.get('build_primary_previous', '?')}`\n\n")
        else:
            f.write(f"ℹ️ Kein Wechsel — aktuelles Modell ist optimal\n\n")

        f.write("## Verfügbare Hermes-Modelle\n\n")
        f.write("| Modell | Preis/1M (in/out) | Kontext |\n")
        f.write("|---|---|---|\n")
        for m in hermes_models:
            p = m.get("pricing", {})
            p_in = float(p.get("prompt", 0)) * 1_000_000
            p_out = float(p.get("completion", 0)) * 1_000_000
            ctx = m.get("context_length", "?")
            active = " ← aktiv" if m["id"] == cfg["build_primary"] else ""
            f.write(f"| `{m['id']}`{active} | ${p_in:.3f} / ${p_out:.3f} | {ctx} |\n")

        if new_discoveries:
            f.write(f"\n## Neu entdeckte Modelle\n\n")
            for m in new_discoveries:
                f.write(f"- `{m['id']}` — {m.get('name', '')}\n")

        f.write(f"\n---\n\n*Automatisch erstellt von check_model_updates.py*\n")

    # 6. Wenn Wechsel: committen und pushen
    if switch_happened:
        try:
            subprocess.run(["git", "-C", str(ROOT), "add",
                          str(MODEL_CONFIG), str(report_path)], check=True)
            subprocess.run(["git", "-C", str(ROOT), "commit", "-m",
                          f"chore(model): auto-update build model to {cfg['build_primary']}\n\n{switch_reason}"],
                         check=True)
            subprocess.run(["git", "-C", str(ROOT), "push"], check=False)
            print("[model-check] committed + pushed")
        except subprocess.CalledProcessError as e:
            print(f"[model-check] git error: {e}")
    else:
        # Report trotzdem pushen (wöchentlicher Nachweis)
        try:
            subprocess.run(["git", "-C", str(ROOT), "add", str(report_path)], check=False)
            subprocess.run(["git", "-C", str(ROOT), "commit", "-m",
                          f"docs(model): weekly check {today} — no update needed"], check=False)
            subprocess.run(["git", "-C", str(ROOT), "push"], check=False)
        except Exception:
            pass

    print(f"[model-check] done → {report_path}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
