"""Tests for routewatch/commands/run_checks.py."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from routewatch.commands.run_checks import run_checks
from routewatch.config import AlertConfig, AppConfig, EndpointConfig
from routewatch.history import EndpointHistory
from routewatch.monitor import CheckResult
from routewatch.notifier import NotifierState
from routewatch.state_store import build_stores


@pytest.fixture()
def app_config():
    ep = EndpointConfig(url="https://example.com", timeout_s=5.0, slow_threshold_ms=300)
    return AppConfig(
        endpoints=[ep],
        alert=AlertConfig(webhook_url="https://hook.example", cooldown_s=60),
        interval_s=10,
        history_size=50,
    )


@pytest.fixture()
def stores(app_config):
    return build_stores(app_config)


@pytest.fixture()
def good_result():
    return CheckResult(
        url="https://example.com",
        status_code=200,
        response_time_ms=120.0,
        error=None,
    )


def test_run_checks_records_result(app_config, stores, good_result):
    histories, states = stores
    with patch(
        "routewatch.commands.run_checks.check_endpoint",
        new=AsyncMock(return_value=good_result),
    ), patch(
        "routewatch.commands.run_checks.evaluate_and_notify",
        new=AsyncMock(),
    ):
        run_checks(app_config, histories, states)

    from routewatch.history import latest

    assert latest(histories["https://example.com"]) == good_result


def test_run_checks_calls_evaluate_and_notify(app_config, stores, good_result):
    histories, states = stores
    mock_notify = AsyncMock()
    with patch(
        "routewatch.commands.run_checks.check_endpoint",
        new=AsyncMock(return_value=good_result),
    ), patch(
        "routewatch.commands.run_checks.evaluate_and_notify",
        new=mock_notify,
    ):
        run_checks(app_config, histories, states)

    mock_notify.assert_awaited_once()


def test_run_checks_all_endpoints_checked():
    eps = [
        EndpointConfig(url=f"https://ep{i}.example", timeout_s=5.0, slow_threshold_ms=300)
        for i in range(3)
    ]
    cfg = AppConfig(
        endpoints=eps,
        alert=AlertConfig(webhook_url="https://hook.example", cooldown_s=60),
        interval_s=10,
        history_size=50,
    )
    histories, states = build_stores(cfg)

    checked_urls = []

    async def fake_check(ep):
        checked_urls.append(ep.url)
        return CheckResult(url=ep.url, status_code=200, response_time_ms=50.0, error=None)

    with patch(
        "routewatch.commands.run_checks.check_endpoint", new=fake_check
    ), patch(
        "routewatch.commands.run_checks.evaluate_and_notify", new=AsyncMock()
    ):
        run_checks(cfg, histories, states)

    assert sorted(checked_urls) == sorted(ep.url for ep in eps)
