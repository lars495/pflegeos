"""Verarbeitet Community-Einreichungen aus contributions/inbox/.

Eine Einreichung ist eine JSON-Datei mit folgendem Schema:
{
  "submitted_at": "2026-05-27T12:34:56Z",
  "submitter_name": "M. Schulze",          # optional
  "submitter_email": "...",                 # optional, intern
  "consent_to_credit": true,                # Namensnennung im CHANGELOG?
  "type": "idea|legal|bug",
  "title": "...",
  "body": "...",
  "attachments": ["url1", "url2"]
}

Nach Verarbeitung wird die Datei nach contributions/processed/ verschoben
und ein Eintrag in contributions/public_log.md ergänzt.
"""

from __future__ import annotations

import asyncio
import datetime as dt
import json
import shutil
import sys
from pathlib import Path

from packages.llm.budget_guard import BudgetExceeded, BudgetGuard
from packages.llm.openrouter_client import ModelChoice, OpenRouterClient


ROOT = Path(__file__).resolve().parents[1]
INBOX = ROOT / "contributions" / "inbox"
PROCESSED = ROOT / "contributions" / "processed"
PUBLIC_LOG = ROOT / "contributions" / "public_log.md"


def _classify_prompt(payload: dict) -> str:
    return f"""Klassifiziere die folgende Community-Einreichung für PflegeOS.

EINREICHUNG:
Titel: {payload.get("title", "")}
Typ (Selbsteinordnung): {payload.get("type", "idea")}
Inhalt:
{payload.get("body", "")}

Antworte als JSON:
{{
  "category": "feature|bug|legal|spam|abusive|unclear",
  "pillar": "personenzentrierung|empowerment|offenheit|none",
  "effort_estimate": "S|M|L|XL",
  "dsgvo_risk": "none|low|medium|high",
  "summary_de": "ein Satz für public_log.md",
  "response_de": "kurze respektvolle Antwort an Einsender (3-4 Sätze)",
  "next_action": "create_issue|reject|moderate|need_clarification",
  "reject_reason": "nur falls next_action=reject"
}}

Prinzipien:
- Bei Unsicherheit über DSGVO: dsgvo_risk = medium oder höher
- Beleidigend/Spam → category=abusive oder spam
- Wenn Idee gegen PRINCIPLES.md verstößt (z.B. GPS-Tracking) → reject mit Begründung
- Sprache der Antwort: deutsch, respektvoll, kein Marketing-Sprech
"""


async def _classify(client: OpenRouterClient, guard: BudgetGuard, payload: dict) -> dict:
    prompt = _classify_prompt(payload)
    est = OpenRouterClient.estimate_cost(ModelChoice.BUILD_PRIMARY, 2_000, 800)

    # Bei Budgetdruck auf billigeres Modell
    model = (
        ModelChoice.BUILD_CHEAP
        if guard.should_downshift()
        else ModelChoice.BUILD_PRIMARY
    )

    try:
        guard.reserve(est)
    except BudgetExceeded:
        # Notfall: heuristisch ablehnen statt blind verarbeiten
        return {
            "category": "unclear",
            "next_action": "moderate",
            "response_de": "Vielen Dank! Wegen Tagesbudget wird Ihre Einreichung manuell geprüft.",
            "summary_de": payload.get("title", "Manuelle Prüfung nötig"),
        }

    resp = await client.chat(
        messages=[
            {"role": "system", "content": "Antworte ausschließlich als valides JSON."},
            {"role": "user", "content": prompt},
        ],
        model=model,
        max_tokens=600,
        temperature=0.0,
    )
    guard.commit(resp.cost_usd or est)

    try:
        return json.loads(resp.text)
    except json.JSONDecodeError:
        start, end = resp.text.find("{"), resp.text.rfind("}")
        return json.loads(resp.text[start : end + 1])


def _append_public_log(entry: dict) -> None:
    today = dt.date.today().isoformat()
    line = (
        f"- **{today}** — *{entry['summary']}* — "
        f"Status: `{entry['status']}`"
    )
    if entry.get("credit_name"):
        line += f" — Danke an {entry['credit_name']}"
    if entry.get("reject_reason"):
        line += f"\n  - Begründung: {entry['reject_reason']}"
    line += "\n"

    PUBLIC_LOG.parent.mkdir(parents=True, exist_ok=True)
    if not PUBLIC_LOG.exists():
        PUBLIC_LOG.write_text("# Community Contributions — Public Log\n\n")
    with PUBLIC_LOG.open("a") as f:
        f.write(line)


async def main() -> int:
    INBOX.mkdir(parents=True, exist_ok=True)
    PROCESSED.mkdir(parents=True, exist_ok=True)

    files = sorted(INBOX.glob("*.json"))
    if not files:
        print("[contributions] inbox leer")
        return 0

    client = OpenRouterClient()
    guard = BudgetGuard()

    for path in files:
        print(f"[contributions] {path.name}")
        try:
            payload = json.loads(path.read_text())
        except json.JSONDecodeError:
            print(f"  ⚠️ JSON ungültig — überspringe")
            continue

        verdict = await _classify(client, guard, payload)
        status = verdict.get("next_action", "moderate")

        result_path = PROCESSED / path.name
        result_payload = {
            "original": payload,
            "verdict": verdict,
            "processed_at": dt.datetime.utcnow().isoformat() + "Z",
        }
        result_path.write_text(json.dumps(result_payload, ensure_ascii=False, indent=2))

        _append_public_log({
            "summary": verdict.get("summary_de", payload.get("title", "")),
            "status": status,
            "credit_name": payload.get("submitter_name")
                if payload.get("consent_to_credit") else None,
            "reject_reason": verdict.get("reject_reason") if status == "reject" else None,
        })

        path.unlink()  # aus Inbox entfernen

    print(f"[contributions] {len(files)} Einreichung(en) verarbeitet")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
