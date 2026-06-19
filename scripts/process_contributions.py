"""Verarbeitet Community-Beiträge.

Zwei Quellen:
  1. GitHub Issues mit [Community]-Prefix (submitted über pflegeos.vercel.app)
  2. contributions/inbox/ JSON-Dateien (direkte API-Einreichungen, Fallback)

Ablauf für GitHub Issues:
  - Holt offene Issues mit [Community] im Titel, die noch nicht 'hermes:reviewed' haben
  - Lässt Hermes klassifizieren (idea/bug/legal → accept/decline/discuss)
  - Postet Hermes-Antwort als Kommentar auf dem Issue
  - Setzt Labels: hermes:reviewed + hermes:accepted / hermes:declined / hermes:needs-discussion

Lars ist NICHT in the loop. Hermes antwortet direkt.
"""

from __future__ import annotations

import asyncio
import datetime as dt
import json
import os
import shutil
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from packages.llm.budget_guard import BudgetExceeded, BudgetGuard  # noqa: E402
from packages.llm.openrouter_client import ModelChoice, OpenRouterClient  # noqa: E402

INBOX     = ROOT / "contributions" / "inbox"
PROCESSED = ROOT / "contributions" / "processed"
PUBLIC_LOG = ROOT / "contributions" / "public_log.md"

GITHUB_REPO = "lars495/pflegeos"
GITHUB_API  = "https://api.github.com"

# Labels die wir verwenden — werden automatisch erstellt wenn sie fehlen
GITHUB_LABELS = {
    "community-feedback":       {"color": "0075ca", "description": "Community-Einreichung über Website"},
    "type:idea":                {"color": "d4c5f9", "description": "Idee / Feature-Wunsch"},
    "type:legal":               {"color": "e4e669", "description": "Gesetz oder Verordnung"},
    "type:bug":                 {"color": "d73a4a", "description": "Bug / Problem"},
    "hermes:reviewed":          {"color": "0e8a16", "description": "Von Hermes geprüft"},
    "hermes:accepted":          {"color": "0e8a16", "description": "Von Hermes angenommen → in Arbeit"},
    "hermes:needs-discussion":  {"color": "fbca04", "description": "Hermes empfiehlt Team-Diskussion"},
    "hermes:declined":          {"color": "b60205", "description": "Von Hermes abgelehnt (mit Begründung)"},
}


# ────────────────────────────────────────────────────────────────────────────
# GitHub Hilfsfunktionen
# ────────────────────────────────────────────────────────────────────────────

def _gh_headers(token: str) -> dict:
    return {
        "Authorization":          f"Bearer {token}",
        "Accept":                 "application/vnd.github+json",
        "X-GitHub-Api-Version":   "2022-11-28",
        "User-Agent":             "PflegeOS-Hermes/1.0",
    }


async def _ensure_labels(client: httpx.AsyncClient, token: str) -> None:
    """Erstellt fehlende GitHub-Labels (idempotent)."""
    r = await client.get(
        f"{GITHUB_API}/repos/{GITHUB_REPO}/labels",
        headers=_gh_headers(token),
        params={"per_page": 100},
    )
    existing = {lbl["name"] for lbl in (r.json() if r.is_success else [])}

    for name, meta in GITHUB_LABELS.items():
        if name in existing:
            continue
        await client.post(
            f"{GITHUB_API}/repos/{GITHUB_REPO}/labels",
            headers=_gh_headers(token),
            json={"name": name, **meta},
        )
        print(f"  [labels] '{name}' erstellt")


async def _fetch_pending_issues(client: httpx.AsyncClient, token: str) -> list[dict]:
    """Holt offene [Community]-Issues, die Hermes noch nicht beantwortet hat."""
    r = await client.get(
        f"{GITHUB_API}/repos/{GITHUB_REPO}/issues",
        headers=_gh_headers(token),
        params={"state": "open", "per_page": 50, "labels": "community-feedback"},
    )
    if not r.is_success:
        print(f"[contributions] GitHub fetch fehlgeschlagen: {r.status_code}")
        return []

    all_issues = r.json()
    pending = []
    for issue in all_issues:
        if "pull_request" in issue:
            continue  # PRs überspringen
        label_names = {lbl["name"] for lbl in issue.get("labels", [])}
        if "hermes:reviewed" in label_names:
            continue
        if not issue.get("title", "").startswith("[Community]"):
            continue
        pending.append(issue)

    return pending


async def _post_comment(client: httpx.AsyncClient, token: str, issue_number: int, body: str) -> bool:
    r = await client.post(
        f"{GITHUB_API}/repos/{GITHUB_REPO}/issues/{issue_number}/comments",
        headers=_gh_headers(token),
        json={"body": body},
    )
    return r.is_success


