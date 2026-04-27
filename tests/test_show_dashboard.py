"""Tests for routewatch.commands.show_dashboard."""

from __future__ import annotations

import io
import sys

import pytest

from routewatch.commands.show_dashboard import run_dashboard
from routewatch.config import AlertConfig, AppConfig, EndpointConfig
from routewatch.history import EndpointHistory, record
from routewatch.monitor import CheckResult


def _make_result(url: str, response_time_ms: float = 80.0) -> CheckResult:
    return CheckResult(url=url, status_code=200, response_time_ms=response_time_ms, error=None)


@pytest.fixture()
def app_config() -> AppConfig:
    endpoint = EndpointConfig(
        name="api",
        url="http://api.example.com",
        interval_seconds=30,
        timeout_seconds=5,
    )
    alert = AlertConfig(
        webhook_url="http://hooks.example.com/alert",
        response_time_threshold_ms=500.0,
        failure_threshold=2,
    )
    return AppConfig(endpoints=[endpoint], alert=alert)


@pytest.fixture()
def histories() -> dict[str, EndpointHistory]:
    h = EndpointHistory(url="http://api.example.com", maxlen=10)
    record(h, _make_result("http://api.example.com", 80.0))
    return {"api": h}


def test_run_dashboard_once_writes_output(app_config, histories, capsys):
    run_dashboard(app_config, histories, once=True)
    captured = capsys.readouterr()
    assert "RouteWatch Dashboard" in captured.out


def test_run_dashboard_once_shows_endpoint_name(app_config, histories, capsys):
    run_dashboard(app_config, histories, once=True)
    captured = capsys.readouterr()
    assert "api" in captured.out


def test_run_dashboard_uses_slow_threshold(app_config, capsys):
    h = EndpointHistory(url="http://api.example.com", maxlen=10)
    record(h, _make_result("http://api.example.com", response_time_ms=800.0))
    run_dashboard(app_config, {"api": h}, once=True)
    captured = capsys.readouterr()
    assert "SLOW" in captured.out


def test_run_dashboard_empty_histories(app_config, capsys):
    run_dashboard(app_config, {}, once=True)
    captured = capsys.readouterr()
    assert "RouteWatch Dashboard" in captured.out
