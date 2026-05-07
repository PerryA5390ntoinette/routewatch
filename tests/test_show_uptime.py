"""Tests for routewatch.commands.show_uptime."""
from __future__ import annotations

import io
from datetime import datetime, timezone, timedelta

import pytest

from routewatch.commands.show_uptime import run_uptime
from routewatch.config import AppConfig, EndpointConfig, AlertConfig
from routewatch.history import EndpointHistory, record
from routewatch.monitor import CheckResult


def _make_result(url: str, status: int, offset: int = 0) -> CheckResult:
    return CheckResult(
        endpoint_url=url,
        status_code=status,
        response_time_ms=120.0,
        error=None,
        checked_at=datetime(2024, 6, 1, 10, 0, 0, tzinfo=timezone.utc) + timedelta(seconds=offset),
    )


def _make_error(url: str, offset: int = 0) -> CheckResult:
    return CheckResult(
        endpoint_url=url,
        status_code=None,
        response_time_ms=None,
        error="timeout",
        checked_at=datetime(2024, 6, 1, 10, 0, 0, tzinfo=timezone.utc) + timedelta(seconds=offset),
    )


@pytest.fixture
def app_config():
    return AppConfig(
        endpoints=[
            EndpointConfig(url="https://alpha.io", interval_seconds=30, timeout_seconds=5),
            EndpointConfig(url="https://beta.io", interval_seconds=30, timeout_seconds=5),
        ],
        alert=AlertConfig(webhook_url="https://hook.example.com", response_time_threshold_ms=500),
        history_max_size=100,
    )


@pytest.fixture
def histories(app_config):
    hs = {}
    for ep in app_config.endpoints:
        h = EndpointHistory(endpoint_url=ep.url, max_size=50)
        record(h, _make_result(ep.url, 200, offset=0))
        record(h, _make_error(ep.url, offset=10))
        record(h, _make_result(ep.url, 200, offset=20))
        hs[ep.url] = h
    return hs


def test_run_uptime_writes_output(app_config, histories):
    buf = io.StringIO()
    run_uptime(app_config, histories, out=buf)
    assert len(buf.getvalue()) > 0


def test_run_uptime_contains_endpoint_url(app_config, histories):
    buf = io.StringIO()
    run_uptime(app_config, histories, out=buf)
    assert "alpha.io" in buf.getvalue()
    assert "beta.io" in buf.getvalue()


def test_run_uptime_shows_uptime_percentage(app_config, histories):
    buf = io.StringIO()
    run_uptime(app_config, histories, out=buf)
    assert "%" in buf.getvalue()


def test_run_uptime_shows_outage_count(app_config, histories):
    buf = io.StringIO()
    run_uptime(app_config, histories, out=buf)
    output = buf.getvalue()
    # Each endpoint has 1 outage window (error sandwiched between healthy checks)
    assert "1" in output


def test_run_uptime_header_present(app_config, histories):
    buf = io.StringIO()
    run_uptime(app_config, histories, out=buf)
    output = buf.getvalue()
    assert "ENDPOINT" in output
    assert "UPTIME" in output
    assert "OUTAGES" in output


def test_run_uptime_empty_histories(app_config):
    empty = {ep.url: EndpointHistory(endpoint_url=ep.url, max_size=50) for ep in app_config.endpoints}
    buf = io.StringIO()
    run_uptime(app_config, empty, out=buf)
    output = buf.getvalue()
    assert "100.00%" in output
