"""Tests for routewatch.notifier."""

from unittest.mock import MagicMock, patch

import pytest

from routewatch.config import AlertConfig, EndpointConfig
from routewatch.history import EndpointHistory, record
from routewatch.monitor import CheckResult
from routewatch.notifier import NotifierState, evaluate_and_notify


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def endpoint_cfg() -> EndpointConfig:
    return EndpointConfig(url="https://example.com/health", interval_seconds=30, timeout_ms=500)


@pytest.fixture()
def alert_cfg() -> AlertConfig:
    return AlertConfig(webhook_url="https://hooks.example.com/alert", error_rate_threshold=0.5)


@pytest.fixture()
def state() -> NotifierState:
    return NotifierState()


def _history_with(*results: CheckResult) -> EndpointHistory:
    h = EndpointHistory(max_size=20)
    for r in results:
        record(h, r)
    return h


def _ok(url: str = "https://example.com/health", rt: float = 100.0) -> CheckResult:
    return CheckResult(url=url, ok=True, status_code=200, response_time_ms=rt, error=None)


def _fail(url: str = "https://example.com/health") -> CheckResult:
    return CheckResult(url=url, ok=False, status_code=503, response_time_ms=None, error="Service Unavailable")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@patch("routewatch.notifier.send_alert")
def test_alert_fires_on_first_failure(mock_send, endpoint_cfg, alert_cfg, state):
    result = _fail()
    history = _history_with(result)
    fired = evaluate_and_notify(result, history, endpoint_cfg, alert_cfg, state)
    assert fired is True
    mock_send.assert_called_once()


@patch("routewatch.notifier.send_alert")
def test_alert_suppressed_on_consecutive_failures(mock_send, endpoint_cfg, alert_cfg, state):
    fail1 = _fail()
    fail2 = _fail()
    history = _history_with(fail1, fail2)
    evaluate_and_notify(fail1, history, endpoint_cfg, alert_cfg, state)
    fired = evaluate_and_notify(fail2, history, endpoint_cfg, alert_cfg, state)
    assert fired is False
    assert mock_send.call_count == 1


@patch("routewatch.notifier.send_alert")
def test_no_alert_for_healthy_endpoint(mock_send, endpoint_cfg, alert_cfg, state):
    result = _ok()
    history = _history_with(result)
    fired = evaluate_and_notify(result, history, endpoint_cfg, alert_cfg, state)
    assert fired is False
    mock_send.assert_not_called()


@patch("routewatch.notifier.send_alert")
def test_alert_fires_for_slow_response(mock_send, endpoint_cfg, alert_cfg, state):
    # timeout_ms is 500; response_time_ms of 800 should trigger alert
    result = _ok(rt=800.0)
    history = _history_with(result)
    fired = evaluate_and_notify(result, history, endpoint_cfg, alert_cfg, state)
    assert fired is True
    mock_send.assert_called_once()


@patch("routewatch.notifier.send_alert")
def test_state_cleared_after_recovery(mock_send, endpoint_cfg, alert_cfg, state):
    fail = _fail()
    ok = _ok()
    history = _history_with(fail)
    evaluate_and_notify(fail, history, endpoint_cfg, alert_cfg, state)
    # Endpoint recovers
    record(history, ok)
    evaluate_and_notify(ok, history, endpoint_cfg, alert_cfg, state)
    # A subsequent failure should fire a new alert
    fail2 = _fail()
    record(history, fail2)
    fired = evaluate_and_notify(fail2, history, endpoint_cfg, alert_cfg, state)
    assert fired is True
    assert mock_send.call_count == 2
