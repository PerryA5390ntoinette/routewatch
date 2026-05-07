"""Tests for routewatch.anomaly and routewatch.commands.show_anomalies."""

from __future__ import annotations

import io
from datetime import datetime, timezone

import pytest

from routewatch.anomaly import AnomalyResult, detect, detect_all
from routewatch.commands.show_anomalies import run_anomalies
from routewatch.config import AlertConfig, AppConfig, EndpointConfig
from routewatch.history import EndpointHistory, record
from routewatch.monitor import CheckResult


def _make_result(url: str, rt: float | None = 100.0, ok: bool = True) -> CheckResult:
    return CheckResult(
        url=url,
        status_code=200 if ok else 0,
        response_time_ms=rt,
        error=None if ok else "timeout",
        timestamp=datetime.now(timezone.utc),
    )


def _history_with_times(url: str, times: list[float]) -> EndpointHistory:
    h = EndpointHistory(url=url, max_size=200)
    for t in times:
        record(h, _make_result(url, rt=t))
    return h


# ---------------------------------------------------------------------------
# detect()
# ---------------------------------------------------------------------------

def test_detect_no_response_time():
    h = _history_with_times("http://a.test", [100, 110, 90])
    result = _make_result("http://a.test", rt=None, ok=False)
    ar = detect(result, h)
    assert ar.is_anomaly is False
    assert ar.z_score is None
    assert "failed" in ar.reason


def test_detect_insufficient_history():
    h = EndpointHistory(url="http://a.test", max_size=200)
    result = _make_result("http://a.test", rt=500.0)
    ar = detect(result, h)
    assert ar.is_anomaly is False
    assert ar.mean_ms is None


def test_detect_normal_value_not_anomaly():
    times = [100.0] * 20
    h = _history_with_times("http://a.test", times)
    result = _make_result("http://a.test", rt=102.0)
    ar = detect(result, h)
    assert ar.is_anomaly is False


def test_detect_spike_is_anomaly():
    times = [100.0] * 30
    h = _history_with_times("http://a.test", times)
    # Introduce variance so stddev > 0
    for t in [95, 105, 98, 103]:
        record(h, _make_result("http://a.test", rt=float(t)))
    result = _make_result("http://a.test", rt=9999.0)
    ar = detect(result, h)
    assert ar.is_anomaly is True
    assert ar.z_score is not None
    assert ar.z_score > 2.5


def test_detect_zero_variance_not_anomaly():
    times = [200.0] * 10
    h = _history_with_times("http://a.test", times)
    result = _make_result("http://a.test", rt=200.0)
    ar = detect(result, h)
    assert ar.is_anomaly is False
    assert "zero variance" in ar.reason


def test_detect_custom_sigma_threshold():
    times = [100.0] * 20 + [95.0, 105.0, 98.0, 102.0]
    h = _history_with_times("http://a.test", times)
    result = _make_result("http://a.test", rt=130.0)
    ar_strict = detect(result, h, sigma_threshold=1.0)
    ar_loose = detect(result, h, sigma_threshold=10.0)
    assert ar_strict.is_anomaly is True
    assert ar_loose.is_anomaly is False


# ---------------------------------------------------------------------------
# detect_all()
# ---------------------------------------------------------------------------

def test_detect_all_returns_one_per_endpoint():
    h1 = _history_with_times("http://a.test", [100] * 10)
    h2 = _history_with_times("http://b.test", [200] * 10)
    results = detect_all({"http://a.test": h1, "http://b.test": h2})
    assert len(results) == 2


def test_detect_all_empty_history_skipped():
    h = EndpointHistory(url="http://empty.test", max_size=50)
    results = detect_all({"http://empty.test": h})
    assert results == []


# ---------------------------------------------------------------------------
# run_anomalies() (command)
# ---------------------------------------------------------------------------

@pytest.fixture
def app_config():
    ep = EndpointConfig(url="http://svc.test", interval_seconds=30, timeout_seconds=5)
    alert = AlertConfig(webhook_url="http://hook.test", response_time_threshold_ms=500)
    return AppConfig(endpoints=[ep], alert=alert)


@pytest.fixture
def histories():
    times = [100.0] * 20 + [95.0, 105.0]
    return {"http://svc.test": _history_with_times("http://svc.test", times)}


def test_run_anomalies_writes_output(app_config, histories):
    buf = io.StringIO()
    run_anomalies(app_config, histories, out=buf)
    assert len(buf.getvalue()) > 0


def test_run_anomalies_contains_endpoint_url(app_config, histories):
    buf = io.StringIO()
    run_anomalies(app_config, histories, out=buf)
    assert "http://svc.test" in buf.getvalue()


def test_run_anomalies_summary_line(app_config, histories):
    buf = io.StringIO()
    run_anomalies(app_config, histories, out=buf)
    assert "detected" in buf.getvalue()


def test_run_anomalies_header_present(app_config, histories):
    buf = io.StringIO()
    run_anomalies(app_config, histories, out=buf)
    assert "ENDPOINT" in buf.getvalue()
    assert "Z-SCORE" in buf.getvalue()
