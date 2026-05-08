"""Tests for routewatch.latency_budget."""

from __future__ import annotations

import pytest

from routewatch.config import EndpointConfig
from routewatch.history import EndpointHistory, record
from routewatch.latency_budget import BudgetResult, compute_budget, compute_all
from routewatch.monitor import CheckResult


def _endpoint(url: str = "http://example.com", threshold_ms: int = 500) -> EndpointConfig:
    return EndpointConfig(url=url, response_time_threshold_ms=threshold_ms)


def _make_result(url: str, response_time_ms: float | None, ok: bool = True) -> CheckResult:
    return CheckResult(
        url=url,
        status_code=200 if ok else 0,
        response_time_ms=response_time_ms,
        error=None if ok else "err",
        timestamp=0.0,
    )


def _history_with_times(url: str, times: list[float]) -> EndpointHistory:
    h = EndpointHistory(url=url, max_size=50)
    for t in times:
        record(h, _make_result(url, t))
    return h


def test_no_data_returns_no_data_status():
    ep = _endpoint()
    h = EndpointHistory(url=ep.url, max_size=10)
    result = compute_budget(ep, h)
    assert result.status == "no_data"
    assert result.avg_ms is None
    assert result.consumed_pct is None
    assert result.remaining_ms is None


def test_ok_when_well_below_budget():
    ep = _endpoint(threshold_ms=500)
    h = _history_with_times(ep.url, [100.0, 120.0, 110.0])
    result = compute_budget(ep, h)
    assert result.status == "ok"
    assert result.consumed_pct is not None
    assert result.consumed_pct < 80.0


def test_warning_when_near_budget():
    ep = _endpoint(threshold_ms=500)
    # ~85% consumed
    h = _history_with_times(ep.url, [425.0, 425.0, 425.0])
    result = compute_budget(ep, h)
    assert result.status == "warning"


def test_exceeded_when_over_budget():
    ep = _endpoint(threshold_ms=300)
    h = _history_with_times(ep.url, [400.0, 420.0, 410.0])
    result = compute_budget(ep, h)
    assert result.status == "exceeded"
    assert result.consumed_pct is not None
    assert result.consumed_pct > 100.0
    assert result.remaining_ms is not None
    assert result.remaining_ms < 0


def test_budget_ms_matches_threshold():
    ep = _endpoint(threshold_ms=750)
    h = _history_with_times(ep.url, [200.0])
    result = compute_budget(ep, h)
    assert result.budget_ms == 750.0


def test_consumed_pct_calculation():
    ep = _endpoint(threshold_ms=400)
    h = _history_with_times(ep.url, [200.0, 200.0])  # avg=200, 50%
    result = compute_budget(ep, h)
    assert result.consumed_pct == pytest.approx(50.0, rel=1e-2)


def test_compute_all_returns_one_per_endpoint():
    endpoints = [
        _endpoint("http://a.com", 500),
        _endpoint("http://b.com", 300),
    ]
    histories = {
        "http://a.com": _history_with_times("http://a.com", [100.0]),
        "http://b.com": _history_with_times("http://b.com", [250.0]),
    }
    results = compute_all(endpoints, histories)
    assert len(results) == 2
    urls = [r.url for r in results]
    assert "http://a.com" in urls
    assert "http://b.com" in urls
