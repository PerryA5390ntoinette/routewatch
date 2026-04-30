"""Tests for routewatch.commands.show_history."""
from __future__ import annotations

import time
import io
import pytest

from routewatch.config import AppConfig, EndpointConfig, AlertConfig
from routewatch.monitor import CheckResult
from routewatch.history import EndpointHistory, record
from routewatch.commands.show_history import run_history


URL = "https://example.com/api"


def _make_result(healthy: bool = True, rt: float = 120.0, error: str | None = None) -> CheckResult:
    return CheckResult(
        url=URL,
        status_code=200 if healthy else 500,
        response_time_ms=rt,
        is_healthy=healthy,
        error=error,
        checked_at=time.time(),
    )


@pytest.fixture()
def app_config() -> AppConfig:
    return AppConfig(
        endpoints=[EndpointConfig(url=URL, timeout_s=5.0, max_response_time_ms=500.0)],
        alert=AlertConfig(webhook_url="https://hooks.example.com", threshold_consecutive_failures=2),
        check_interval_s=30,
        history_size=50,
    )


@pytest.fixture()
def histories(app_config: AppConfig) -> dict:
    h = EndpointHistory(max_size=50)
    for i in range(5):
        record(h, _make_result(healthy=(i % 2 == 0), rt=100.0 + i * 10))
    return {URL: h}


def test_run_history_writes_output(app_config, histories):
    out = io.StringIO()
    run_history(app_config, histories, out=out)
    assert len(out.getvalue()) > 0


def test_run_history_contains_endpoint_url(app_config, histories):
    out = io.StringIO()
    run_history(app_config, histories, out=out)
    assert URL in out.getvalue()


def test_run_history_shows_ok_and_fail(app_config, histories):
    out = io.StringIO()
    run_history(app_config, histories, out=out)
    text = out.getvalue()
    assert "OK" in text
    assert "FAIL" in text


def test_run_history_limit_respected(app_config, histories):
    out = io.StringIO()
    run_history(app_config, histories, limit=2, out=out)
    text = out.getvalue()
    # Only 2 data rows should appear (rows 1 and 2)
    assert "  1  " in text
    assert "  2  " in text
    assert "  3  " not in text


def test_run_history_no_data_message(app_config):
    empty_histories: dict = {URL: EndpointHistory(max_size=50)}
    out = io.StringIO()
    run_history(app_config, empty_histories, out=out)
    assert "No data recorded yet" in out.getvalue()


def test_run_history_missing_history_key(app_config):
    out = io.StringIO()
    run_history(app_config, {}, out=out)
    assert "No data recorded yet" in out.getvalue()


def test_run_history_error_shown(app_config):
    h = EndpointHistory(max_size=50)
    record(h, _make_result(healthy=False, rt=None, error="Connection refused"))
    out = io.StringIO()
    run_history(app_config, {URL: h}, out=out)
    assert "Connection refused" in out.getvalue()
