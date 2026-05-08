"""Unit tests for routewatch.heatmap."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from routewatch.history import EndpointHistory
from routewatch.monitor import CheckResult
from routewatch.heatmap import (
    HeatmapResult,
    compute_heatmap,
    compute_all,
    peak_hour,
)

_URL = "https://example.com/api"


def _make_result(
    hour: int,
    response_ms: float | None = 120.0,
    error: str | None = None,
) -> CheckResult:
    ts = datetime(2024, 1, 15, hour, 0, 0, tzinfo=timezone.utc)
    return CheckResult(
        url=_URL,
        status_code=200 if error is None else None,
        response_time_ms=response_ms,
        checked_at=ts,
        error=error,
    )


@pytest.fixture()
def history() -> EndpointHistory:
    h = EndpointHistory(url=_URL, max_size=200)
    return h


def test_compute_heatmap_returns_24_buckets(history):
    result = compute_heatmap(_URL, history)
    assert len(result.buckets) == 24


def test_compute_heatmap_bucket_hours_are_0_to_23(history):
    result = compute_heatmap(_URL, history)
    assert [b.hour for b in result.buckets] == list(range(24))


def test_empty_history_all_none_avg(history):
    result = compute_heatmap(_URL, history)
    assert all(b.avg_response_ms is None for b in result.buckets)


def test_single_result_populates_correct_bucket(history):
    history.results.append(_make_result(hour=9, response_ms=200.0))
    result = compute_heatmap(_URL, history)
    assert result.buckets[9].sample_count == 1
    assert result.buckets[9].avg_response_ms == 200.0


def test_average_across_multiple_results_same_hour(history):
    history.results.append(_make_result(hour=14, response_ms=100.0))
    history.results.append(_make_result(hour=14, response_ms=200.0))
    result = compute_heatmap(_URL, history)
    assert result.buckets[14].avg_response_ms == 150.0
    assert result.buckets[14].sample_count == 2


def test_error_results_excluded_from_avg(history):
    history.results.append(_make_result(hour=6, response_ms=None, error="timeout"))
    history.results.append(_make_result(hour=6, response_ms=300.0))
    result = compute_heatmap(_URL, history)
    assert result.buckets[6].error_count == 1
    assert result.buckets[6].avg_response_ms == 300.0


def test_all_errors_gives_none_avg(history):
    history.results.append(_make_result(hour=3, response_ms=None, error="conn refused"))
    result = compute_heatmap(_URL, history)
    assert result.buckets[3].avg_response_ms is None


def test_peak_hour_returns_slowest_hour(history):
    history.results.append(_make_result(hour=10, response_ms=100.0))
    history.results.append(_make_result(hour=22, response_ms=999.0))
    result = compute_heatmap(_URL, history)
    assert peak_hour(result) == 22


def test_peak_hour_none_when_no_data(history):
    result = compute_heatmap(_URL, history)
    assert peak_hour(result) is None


def test_compute_all_returns_entry_per_url():
    h1 = EndpointHistory(url="https://a.com", max_size=50)
    h2 = EndpointHistory(url="https://b.com", max_size=50)
    results = compute_all({"https://a.com": h1, "https://b.com": h2})
    assert set(results.keys()) == {"https://a.com", "https://b.com"}
