"""Tests for routewatch.baseline."""
from __future__ import annotations

import pytest

from routewatch.baseline import (
    BaselineStats,
    compute_all,
    compute_baseline,
    is_slower_than_baseline,
)
from routewatch.history import EndpointHistory, record
from routewatch.monitor import CheckResult


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

URL = "https://example.com/api"


def _make_result(response_time_ms: float | None = 120.0, ok: bool = True) -> CheckResult:
    return CheckResult(
        url=URL,
        status_code=200 if ok else None,
        response_time_ms=response_time_ms,
        error=None if ok else "timeout",
        timestamp="2024-01-01T00:00:00",
    )


def _history_with_times(*times: float | None) -> EndpointHistory:
    h = EndpointHistory(url=URL, max_size=100)
    for t in times:
        record(h, _make_result(response_time_ms=t, ok=t is not None))
    return h


# ---------------------------------------------------------------------------
# compute_baseline
# ---------------------------------------------------------------------------

def test_empty_history_returns_none_fields():
    h = EndpointHistory(url=URL, max_size=50)
    stats = compute_baseline(h)
    assert stats.median_ms is None
    assert stats.p95_ms is None
    assert stats.sample_count == 0


def test_single_sample():
    h = _history_with_times(200.0)
    stats = compute_baseline(h)
    assert stats.median_ms == 200.0
    assert stats.p95_ms == 200.0
    assert stats.sample_count == 1


def test_median_of_odd_samples():
    h = _history_with_times(100.0, 200.0, 300.0)
    stats = compute_baseline(h)
    assert stats.median_ms == 200.0


def test_median_of_even_samples():
    h = _history_with_times(100.0, 200.0, 300.0, 400.0)
    stats = compute_baseline(h)
    assert stats.median_ms == 250.0


def test_p95_large_sample():
    # 20 values: 10..200 step 10; p95 index = int(20*0.95)-1 = 18 → value 190
    h = _history_with_times(*[float(i * 10) for i in range(1, 21)])
    stats = compute_baseline(h)
    assert stats.p95_ms == 190.0


def test_none_response_times_excluded():
    h = _history_with_times(100.0, None, 300.0)
    stats = compute_baseline(h)
    assert stats.sample_count == 2
    assert stats.median_ms == 200.0


def test_url_preserved():
    h = _history_with_times(100.0)
    stats = compute_baseline(h)
    assert stats.url == URL


# ---------------------------------------------------------------------------
# is_slower_than_baseline
# ---------------------------------------------------------------------------

def test_no_baseline_never_slower():
    stats = BaselineStats(url=URL, sample_count=0, median_ms=None, p95_ms=None)
    assert is_slower_than_baseline(9999.0, stats) is False


def test_within_multiplier_not_slower():
    stats = BaselineStats(url=URL, sample_count=10, median_ms=100.0, p95_ms=180.0)
    assert is_slower_than_baseline(190.0, stats, multiplier=2.0) is False


def test_exceeds_multiplier_is_slower():
    stats = BaselineStats(url=URL, sample_count=10, median_ms=100.0, p95_ms=180.0)
    assert is_slower_than_baseline(201.0, stats, multiplier=2.0) is True


def test_custom_multiplier():
    stats = BaselineStats(url=URL, sample_count=5, median_ms=50.0, p95_ms=90.0)
    assert is_slower_than_baseline(100.0, stats, multiplier=1.5) is True
    assert is_slower_than_baseline(74.0, stats, multiplier=1.5) is False


# ---------------------------------------------------------------------------
# compute_all
# ---------------------------------------------------------------------------

def test_compute_all_keys_match_histories():
    url2 = "https://other.com"
    h1 = _history_with_times(100.0, 200.0)
    h2 = EndpointHistory(url=url2, max_size=50)
    result = compute_all({URL: h1, url2: h2})
    assert set(result.keys()) == {URL, url2}


def test_compute_all_empty_history_has_no_median():
    url2 = "https://other.com"
    h = EndpointHistory(url=url2, max_size=50)
    result = compute_all({url2: h})
    assert result[url2].median_ms is None
