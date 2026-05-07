"""Tests for routewatch.uptime module."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock

import pytest

from routewatch.uptime import compute_uptime, UptimeStats, DowntimeWindow, compute_all
from routewatch.history import EndpointHistory, record
from routewatch.monitor import CheckResult


def _make_result(url: str, status: int, response_ms: float, offset_seconds: int = 0) -> CheckResult:
    return CheckResult(
        endpoint_url=url,
        status_code=status,
        response_time_ms=response_ms,
        error=None,
        checked_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc) + timedelta(seconds=offset_seconds),
    )


def _make_error_result(url: str, offset_seconds: int = 0) -> CheckResult:
    return CheckResult(
        endpoint_url=url,
        status_code=None,
        response_time_ms=None,
        error="Connection refused",
        checked_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc) + timedelta(seconds=offset_seconds),
    )


@pytest.fixture
def empty_history():
    return EndpointHistory(endpoint_url="https://example.com", max_size=50)


@pytest.fixture
def all_healthy_history():
    h = EndpointHistory(endpoint_url="https://example.com", max_size=50)
    for i in range(5):
        record(h, _make_result("https://example.com", 200, 100.0, offset_seconds=i * 10))
    return h


@pytest.fixture
def mixed_history():
    h = EndpointHistory(endpoint_url="https://example.com", max_size=50)
    record(h, _make_result("https://example.com", 200, 100.0, offset_seconds=0))
    record(h, _make_error_result("https://example.com", offset_seconds=10))
    record(h, _make_error_result("https://example.com", offset_seconds=20))
    record(h, _make_result("https://example.com", 200, 100.0, offset_seconds=30))
    return h


def test_empty_history_returns_100_pct(empty_history):
    stats = compute_uptime(empty_history)
    assert stats.uptime_pct == 100.0
    assert stats.total_checks == 0


def test_all_healthy_uptime_is_100(all_healthy_history):
    stats = compute_uptime(all_healthy_history)
    assert stats.uptime_pct == 100.0
    assert stats.healthy_checks == stats.total_checks


def test_mixed_history_uptime_pct(mixed_history):
    stats = compute_uptime(mixed_history)
    assert stats.total_checks == 4
    assert stats.healthy_checks == 2
    assert stats.uptime_pct == 50.0


def test_downtime_windows_detected(mixed_history):
    stats = compute_uptime(mixed_history)
    assert len(stats.downtime_windows) == 1


def test_downtime_window_has_end_when_recovered(mixed_history):
    stats = compute_uptime(mixed_history)
    window = stats.downtime_windows[0]
    assert window.ended_at is not None


def test_ongoing_downtime_window_has_no_end():
    h = EndpointHistory(endpoint_url="https://example.com", max_size=50)
    record(h, _make_result("https://example.com", 200, 100.0, offset_seconds=0))
    record(h, _make_error_result("https://example.com", offset_seconds=10))
    record(h, _make_error_result("https://example.com", offset_seconds=20))

    stats = compute_uptime(h)
    assert len(stats.downtime_windows) == 1
    assert stats.downtime_windows[0].ended_at is None


def test_downtime_window_duration(mixed_history):
    stats = compute_uptime(mixed_history)
    window = stats.downtime_windows[0]
    assert window.duration_seconds == pytest.approx(20.0)


def test_compute_all_returns_entry_per_endpoint():
    urls = ["https://a.com", "https://b.com"]
    histories = {url: EndpointHistory(endpoint_url=url, max_size=10) for url in urls}
    result = compute_all(histories)
    assert set(result.keys()) == set(urls)
    assert all(isinstance(v, UptimeStats) for v in result.values())
