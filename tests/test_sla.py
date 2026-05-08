"""Unit tests for routewatch.sla."""
from __future__ import annotations

import datetime
from unittest.mock import MagicMock

import pytest

from routewatch.history import EndpointHistory, record
from routewatch.monitor import CheckResult
from routewatch.sla import SLAResult, compute_sla, compute_all


def _make_result(url: str, *, ok: bool = True, response_time_ms: float = 120.0) -> CheckResult:
    return CheckResult(
        url=url,
        status_code=200 if ok else None,
        response_time_ms=response_time_ms if ok else None,
        error=None if ok else "timeout",
        timestamp=datetime.datetime.utcnow(),
    )


def _endpoint(url: str, sla_target_pct: float = 99.9):
    ep = MagicMock()
    ep.url = url
    ep.sla_target_pct = sla_target_pct
    return ep


def _history_with(url: str, results: list[CheckResult]) -> EndpointHistory:
    h = EndpointHistory(url=url, max_size=500)
    for r in results:
        record(h, r)
    return h


# ---------------------------------------------------------------------------

def test_compute_sla_no_history():
    ep = _endpoint("http://example.com")
    h = EndpointHistory(url=ep.url, max_size=100)
    result = compute_sla(ep, h)
    assert result.actual_pct is None
    assert result.met is None
    assert result.sample_count == 0


def test_compute_sla_all_healthy_meets_target():
    ep = _endpoint("http://example.com", sla_target_pct=99.0)
    results = [_make_result(ep.url, ok=True) for _ in range(20)]
    h = _history_with(ep.url, results)
    sla = compute_sla(ep, h)
    assert sla.actual_pct == pytest.approx(100.0)
    assert sla.met is True


def test_compute_sla_all_errors_misses_target():
    ep = _endpoint("http://example.com", sla_target_pct=99.9)
    results = [_make_result(ep.url, ok=False) for _ in range(10)]
    h = _history_with(ep.url, results)
    sla = compute_sla(ep, h)
    assert sla.actual_pct == pytest.approx(0.0)
    assert sla.met is False


def test_compute_sla_partial_errors():
    ep = _endpoint("http://example.com", sla_target_pct=90.0)
    # 9 ok, 1 error => 90 % uptime
    results = [_make_result(ep.url, ok=True) for _ in range(9)]
    results.append(_make_result(ep.url, ok=False))
    h = _history_with(ep.url, results)
    sla = compute_sla(ep, h)
    assert sla.actual_pct == pytest.approx(90.0)
    assert sla.met is True


def test_compute_sla_just_below_target():
    ep = _endpoint("http://example.com", sla_target_pct=95.0)
    results = [_make_result(ep.url, ok=True) for _ in range(9)]
    results.append(_make_result(ep.url, ok=False))
    h = _history_with(ep.url, results)
    sla = compute_sla(ep, h)
    assert sla.met is False


def test_compute_sla_stores_target():
    ep = _endpoint("http://example.com", sla_target_pct=99.5)
    h = EndpointHistory(url=ep.url, max_size=100)
    sla = compute_sla(ep, h)
    assert sla.target_pct == 99.5


def test_compute_all_returns_one_per_endpoint():
    ep1 = _endpoint("http://a.com")
    ep2 = _endpoint("http://b.com")
    h1 = _history_with(ep1.url, [_make_result(ep1.url)])
    h2 = _history_with(ep2.url, [_make_result(ep2.url)])
    results = compute_all([ep1, ep2], {ep1.url: h1, ep2.url: h2})
    assert len(results) == 2
    assert {r.url for r in results} == {ep1.url, ep2.url}


def test_compute_all_skips_missing_history():
    ep1 = _endpoint("http://a.com")
    ep2 = _endpoint("http://b.com")
    h1 = _history_with(ep1.url, [_make_result(ep1.url)])
    results = compute_all([ep1, ep2], {ep1.url: h1})
    assert len(results) == 1
    assert results[0].url == ep1.url