async def _add_labels(client: httpx.AsyncClient, token: str, issue_number: int, labels: list[str]) -> None:
    await client.post(
        f"{GITHUB_API}/repos/{GITHUB_REPO}/issues/{issue_number}/labels",
        headers=_gh_headers(token),
        json={"labels": labels},
    )


# ────────────────────────────────────────────────────────────────────────────
# Hermes-Klassifikation
# ────────────────────────────────────────────────────────────────────────────

def _classify_prompt(title: str, body: str, issue_type: str = "") -> str:
    return f"""Du bist Hermes, der KI-Assistent des PflegeOS-Projekts.

Eine Pflegekraft oder pflegeinteressierte Person hat über pflegeos.vercel.app folgendes eingereicht.
Die Person kennt sich mit Software aus, aber nicht mit Programmierung. Nimm ihr Feedback ernst.

TITEL: {title}
TYP: {issue_type or 'nicht angegeben'}
INHALT:
{body}

PflegeOS-Prinzipien (unveränderlich):
1. Personenzentrierung — Bewohner:innen sind Menschen mit Biografie, keine Fälle
2. Empowerment — Pflegekräfte sind Owner des Prozesses, KI dient ihnen
3. Offenheit — Jede Stimme zählt, auch Kritik

Antworte NUR als valides JSON:
{{
  "category": "feature|document|problem|spam|unclear",
  "pillar": "personenzentrierung|empowerment|offenheit|alle|none",
  "next_action": "accepted|needs-discussion|declined",
  "reject_reason": "nur falls declined: kurze, respektvolle Begründung auf Deutsch",
  "roadmap_note": "falls accepted: ein Satz wie dieser Beitrag in die Roadmap einfliesst",
  "response_de": "Deine Antwort, 3–5 Sätze Deutsch. Warm, direkt, kein Marketing-Sprech. Sag klar was passiert. Vermeide Fachbegriffe wie 'Issue', 'Commit', 'Feature'. Sprich die Person als Pflegekraft an."
}}

Entscheidungsregeln:
- 'accepted': Passt zu Prinzipien, konkret umsetzbar, kein DSGVO-Risiko
- 'needs-discussion': Gute Idee, aber Abwägungen nötig (Datenschutz, Scope, Ressourcen)
- 'declined': Widerspricht Prinzipien, Spam, oder grundsätzlich nicht machbar
- Kategorien: 'feature'=Wunsch/Idee, 'document'=Gesetz/Standard/Verordnung, 'problem'=Kritik/Fehler
- Bei Unsicherheit: needs-discussion bevorzugen
"""


async def _classify_with_hermes(
    llm: OpenRouterClient,
    guard: BudgetGuard,
    title: str,
    body: str,
    issue_type: str = "",
) -> dict:
    prompt = _classify_prompt(title, body, issue_type)
    est = OpenRouterClient.estimate_cost(ModelChoice.BUILD_PRIMARY, 2_000, 600)
    model = ModelChoice.BUILD_CHEAP if guard.should_downshift() else ModelChoice.BUILD_PRIMARY

    try:
        guard.reserve(est)
    except BudgetExceeded:
        return {
            "next_action": "needs-discussion",
            "response_de": (
                "Vielen Dank für deinen Beitrag! Das tägliche Budget ist heute erschöpft — "
                "dein Beitrag wird morgen von Hermes geprüft."
            ),
        }

    resp = await llm.chat(
        messages=[
            {"role": "system", "content": "Antworte ausschließlich als valides JSON ohne Markdown-Code-Blöcke."},
            {"role": "user", "content": prompt},
        ],
        model=model,
        max_tokens=600,
        temperature=0.0,
    )
    guard.commit(resp.cost_usd or est)

    text = resp.text.strip()
    # JSON aus Antwort extrahieren (falls Modell trotzdem Markdown einfügt)
    if "```" in text:
        start = text.find("{")
        end   = text.rfind("}") + 1
        text  = text[start:end]

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end   = text.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(text[start:end])
        return {"next_action": "needs-discussion", "response_de": text}


# ────────────────────────────────────────────────────────────────────────────
# Hilfsfunktionen für public_log.md
# ────────────────────────────────────────────────────────────────────────────

def _append_public_log(summary: str, status: str, credit_name: str | None = None, reject_reason: str | None = None) -> None:
    today = dt.date.today().isoformat()
    line = f"- **{today}** — *{summary}* — Status: `{status}`"
    if credit_name:
        line += f" — Danke an {credit_name}"
    if reject_reason:
        line += f"\n  - Begründung: {reject_reason}"
    line += "\n"

    PUBLIC_LOG.parent.mkdir(parents=True, exist_ok=True)
    if not PUBLIC_LOG.exists():
        PUBLIC_LOG.write_text("# Community Contributions — Public Log\n\n")
    with PUBLIC_LOG.open("a") as f:
        f.write(line)


