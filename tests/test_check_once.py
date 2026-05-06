"""Tests for the check_once command."""

from __future__ import annotations

import io
from unittest.mock import patch

import pytest

from routewatch.config import AppConfig, EndpointConfig, AlertConfig
from routewatch.monitor import CheckResult
from routewatch.history import EndpointHistory
from routewatch.notifier import NotifierState
from routewatch.state_store import build_stores
from routewatch.commands.check_once import run_check_once


@pytest.fixture()
def app_config() -> AppConfig:
    return AppConfig(
        endpoints=[
            EndpointConfig(url="https://example.com", timeout_s=5, max_response_time_ms=500),
            EndpointConfig(url="https://broken.example", timeout_s=5, max_response_time_ms=500),
        ],
        alert=AlertConfig(webhook_url="https://hooks.example/w", threshold_failures=2),
        check_interval_s=30,
        history_size=10,
    )


@pytest.fixture()
def stores(app_config):
    return build_stores(app_config)


def _good_result(url: str) -> CheckResult:
    return CheckResult(url=url, status_code=200, response_time_ms=120.0, error=None)


def _bad_result(url: str) -> CheckResult:
    return CheckResult(url=url, status_code=None, response_time_ms=None, error="connection refused")


def test_run_check_once_writes_output(app_config, stores):
    histories, states = stores
    out = io.StringIO()
    side_effects = [_good_result(app_config.endpoints[0].url), _bad_result(app_config.endpoints[1].url)]

    with patch("routewatch.commands.check_once.check_endpoint", side_effect=side_effects), \
         patch("routewatch.commands.check_once.evaluate_and_notify"):
        run_check_once(app_config, histories, states, out=out, notify=False)

    output = out.getvalue()
    assert output, "expected non-empty output"


def test_run_check_once_shows_endpoint_url(app_config, stores):
    histories, states = stores
    out = io.StringIO()
    side_effects = [_good_result(app_config.endpoints[0].url), _bad_result(app_config.endpoints[1].url)]

    with patch("routewatch.commands.check_once.check_endpoint", side_effect=side_effects), \
         patch("routewatch.commands.check_once.evaluate_and_notify"):
        run_check_once(app_config, histories, states, out=out, notify=False)

    output = out.getvalue()
    assert "https://example.com" in output
    assert "https://broken.example" in output


def test_run_check_once_returns_failure_count(app_config, stores):
    histories, states = stores
    out = io.StringIO()
    side_effects = [_good_result(app_config.endpoints[0].url), _bad_result(app_config.endpoints[1].url)]

    with patch("routewatch.commands.check_once.check_endpoint", side_effect=side_effects), \
         patch("routewatch.commands.check_once.evaluate_and_notify"):
        failures = run_check_once(app_config, histories, states, out=out, notify=False)

    assert failures == 1


def test_run_check_once_all_healthy_returns_zero(app_config, stores):
    histories, states = stores
    out = io.StringIO()
    side_effects = [_good_result(ep.url) for ep in app_config.endpoints]

    with patch("routewatch.commands.check_once.check_endpoint", side_effect=side_effects), \
         patch("routewatch.commands.check_once.evaluate_and_notify"):
        failures = run_check_once(app_config, histories, states, out=out, notify=False)

    assert failures == 0


def test_run_check_once_shows_error_message(app_config, stores):
    histories, states = stores
    out = io.StringIO()
    side_effects = [_good_result(app_config.endpoints[0].url), _bad_result(app_config.endpoints[1].url)]

    with patch("routewatch.commands.check_once.check_endpoint", side_effect=side_effects), \
         patch("routewatch.commands.check_once.evaluate_and_notify"):
        run_check_once(app_config, histories, states, out=out, notify=False)

    assert "connection refused" in out.getvalue()


def test_run_check_once_calls_notify_when_enabled(app_config, stores):
    histories, states = stores
    out = io.StringIO()
    side_effects = [_good_result(ep.url) for ep in app_config.endpoints]

    with patch("routewatch.commands.check_once.check_endpoint", side_effect=side_effects) as _mock_check, \
         patch("routewatch.commands.check_once.evaluate_and_notify") as mock_notify:
        run_check_once(app_config, histories, states, out=out, notify=True)

    assert mock_notify.call_count == len(app_config.endpoints)


def test_run_check_once_summary_line_contains_count(app_config, stores):
    histories, states = stores
    out = io.StringIO()
    side_effects = [_good_result(ep.url) for ep in app_config.endpoints]

    with patch("routewatch.commands.check_once.check_endpoint", side_effect=side_effects), \
         patch("routewatch.commands.check_once.evaluate_and_notify"):
        run_check_once(app_config, histories, states, out=out, notify=False)

    assert "2 endpoint(s) checked" in out.getvalue()
