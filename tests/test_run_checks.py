"""Tests for routewatch/commands/run_checks.py."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call

from routewatch.config import AppConfig, EndpointConfig, AlertConfig
from routewatch.monitor import CheckResult
from routewatch.history import EndpointHistory
from routewatch.notifier import NotifierState
from routewatch.commands.run_checks import run_checks


@pytest.fixture
def app_config():
    return AppConfig(
        endpoints=[
            EndpointConfig(
                name="api",
                url="https://api.example.com/health",
                interval_seconds=30,
                timeout_seconds=5,
                response_time_warn_ms=500,
                response_time_crit_ms=1000,
            ),
            EndpointConfig(
                name="web",
                url="https://web.example.com/",
                interval_seconds=60,
                timeout_seconds=10,
                response_time_warn_ms=800,
                response_time_crit_ms=2000,
            ),
        ],
        alert=AlertConfig(
            webhook_url="https://hooks.example.com/alert",
            cooldown_seconds=300,
        ),
    )


@pytest.fixture
def stores(app_config):
    return {
        ep.url: {
            "history": EndpointHistory(max_size=100),
            "state": NotifierState(),
        }
        for ep in app_config.endpoints
    }


@pytest.fixture
def good_result():
    return CheckResult(
        url="https://api.example.com/health",
        status_code=200,
        response_time_ms=120.0,
        error=None,
    )


@pytest.fixture
def error_result():
    return CheckResult(
        url="https://web.example.com/",
        status_code=None,
        response_time_ms=None,
        error="Connection refused",
    )


def test_run_checks_records_result(app_config, stores, good_result, error_result):
    """run_checks should record each check result into the appropriate history."""
    results = {
        "https://api.example.com/health": good_result,
        "https://web.example.com/": error_result,
    }

    async def fake_check(endpoint, timeout):
        return results[endpoint.url]

    with patch("routewatch.commands.run_checks.check_endpoint", side_effect=fake_check), \
         patch("routewatch.commands.run_checks.evaluate_and_notify"):
        import asyncio
        asyncio.run(run_checks(app_config, stores))

    api_history = stores["https://api.example.com/health"]["history"]
    web_history = stores["https://web.example.com/"]["history"]

    from routewatch.history import latest
    assert latest(api_history) == good_result
    assert latest(web_history) == error_result


def test_run_checks_calls_evaluate_and_notify(app_config, stores, good_result, error_result):
    """run_checks should call evaluate_and_notify for each endpoint after recording."""
    results = {
        "https://api.example.com/health": good_result,
        "https://web.example.com/": error_result,
    }

    async def fake_check(endpoint, timeout):
        return results[endpoint.url]

    with patch("routewatch.commands.run_checks.check_endpoint", side_effect=fake_check) as mock_check, \
         patch("routewatch.commands.run_checks.evaluate_and_notify") as mock_notify:
        import asyncio
        asyncio.run(run_checks(app_config, stores))

    assert mock_notify.call_count == 2


def test_run_checks_passes_correct_state_to_notify(app_config, stores, good_result):
    """evaluate_and_notify should receive the correct state object for each endpoint."""
    results = {
        ep.url: CheckResult(
            url=ep.url,
            status_code=200,
            response_time_ms=100.0,
            error=None,
        )
        for ep in app_config.endpoints
    }

    async def fake_check(endpoint, timeout):
        return results[endpoint.url]

    notify_calls = []

    def capture_notify(endpoint_cfg, alert_cfg, result, history, state):
        notify_calls.append({
            "url": endpoint_cfg.url,
            "state": state,
            "history": history,
        })

    with patch("routewatch.commands.run_checks.check_endpoint", side_effect=fake_check), \
         patch("routewatch.commands.run_checks.evaluate_and_notify", side_effect=capture_notify):
        import asyncio
        asyncio.run(run_checks(app_config, stores))

    urls_notified = {c["url"] for c in notify_calls}
    assert urls_notified == {"https://api.example.com/health", "https://web.example.com/"}

    for c in notify_calls:
        expected_state = stores[c["url"]]["state"]
        expected_history = stores[c["url"]]["history"]
        assert c["state"] is expected_state
        assert c["history"] is expected_history
