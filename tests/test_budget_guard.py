"""Smoke-Tests für den Budget-Guard.

Benötigt keinen echten Redis — verwendet fakeredis.
"""

import datetime as dt

import pytest

from packages.llm.budget_guard import BudgetExceeded, BudgetGuard


@pytest.fixture
def guard(monkeypatch):
    fake = pytest.importorskip("fakeredis").FakeRedis(decode_responses=True)

    g = BudgetGuard.__new__(BudgetGuard)
    g.redis = fake
    g.daily_limit = 1.10
    g.legal_limit = 6.00
    return g


def test_initial_state_is_zero(guard):
    s = guard.state()
    assert s.spent_usd == 0.0
    assert s.remaining_usd == 1.10
    assert not guard.is_exhausted()


def test_reserve_within_budget_passes(guard):
    guard.reserve(0.50)  # ok, kein commit nötig zum reservieren


def test_reserve_over_budget_raises(guard):
    guard.commit(1.00)
    with pytest.raises(BudgetExceeded):
        guard.reserve(0.20)


def test_commit_accumulates(guard):
    guard.commit(0.30)
    guard.commit(0.40)
    s = guard.state()
    assert round(s.spent_usd, 4) == 0.70


def test_downshift_threshold(guard):
    guard.commit(1.00)
    assert guard.should_downshift(threshold=0.9)


def test_legal_pot_separate(guard):
    guard.commit(1.00)
    assert not guard.is_exhausted(pot="legal")
    assert guard.state(pot="legal").remaining_usd == 6.00


def test_call_context_commits_actual(guard):
    with guard.call(estimated_usd=0.10) as call:
        call.actual_usd = 0.07
    assert round(guard.state().spent_usd, 4) == 0.07
