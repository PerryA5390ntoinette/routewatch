"""Tests for routewatch.commands.show_baseline."""
from __future__ import annotations

import io

import pytest

from routewatch.commands.show_baseline import run_baseline
from routewatch.config import AlertConfig, AppConfig, EndpointConfig
from routewatch.history import EndpointHistory, record
from routewatch.monitor import CheckResult

# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------

URL_A = "https://api.example.com/health"
URL_B = "https://api.example.com/metrics"


@pytest.fixture()
def app_config() -> AppConfig:
    return AppConfig(
        endpoints=[
            EndpointConfig(url=URL_A, interval_seconds=30, timeout_seconds=5),
            EndpointConfig(url=URL_B, interval_seconds=30, timeout_seconds=5),
        ],
        alert=AlertConfig(webhook_url="https://hooks.example.com", threshold_ms=500),
    )


def _make_result(url: str, rt: float | None) -> CheckResult:
    return CheckResult(
        url=url,
        status_code=200 if rt is not None else None,
        response_time_ms=rt,
        error=None if rt is not None else "timeout",
        timestamp="2024-06-01T12:00:00",
    )


@pytest.fixture()
def histories() -> dict[str, EndpointHistory]:
    h_a = EndpointHistory(url=URL_A, max_size=100)
    for t in [100.0, 120.0, 110.0, 130.0, 105.0]:
        record(h_a, _make_result(URL_A, t))

    h_b = EndpointHistory(url=URL_B, max_size=100)
    # no data yet

    return {URL_A: h_a, URL_B: h_b}


# ---------------------------------------------------------------------------
# tests
# ---------------------------------------------------------------------------

def test_run_baseline_writes_output(app_config, histories):
    buf = io.StringIO()
    run_baseline(app_config, histories, out=buf)
    assert len(buf.getvalue()) > 0


def test_run_baseline_contains_endpoint_url(app_config, histories):
    buf = io.StringIO()
    run_baseline(app_config, histories, out=buf)
    assert URL_A in buf.getvalue()


def test_run_baseline_shows_sample_count(app_config, histories):
    buf = io.StringIO()
    run_baseline(app_config, histories, out=buf)
    # 5 samples were recorded for URL_A
    assert "5" in buf.getvalue()


def test_run_baseline_shows_median(app_config, histories):
    buf = io.StringIO()
    run_baseline(app_config, histories, out=buf)
    # median of [100, 105, 110, 120, 130] == 110.0
    assert "110.0" in buf.getvalue()


def test_run_baseline_empty_history_shows_na(app_config, histories):
    buf = io.StringIO()
    run_baseline(app_config, histories, out=buf)
    assert "n/a" in buf.getvalue()


def test_run_baseline_shows_multiplier_note(app_config, histories):
    buf = io.StringIO()
    run_baseline(app_config, histories, out=buf, multiplier=3.0)
    output = buf.getvalue()
    assert "3.0" in output
    assert "multiplier" in output.lower()


def test_run_baseline_both_endpoints_present(app_config, histories):
    buf = io.StringIO()
    run_baseline(app_config, histories, out=buf)
    output = buf.getvalue()
    assert URL_A in output
    assert URL_B in output
