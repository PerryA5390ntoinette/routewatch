"""Tests for routewatch.commands.show_latency_budget."""

from __future__ import annotations

import io

import pytest

from routewatch.config import AppConfig, EndpointConfig, AlertConfig
from routewatch.history import EndpointHistory, record
from routewatch.monitor import CheckResult
from routewatch.commands.show_latency_budget import run_latency_budget


def _make_result(url: str, rt: float) -> CheckResult:
    return CheckResult(
        url=url,
        status_code=200,
        response_time_ms=rt,
        error=None,
        timestamp=0.0,
    )


@pytest.fixture()
def app_config() -> AppConfig:
    return AppConfig(
        endpoints=[
            EndpointConfig(url="http://alpha.io", response_time_threshold_ms=400),
            EndpointConfig(url="http://beta.io", response_time_threshold_ms=600),
        ],
        alert=AlertConfig(webhook_url="http://hook", threshold_consecutive_failures=2),
        check_interval_seconds=30,
    )


@pytest.fixture()
def histories(app_config: AppConfig) -> dict[str, EndpointHistory]:
    out: dict[str, EndpointHistory] = {}
    for ep in app_config.endpoints:
        h = EndpointHistory(url=ep.url, max_size=20)
        record(h, _make_result(ep.url, 200.0))
        record(h, _make_result(ep.url, 220.0))
        out[ep.url] = h
    return out


def test_run_latency_budget_writes_output(app_config, histories):
    buf = io.StringIO()
    run_latency_budget(app_config, histories, out=buf)
    assert len(buf.getvalue()) > 0


def test_run_latency_budget_contains_endpoint_url(app_config, histories):
    buf = io.StringIO()
    run_latency_budget(app_config, histories, out=buf)
    assert "http://alpha.io" in buf.getvalue()
    assert "http://beta.io" in buf.getvalue()


def test_run_latency_budget_contains_header(app_config, histories):
    buf = io.StringIO()
    run_latency_budget(app_config, histories, out=buf)
    assert "BUDGET" in buf.getvalue()
    assert "CONSUMED" in buf.getvalue()


def test_run_latency_budget_shows_status(app_config, histories):
    buf = io.StringIO()
    run_latency_budget(app_config, histories, out=buf)
    content = buf.getvalue()
    # both endpoints are well within budget -> "ok"
    assert "ok" in content


def test_run_latency_budget_empty_history(app_config):
    empty_histories = {
        ep.url: EndpointHistory(url=ep.url, max_size=20)
        for ep in app_config.endpoints
    }
    buf = io.StringIO()
    run_latency_budget(app_config, empty_histories, out=buf)
    assert "no_data" in buf.getvalue()
