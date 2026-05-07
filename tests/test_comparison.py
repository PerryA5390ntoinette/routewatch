"""Tests for routewatch.comparison."""
from __future__ import annotations

import datetime
from typing import List

import pytest

from routewatch.comparison import compare_endpoints, ComparisonRow
from routewatch.history import EndpointHistory, record
from routewatch.monitor import CheckResult


def _make_result(
    url: str,
    status: int = 200,
    response_time_ms: float | None = 100.0,
    error: str | None = None,
) -> CheckResult:
    return CheckResult(
        url=url,
        status_code=status,
        response_time_ms=response_time_ms,
        error=error,
        timestamp=datetime.datetime.utcnow(),
    )


@pytest.fixture()
def histories():
    fast = EndpointHistory(url="https://fast.example.com", max_size=50)
    for _ in range(5):
        record(fast, _make_result("https://fast.example.com", response_time_ms=80.0))

    slow = EndpointHistory(url="https://slow.example.com", max_size=50)
    for _ in range(5):
        record(slow, _make_result("https://slow.example.com", response_time_ms=400.0))

    error_ep = EndpointHistory(url="https://error.example.com", max_size=50)
    record(error_ep, _make_result("https://error.example.com", status=500, error="timeout"))

    return {
        "https://fast.example.com": fast,
        "https://slow.example.com": slow,
        "https://error.example.com": error_ep,
    }


def test_compare_returns_all_endpoints(histories):
    rows = compare_endpoints(histories)
    assert len(rows) == 3


def test_compare_ranks_start_at_one(histories):
    rows = compare_endpoints(histories)
    ranks = {r.rank for r in rows}
    assert min(ranks) == 1


def test_compare_error_endpoint_ranked_last(histories):
    rows = compare_endpoints(histories)
    last = max(rows, key=lambda r: r.rank)
    assert last.url == "https://error.example.com"


def test_compare_fast_endpoint_ranked_first(histories):
    rows = compare_endpoints(histories)
    first = min(rows, key=lambda r: r.rank)
    assert first.url == "https://fast.example.com"


def test_compare_avg_response_time_populated(histories):
    rows = compare_endpoints(histories)
    by_url = {r.url: r for r in rows}
    assert by_url["https://fast.example.com"].avg_response_time_ms == pytest.approx(80.0)


def test_compare_error_rate_for_error_endpoint(histories):
    rows = compare_endpoints(histories)
    by_url = {r.url: r for r in rows}
    assert by_url["https://error.example.com"].error_rate_pct == pytest.approx(100.0)


def test_compare_baseline_median_present(histories):
    rows = compare_endpoints(histories)
    by_url = {r.url: r for r in rows}
    # fast endpoint has 5 samples so baseline should be computed
    assert by_url["https://fast.example.com"].baseline_median_ms is not None


def test_compare_empty_histories():
    rows = compare_endpoints({})
    assert rows == []
