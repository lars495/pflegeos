"""Postet das Daily-Update zu Mastodon, LinkedIn und X.

Liest reports/daily/YYYY-MM-DD.md, generiert daraus eine Kurzfassung
(falls noch nicht vorhanden) und postet auf alle Kanäle, für die
ein Token gesetzt ist. Fehlende Tokens werden geräuschlos übersprungen.

Mastodon:    POST {MASTODON_BASE_URL}/api/v1/statuses (Token-Scope: write:statuses)
LinkedIn API: https://learn.microsoft.com/en-us/linkedin/marketing/integrations/community-management/shares/ugc-post-api
X API v2:    https://docs.x.com/x-api/posts/creation-of-a-post
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import sys
from pathlib import Path

import httpx


ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports" / "daily"


def _load_report(date: dt.date) -> str:
    p = REPORTS / f"{date.isoformat()}.md"
    if not p.exists():
        print(f"[post] kein Report unter {p}", file=sys.stderr)
        sys.exit(1)
    return p.read_text()


def _shorten_for_x(markdown: str, max_chars: int = 270) -> str:
    """Quick & dirty: nimm ersten Absatz, kappe auf max_chars."""
    paragraphs = [p.strip() for p in markdown.split("\n\n") if p.strip() and not p.startswith("#")]
    text = paragraphs[0] if paragraphs else markdown[:max_chars]
    if len(text) > max_chars:
        text = text[: max_chars - 1].rsplit(" ", 1)[0] + "…"
    return text + "\n\n#PflegeOS"


def _shorten_for_linkedin(markdown: str, max_chars: int = 2500) -> str:
    lines = []
    for line in markdown.splitlines():
        if line.startswith("# "):
            continue  # Header rauslassen
        lines.append(line)
    text = "\n".join(lines).strip()
    if len(text) > max_chars:
        text = text[: max_chars - 1].rsplit(" ", 1)[0] + "…"
    return text + "\n\n#Pflege #DSGVO #PflegeOS"


def _extract_title_and_status(markdown: str) -> tuple[str, str]:
    """Holt Task-Titel und Status-Icon aus dem Report."""
    title, icon = "Tagesbericht", ""
    for line in markdown.splitlines():
        if line.startswith("## "):
            title = line.lstrip("# ").strip()
            break
    if "✅" in markdown:
        icon = "✅"
    elif "⛔" in markdown:
        icon = "⛔"
    return title, icon


def _shorten_for_mastodon(markdown: str, date: dt.date, max_chars: int = 480) -> str:
    """Toot-Format: Titel + Kernaussage + Link, unter 500 Zeichen."""
    title, icon = _extract_title_and_status(markdown)
    day_n = (date - dt.date(2026, 5, 26)).days + 1

    # Kernaussage: bevorzugt die pflegekraftverständliche Zusammenfassung,
    # sonst der technische Plan
    core = ""
    lines = markdown.splitlines()
    for marker in ("### Für Pflegekräfte", "### Plan"):
        for i, line in enumerate(lines):
            if line.startswith(marker):
                rest = [x.strip() for x in lines[i + 1:] if x.strip() and not x.startswith("#")]
                if rest:
                    core = rest[0]
                break
        if core:
            break

    text = f"🤖 PflegeOS · Tag {day_n}\n\n{icon} {title}\n"
    if core:
        text += f"\n{core}\n"
    text += (
        "\nEine KI baut Pflegesoftware — max. 1 €/Tag, alles öffentlich."
        "\n\n📖 https://github.com/lars495/pflegeos"
        "\n\n#PflegeOS #Pflege #KI #OpenSource"
    )
    if len(text) > max_chars:
        text = text[: max_chars - 1] + "…"
    return text


def _post_mastodon(text: str) -> None:
    base = os.environ.get("MASTODON_BASE_URL", "").strip().rstrip("/")
    token = os.environ.get("MASTODON_ACCESS_TOKEN", "").strip()
    if not base or not token:
        print("[post] Mastodon: kein Token/URL — übersprungen")
        return

    r = httpx.post(
        f"{base}/api/v1/statuses",
        json={"status": text, "visibility": "public", "language": "de"},
        headers={"Authorization": f"Bearer {token}"},
        timeout=30.0,
    )
    if r.status_code >= 300:
        print(f"[post] Mastodon-Fehler {r.status_code}: {r.text[:200]}", file=sys.stderr)
    else:
        print(f"[post] Mastodon ✓ {r.json().get('url', '')}")


def _post_linkedin(text: str) -> None:
    token = os.environ.get("LINKEDIN_ACCESS_TOKEN", "").strip()
    author = os.environ.get("LINKEDIN_AUTHOR_URN", "").strip()
    if not token or not author:
        print("[post] LinkedIn: kein Token/Author — übersprungen")
        return

    payload = {
        "author": author,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": text},
                "shareMediaCategory": "NONE",
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
    }

    r = httpx.post(
        "https://api.linkedin.com/v2/ugcPosts",
        json=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "X-Restli-Protocol-Version": "2.0.0",
            "Content-Type": "application/json",
        },
        timeout=30.0,
    )
    if r.status_code >= 300:
        print(f"[post] LinkedIn-Fehler {r.status_code}: {r.text}", file=sys.stderr)
    else:
        print("[post] LinkedIn ✓")


def _post_x(text: str) -> None:
    bearer = os.environ.get("X_BEARER_TOKEN", "").strip()
    if not bearer:
        print("[post] X: kein Bearer Token — übersprungen")
        return

    r = httpx.post(
        "https://api.x.com/2/tweets",
        json={"text": text},
        headers={
            "Authorization": f"Bearer {bearer}",
            "Content-Type": "application/json",
        },
        timeout=30.0,
    )
    if r.status_code >= 300:
        print(f"[post] X-Fehler {r.status_code}: {r.text}", file=sys.stderr)
    else:
        print("[post] X ✓")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=dt.date.today().isoformat())
    args = ap.parse_args()

    date = dt.date.fromisoformat(args.date)
    md = _load_report(date)

    _post_mastodon(_shorten_for_mastodon(md, date))
    _post_linkedin(_shorten_for_linkedin(md))
    _post_x(_shorten_for_x(md))
    return 0


if __name__ == "__main__":
    sys.exit(main())
