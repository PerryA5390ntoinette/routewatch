"""Tests for routewatch.digest."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from routewatch.config import EndpointConfig, AlertConfig
from routewatch.digest import (
    DigestEntry,
    Digest,
    build_digest,
    format_digest_text,
)
from routewatch.history import EndpointHistory
from routewatch.monitor import CheckResult


def _ep(url: str = "http://example.com") -> EndpointConfig:
    return EndpointConfig(
        url=url,
        interval_seconds=30,
        timeout_seconds=5,
        alert=AlertConfig(webhook_url="http://hook", response_time_threshold_ms=500),
    )


def _make_result(url: str, ok: bool = True, rt: float | None = 120.0) -> CheckResult:
    return CheckResult(
        url=url,
        status_code=200 if ok else 0,
        response_time_ms=rt,
        error=None if ok else "timeout",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


def _history_with(*results: CheckResult) -> EndpointHistory:
    h = EndpointHistory(max_size=50)
    for r in results:
        h.results.append(r)
    return h


@pytest.fixture()
def endpoint():
    return _ep("http://svc.local")


@pytest.fixture()
def histories(endpoint):
    return {
        endpoint.url: _history_with(
            _make_result(endpoint.url, ok=True, rt=100.0),
            _make_result(endpoint.url, ok=True, rt=200.0),
            _make_result(endpoint.url, ok=False, rt=None),
        )
    }


def test_build_digest_returns_digest(endpoint, histories):
    digest = build_digest([endpoint], histories, window_label="last-hour")
    assert isinstance(digest, Digest)


def test_build_digest_entry_count(endpoint, histories):
    digest = build_digest([endpoint], histories)
    assert len(digest.entries) == 1


def test_build_digest_error_rate(endpoint, histories):
    digest = build_digest([endpoint], histories)
    entry = digest.entries[0]
    # 1 out of 3 checks failed → ~33 %
    assert entry.error_rate_pct == pytest.approx(33.33, abs=0.1)


def test_build_digest_avg_response_ms(endpoint, histories):
    digest = build_digest([endpoint], histories)
    entry = digest.entries[0]
    # only two results have response times: 100 and 200 → avg 150
    assert entry.avg_response_ms == pytest.approx(150.0, abs=0.1)


def test_build_digest_total_checks(endpoint, histories):
    digest = build_digest([endpoint], histories)
    assert digest.entries[0].total_checks == 3


def test_build_digest_skips_missing_history(endpoint):
    digest = build_digest([endpoint], {})
    assert digest.entries == []


def test_digest_healthy_count():
    good = DigestEntry(url="a", total_checks=5, error_rate_pct=0, avg_response_ms=50, score=None, grade="A")
    bad = DigestEntry(url="b", total_checks=5, error_rate_pct=80, avg_response_ms=None, score=None, grade="F")
    digest = Digest(generated_at="now", window_label="x", entries=[good, bad])
    assert digest.healthy_count == 1
    assert digest.degraded_count == 1


def test_format_digest_text_contains_url(endpoint, histories):
    digest = build_digest([endpoint], histories)
    text = format_digest_text(digest)
    assert endpoint.url in text


def test_format_digest_text_contains_header(endpoint, histories):
    digest = build_digest([endpoint], histories, window_label="daily")
    text = format_digest_text(digest)
    assert "RouteWatch Digest" in text
    assert "daily" in text


def test_format_digest_text_contains_grade(endpoint, histories):
    digest = build_digest([endpoint], histories)
    text = format_digest_text(digest)
    # Any single letter grade should appear
    assert any(g in text for g in ("A", "B", "C", "D", "F"))
