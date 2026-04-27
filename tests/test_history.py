"""Tests for the history module."""

import pytest

from routewatch.monitor import CheckResult
from routewatch.history import EndpointHistory, HistoryStore, DEFAULT_MAX_ENTRIES


def make_result(url="https://example.com", status=200, rt=100.0, healthy=True):
    return CheckResult(url=url, status_code=status, response_time_ms=rt, is_healthy=healthy, error=None)


def test_record_and_latest():
    hist = EndpointHistory(url="https://example.com")
    r = make_result(rt=200.0)
    hist.record(r)
    assert hist.latest == r


def test_ring_buffer_evicts_oldest():
    hist = EndpointHistory(url="https://example.com", max_entries=3)
    for i in range(4):
        hist.record(make_result(rt=float(i * 10)))
    assert len(hist.results) == 3
    assert hist.results[0].response_time_ms == 10.0


def test_average_response_time():
    hist = EndpointHistory(url="https://example.com")
    for rt in [100.0, 200.0, 300.0]:
        hist.record(make_result(rt=rt))
    assert hist.average_response_time_ms() == pytest.approx(200.0)


def test_average_response_time_empty():
    hist = EndpointHistory(url="https://example.com")
    assert hist.average_response_time_ms() is None


def test_error_rate():
    hist = EndpointHistory(url="https://example.com")
    hist.record(make_result(healthy=True))
    hist.record(make_result(healthy=False))
    hist.record(make_result(healthy=False))
    assert hist.error_rate() == pytest.approx(2 / 3)


def test_error_rate_empty():
    hist = EndpointHistory(url="https://example.com")
    assert hist.error_rate() == 0.0


def test_history_store_record_and_get():
    store = HistoryStore()
    r = make_result(url="https://a.com")
    store.record(r)
    hist = store.get("https://a.com")
    assert hist is not None
    assert hist.latest == r


def test_history_store_missing_url_returns_none():
    store = HistoryStore()
    assert store.get("https://missing.com") is None


def test_history_store_summary():
    store = HistoryStore()
    store.record(make_result(url="https://a.com", rt=150.0, healthy=True))
    store.record(make_result(url="https://a.com", rt=250.0, healthy=False))
    summary = store.summary()
    assert len(summary) == 1
    assert summary[0]["url"] == "https://a.com"
    assert summary[0]["checks"] == 2
    assert summary[0]["error_rate"] == pytest.approx(0.5)
