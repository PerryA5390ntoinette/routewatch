"""Tests for routewatch.commands.show_status."""
from __future__ import annotations

import io
from datetime import datetime, timezone
from typing import Dict

import pytest

from routewatch.commands.show_status import run_status
from routewatch.config import AlertConfig, AppConfig, EndpointConfig
from routewatch.history import EndpointHistory, record
from routewatch.monitor import CheckResult


def _make_result(
    url: str,
    status_code: int = 200,
    response_time_ms: float | None = 120.0,
    error: str | None = None,
) -> CheckResult:
    return CheckResult(
        url=url,
        status_code=status_code,
        response_time_ms=response_time_ms,
        error=error,
        timestamp=datetime.now(timezone.utc),
    )


@pytest.fixture()
def app_config() -> AppConfig:
    return AppConfig(
        endpoints=[
            EndpointConfig(url="https://example.com/health", interval_seconds=30),
            EndpointConfig(url="https://api.example.com/ping", interval_seconds=60),
        ],
        alert=AlertConfig(webhook_url="https://hooks.example.com", response_time_threshold_ms=500),
    )


@pytest.fixture()
def histories(app_config: AppConfig) -> Dict[str, EndpointHistory]:
    stores: Dict[str, EndpointHistory] = {}
    for ep in app_config.endpoints:
        h = EndpointHistory(endpoint=ep, max_size=50)
        record(h, _make_result(ep.url))
        stores[ep.url] = h
    return stores


def test_run_status_writes_output(app_config: AppConfig, histories: Dict[str, EndpointHistory]) -> None:
    out = io.StringIO()
    run_status(app_config, histories, out=out)
    assert len(out.getvalue()) > 0


def test_run_status_contains_endpoint_url(app_config: AppConfig, histories: Dict[str, EndpointHistory]) -> None:
    out = io.StringIO()
    run_status(app_config, histories, out=out)
    assert "https://example.com/health" in out.getvalue()


def test_run_status_contains_header(app_config: AppConfig, histories: Dict[str, EndpointHistory]) -> None:
    out = io.StringIO()
    run_status(app_config, histories, out=out)
    assert "ENDPOINT" in out.getvalue()
    assert "STATUS" in out.getvalue()


def test_run_status_ok_label(app_config: AppConfig, histories: Dict[str, EndpointHistory]) -> None:
    out = io.StringIO()
    run_status(app_config, histories, out=out)
    assert "OK" in out.getvalue()


def test_run_status_fail_label(app_config: AppConfig) -> None:
    stores: Dict[str, EndpointHistory] = {}
    for ep in app_config.endpoints:
        h = EndpointHistory(endpoint=ep, max_size=50)
        record(h, _make_result(ep.url, status_code=500, response_time_ms=None, error="timeout"))
        stores[ep.url] = h

    out = io.StringIO()
    run_status(app_config, stores, out=out)
    assert "FAIL" in out.getvalue()


def test_run_status_avg_response_shown(app_config: AppConfig, histories: Dict[str, EndpointHistory]) -> None:
    out = io.StringIO()
    run_status(app_config, histories, out=out)
    # default result has 120.0 ms response time
    assert "120.0" in out.getvalue()


def test_run_status_empty_history_shows_unknown(app_config: AppConfig) -> None:
    stores: Dict[str, EndpointHistory] = {
        ep.url: EndpointHistory(endpoint=ep, max_size=50) for ep in app_config.endpoints
    }
    out = io.StringIO()
    run_status(app_config, stores, out=out)
    assert "UNKNOWN" in out.getvalue()
