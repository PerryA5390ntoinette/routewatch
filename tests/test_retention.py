"""Tests for routewatch.retention."""

from __future__ import annotations

import time
import pytest

from routewatch.history import EndpointHistory, record
from routewatch.monitor import CheckResult
from routewatch.retention import RetentionPolicy, prune_history, prune_all


NOW = 1_700_000_000.0


def _make_result(url: str, age_seconds: float) -> CheckResult:
    return CheckResult(
        url=url,
        status_code=200,
        response_time_ms=50.0,
        error=None,
        checked_at=NOW - age_seconds,
    )


@pytest.fixture()
def history() -> EndpointHistory:
    h = EndpointHistory(url="https://example.com", max_size=20)
    for age in (300, 200, 100, 50, 10):
        record(h, _make_result("https://example.com", age))
    return h


def test_is_expired_true():
    policy = RetentionPolicy(max_age_seconds=60)
    assert policy.is_expired(NOW - 120, now=NOW) is True


def test_is_expired_false():
    policy = RetentionPolicy(max_age_seconds=60)
    assert policy.is_expired(NOW - 30, now=NOW) is False


def test_is_expired_boundary():
    policy = RetentionPolicy(max_age_seconds=60)
    # Exactly at boundary is NOT expired (strictly greater)
    assert policy.is_expired(NOW - 60, now=NOW) is False


def test_prune_history_removes_old(history):
    removed = prune_history(history, RetentionPolicy(max_age_seconds=150), now=NOW)
    assert removed == 2  # 300s and 200s old entries removed


def test_prune_history_keeps_recent(history):
    prune_history(history, RetentionPolicy(max_age_seconds=150), now=NOW)
    assert len(history.results) == 3


def test_prune_history_none_removed(history):
    removed = prune_history(history, RetentionPolicy(max_age_seconds=1000), now=NOW)
    assert removed == 0
    assert len(history.results) == 5


def test_prune_all_returns_per_url():
    h1 = EndpointHistory(url="https://a.com", max_size=10)
    h2 = EndpointHistory(url="https://b.com", max_size=10)
    record(h1, _make_result("https://a.com", 500))
    record(h2, _make_result("https://b.com", 10))

    result = prune_all(
        {"https://a.com": h1, "https://b.com": h2},
        RetentionPolicy(max_age_seconds=60),
        now=NOW,
    )
    assert result["https://a.com"] == 1
    assert result["https://b.com"] == 0
