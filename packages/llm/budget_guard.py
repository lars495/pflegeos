"""Hartes Tagesbudget für LLM-Calls über OpenRouter.

Aufrufer registrieren *vor* dem Call die voraussichtlichen Kosten via
`reserve()`. Nach dem Call wird mit `commit()` die tatsächliche
Verbrauchsmenge gebucht. Wird `BudgetExceeded` geworfen, hat der Aufrufer
auf billigeres Modell auszuweichen oder den Call zu unterlassen.

Persistenz in Redis (Schlüssel: budget:YYYY-MM-DD).
Externe Topf-Budgets (z. B. Legal-Audit) bekommen eigene Keys.
"""

from __future__ import annotations

import datetime as dt
import os
import sys
from contextlib import contextmanager
from dataclasses import dataclass

import redis


class BudgetExceeded(Exception):
    """Wird geworfen, wenn ein Call das Tagesbudget sprengen würde."""


@dataclass(frozen=True)
class BudgetState:
    pot: str
    date: dt.date
    spent_usd: float
    limit_usd: float

    @property
    def remaining_usd(self) -> float:
        return max(0.0, self.limit_usd - self.spent_usd)

    @property
    def utilisation(self) -> float:
        return 0.0 if self.limit_usd <= 0 else self.spent_usd / self.limit_usd


class BudgetGuard:
    """Atomare Budget-Buchhaltung via Redis."""

    DEFAULT_POT = "daily"

    def __init__(
        self,
        redis_url: str | None = None,
        daily_limit_usd: float | None = None,
        monthly_legal_limit_usd: float | None = None,
    ):
        self.redis = redis.Redis.from_url(
            redis_url or os.environ["REDIS_URL"], decode_responses=True
        )
        self.daily_limit = daily_limit_usd or float(
            os.environ.get("DAILY_BUDGET_USD", "1.10")
        )
        self.legal_limit = monthly_legal_limit_usd or float(
            os.environ.get("LEGAL_AUDIT_MONTHLY_BUDGET_USD", "6.00")
        )

    # ── Lookups ────────────────────────────────────────────────
    def _key(self, pot: str, date: dt.date | None = None) -> str:
        date = date or dt.date.today()
        if pot == "legal":
            return f"budget:legal:{date.strftime('%Y-%m')}"
        return f"budget:{pot}:{date.isoformat()}"

    def _limit_for(self, pot: str) -> float:
        return self.legal_limit if pot == "legal" else self.daily_limit

    def state(self, pot: str = DEFAULT_POT) -> BudgetState:
        key = self._key(pot)
        spent = float(self.redis.get(key) or 0.0)
        return BudgetState(
            pot=pot,
            date=dt.date.today(),
            spent_usd=spent,
            limit_usd=self._limit_for(pot),
        )

    # ── Reservation & Commit ───────────────────────────────────
    def reserve(self, estimated_usd: float, pot: str = DEFAULT_POT) -> None:
        """Wirft BudgetExceeded, wenn keine Reserve mehr da ist."""
        s = self.state(pot)
        if s.spent_usd + estimated_usd > s.limit_usd:
            raise BudgetExceeded(
                f"[{pot}] would exceed limit: "
                f"spent ${s.spent_usd:.4f} + est ${estimated_usd:.4f} "
                f"> limit ${s.limit_usd:.2f}"
            )

    def commit(self, actual_usd: float, pot: str = DEFAULT_POT) -> BudgetState:
        """Schreibt tatsächlichen Verbrauch. Idempotent nicht möglich –
        Caller darf nur einmal pro Call committen."""
        key = self._key(pot)
        ttl_days = 35 if pot == "legal" else 7
        self.redis.incrbyfloat(key, actual_usd)
        self.redis.expire(key, ttl_days * 86400)
        return self.state(pot)

    @contextmanager
    def call(self, estimated_usd: float, pot: str = DEFAULT_POT):
        """Convenience-Kontext: reserviert vor, comitted nach Call.

        Aufrufer setzt im With-Block `actual` auf die wahren Kosten:

            with guard.call(0.002) as call:
                response = client.chat(...)
                call.actual_usd = response.cost
        """
        self.reserve(estimated_usd, pot)

        class _Slot:
            actual_usd: float = estimated_usd

        slot = _Slot()
        try:
            yield slot
        finally:
            self.commit(slot.actual_usd, pot)

    # ── Strategien für Modellauswahl ───────────────────────────
    def should_downshift(self, pot: str = DEFAULT_POT, threshold: float = 0.9) -> bool:
        """True wenn nur noch <threshold>·100 % Budget übrig — auf
        billigeres Modell wechseln."""
        return self.state(pot).utilisation >= threshold

    def is_exhausted(self, pot: str = DEFAULT_POT) -> bool:
        return self.state(pot).remaining_usd <= 0.0


# ── CLI: `python -m packages.llm.budget_guard status` ─────────
def _cli_status() -> int:
    g = BudgetGuard()
    for pot in ("daily", "legal"):
        s = g.state(pot)
        print(
            f"[{pot}] spent ${s.spent_usd:.4f} / ${s.limit_usd:.2f} "
            f"({s.utilisation * 100:.1f}%) — remaining ${s.remaining_usd:.4f}"
        )
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "status":
        sys.exit(_cli_status())
    print("usage: python -m packages.llm.budget_guard status", file=sys.stderr)
    sys.exit(2)