# ────────────────────────────────────────────────────────────────────────────
# GitHub Issues verarbeiten
# ────────────────────────────────────────────────────────────────────────────

async def _process_github_issues(token: str, llm: OpenRouterClient, guard: BudgetGuard) -> int:
    processed = 0
    async with httpx.AsyncClient(timeout=30.0) as gh:
        await _ensure_labels(gh, token)
        issues = await _fetch_pending_issues(gh, token)

        if not issues:
            print("[contributions] Keine neuen GitHub Issues")
            return 0

        print(f"[contributions] {len(issues)} neue GitHub Issue(s) gefunden")

        for issue in issues:
            number = issue["number"]
            title  = issue["title"].removeprefix("[Community]").strip()
            body   = issue.get("body", "")

            # Typ aus Labels ableiten
            label_names = {lbl["name"] for lbl in issue.get("labels", [])}
            issue_type = ""
            if "type:idea"  in label_names: issue_type = "idea"
            elif "type:legal" in label_names: issue_type = "legal"
            elif "type:bug"   in label_names: issue_type = "bug"

            print(f"  → Issue #{number}: {title[:60]}")

            verdict = await _classify_with_hermes(llm, guard, title, body, issue_type)
            action  = verdict.get("next_action", "needs-discussion")

            # Kommentar formulieren
            action_icon = {
                "accepted":         "✅",
                "needs-discussion": "💬",
                "declined":         "❌",
            }.get(action, "🔍")

            comment = f"**Hermes hat deinen Beitrag geprüft** {action_icon}\n\n"
            comment += verdict.get("response_de", "Danke für deinen Beitrag!")

            if action == "accepted" and verdict.get("roadmap_note"):
                comment += f"\n\n**Roadmap-Notiz:** {verdict['roadmap_note']}"

            comment += "\n\n---\n*Diese Antwort wurde automatisch von Hermes generiert.*"

            ok = await _post_comment(gh, token, number, comment)
            if ok:
                print(f"    ✓ Kommentar gepostet")
            else:
                print(f"    ⚠️ Kommentar-Post fehlgeschlagen")

            # Labels setzen
            new_labels = ["hermes:reviewed", f"hermes:{action}"]
            await _add_labels(gh, token, number, new_labels)

            # Public Log
            _append_public_log(
                summary=title[:120],
                status=action,
                reject_reason=verdict.get("reject_reason"),
            )

            processed += 1

    return processed


# ────────────────────────────────────────────────────────────────────────────
# Inbox-JSON-Dateien verarbeiten (Fallback / Altbestand)
# ────────────────────────────────────────────────────────────────────────────

async def _process_inbox(llm: OpenRouterClient, guard: BudgetGuard) -> int:
    INBOX.mkdir(parents=True, exist_ok=True)
    PROCESSED.mkdir(parents=True, exist_ok=True)

    files = sorted(INBOX.glob("*.json"))
    if not files:
        return 0

    print(f"[contributions] {len(files)} Inbox-Datei(en)")

    for path in files:
        try:
            payload = json.loads(path.read_text())
        except json.JSONDecodeError:
            print(f"  ⚠️ {path.name}: ungültiges JSON — überspringe")
            continue

        title = payload.get("title", "")
        body  = payload.get("body", "")

        verdict = await _classify_with_hermes(llm, guard, title, body, payload.get("type", ""))
        action  = verdict.get("next_action", "needs-discussion")

        result_path = PROCESSED / path.name
        result_path.write_text(json.dumps(
            {"original": payload, "verdict": verdict, "processed_at": dt.datetime.utcnow().isoformat() + "Z"},
            ensure_ascii=False,
            indent=2,
        ))

        _append_public_log(
            summary=verdict.get("summary_de", title)[:120],
            status=action,
            credit_name=payload.get("submitter_name") if payload.get("consent_to_credit") else None,
            reject_reason=verdict.get("reject_reason") if action == "declined" else None,
        )

        path.unlink()
        print(f"  ✓ {path.name} → {action}")

    return len(files)


# ────────────────────────────────────────────────────────────────────────────
# Einstiegspunkt
# ────────────────────────────────────────────────────────────────────────────

async def main() -> int:
    llm   = OpenRouterClient()
    guard = BudgetGuard()
    total = 0

    # 1. GitHub Issues (Haupt-Kanal)
    token = os.environ.get("GITHUB_FEEDBACK_TOKEN", "")
    if token:
        total += await _process_github_issues(token, llm, guard)
    else:
        print("[contributions] GITHUB_FEEDBACK_TOKEN nicht gesetzt — GitHub-Issues übersprungen")

    # 2. Inbox-JSON-Dateien (Fallback)
    total += await _process_inbox(llm, guard)

    print(f"[contributions] {total} Beitrag/Beiträge verarbeitet")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
