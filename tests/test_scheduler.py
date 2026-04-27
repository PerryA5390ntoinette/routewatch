"""Tests for the scheduler module."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from routewatch.config import AlertConfig, AppConfig, EndpointConfig
from routewatch.monitor import CheckResult
from routewatch.scheduler import run_check_cycle, start_scheduler


@pytest.fixture()
def app_config() -> AppConfig:
    return AppConfig(
        endpoints=[
            EndpointConfig(url="https://example.com/health", method="GET", timeout_seconds=5),
        ],
        alert=AlertConfig(
            webhook_url="https://hooks.example.com/alert",
            response_time_threshold_ms=500,
        ),
        check_interval_seconds=30,
    )


@pytest.fixture()
def healthy_result() -> CheckResult:
    return CheckResult(
        url="https://example.com/health",
        status_code=200,
        response_time_ms=120.0,
        is_healthy=True,
        error=None,
    )


@pytest.fixture()
def slow_result() -> CheckResult:
    return CheckResult(
        url="https://example.com/health",
        status_code=200,
        response_time_ms=800.0,
        is_healthy=True,
        error=None,
    )


@pytest.mark.asyncio
async def test_run_check_cycle_healthy_no_alert(app_config, healthy_result):
    with patch("routewatch.scheduler.check_endpoint", AsyncMock(return_value=healthy_result)), \
         patch("routewatch.scheduler.send_alert", AsyncMock()) as mock_alert:
        results = await run_check_cycle(app_config)

    assert len(results) == 1
    assert results[0].is_healthy
    mock_alert.assert_not_called()


@pytest.mark.asyncio
async def test_run_check_cycle_slow_triggers_alert(app_config, slow_result):
    with patch("routewatch.scheduler.check_endpoint", AsyncMock(return_value=slow_result)), \
         patch("routewatch.scheduler.send_alert", AsyncMock()) as mock_alert:
        await run_check_cycle(app_config)

    mock_alert.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_check_cycle_calls_on_result_callback(app_config, healthy_result):
    received = []

    async def capture(result):
        received.append(result)

    with patch("routewatch.scheduler.check_endpoint", AsyncMock(return_value=healthy_result)), \
         patch("routewatch.scheduler.send_alert", AsyncMock()):
        await run_check_cycle(app_config, on_result=capture)

    assert len(received) == 1
    assert received[0].url == "https://example.com/health"


@pytest.mark.asyncio
async def test_start_scheduler_stops_on_event(app_config, healthy_result):
    stop = asyncio.Event()

    with patch("routewatch.scheduler.check_endpoint", AsyncMock(return_value=healthy_result)), \
         patch("routewatch.scheduler.send_alert", AsyncMock()), \
         patch("routewatch.scheduler.run_check_cycle", AsyncMock(side_effect=lambda *a, **kw: stop.set())) as mock_cycle:
        await start_scheduler(app_config, stop_event=stop)

    mock_cycle.assert_called_once()
