"""Tests for routewatch.alerting module."""

import pytest
import respx
import httpx

from routewatch.alerting import build_payload, send_alert
from routewatch.config import AlertConfig
from routewatch.monitor import CheckResult

WEBHOOK_URL = "https://hooks.example.com/alert"


@pytest.fixture
def alert_config():
    return AlertConfig(
        webhook_url=WEBHOOK_URL,
        max_response_time_ms=500,
        expected_status_codes=[200, 201],
        webhook_secret="secret-token",
        retry_attempts=2,
        retry_delay_seconds=0,
    )


@pytest.fixture
def failed_result():
    return CheckResult(
        url="https://api.example.com/health",
        status_code=503,
        response_time_ms=1200.5,
        error=None,
        timestamp="2024-01-15T10:00:00Z",
    )


def test_build_payload_contains_endpoint(failed_result, alert_config):
    payload = build_payload(failed_result, alert_config)
    assert payload["alert"]["endpoint"] == failed_result.url
    assert payload["alert"]["status"] == "unhealthy"
    assert payload["alert"]["status_code"] == 503
    assert payload["alert"]["response_time_ms"] == 1200.5
    assert payload["thresholds"]["max_response_time_ms"] == 500


def test_build_payload_null_response_time(alert_config):
    result = CheckResult(
        url="https://api.example.com/health",
        status_code=None,
        response_time_ms=None,
        error="Connection refused",
        timestamp="2024-01-15T10:00:00Z",
    )
    payload = build_payload(result, alert_config)
    assert payload["alert"]["response_time_ms"] is None
    assert payload["alert"]["error"] == "Connection refused"


@respx.mock
def test_send_alert_success(failed_result, alert_config):
    respx.post(WEBHOOK_URL).mock(return_value=httpx.Response(200))
    result = send_alert(failed_result, alert_config)
    assert result is True


@respx.mock
def test_send_alert_includes_secret_header(failed_result, alert_config):
    route = respx.post(WEBHOOK_URL).mock(return_value=httpx.Response(200))
    send_alert(failed_result, alert_config)
    assert route.called
    request = route.calls[0].request
    assert request.headers["X-RouteWatch-Secret"] == "secret-token"


@respx.mock
def test_send_alert_retries_on_failure(failed_result, alert_config):
    respx.post(WEBHOOK_URL).mock(
        side_effect=[httpx.Response(500), httpx.Response(200)]
    )
    result = send_alert(failed_result, alert_config)
    assert result is True


@respx.mock
def test_send_alert_returns_false_after_all_retries(failed_result, alert_config):
    respx.post(WEBHOOK_URL).mock(return_value=httpx.Response(500))
    result = send_alert(failed_result, alert_config)
    assert result is False
