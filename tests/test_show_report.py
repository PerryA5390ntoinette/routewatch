"""Tests for routewatch.commands.show_report."""

from __future__ import annotations

import io
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from routewatch.config import AlertConfig, AppConfig, EndpointConfig
from routewatch.history import EndpointHistory, record
from routewatch.monitor import CheckResult
from routewatch.commands.show_report import run_report


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_result(url: str, ok: bool = True, response_ms: float = 120.0) -> CheckResult:
    return CheckResult(
        url=url,
        timestamp=datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc),
        status_code=200 if ok else 500,
        response_time_ms=response_ms if ok else None,
        error=None if ok else "connection error",
    )


@pytest.fixture()
def app_config() -> AppConfig:
    return AppConfig(
        endpoints=[
            EndpointConfig(url="https://example.com/health", interval_seconds=30),
            EndpointConfig(url="https://example.com/api", interval_seconds=60),
        ],
        alert=AlertConfig(webhook_url="https://hooks.example.com/alert"),
    )


@pytest.fixture()
def histories(app_config: AppConfig) -> dict:
    h: dict = {}
    for ep in app_config.endpoints:
        hist = EndpointHistory(max_size=50)
        record(hist, _make_result(ep.url))
        h[ep.url] = hist
    return h


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_run_report_writes_output(app_config, histories):
    buf = io.StringIO()
    run_report(app_config, histories, out=buf)
    output = buf.getvalue()
    assert len(output) > 0


def test_run_report_contains_endpoint_url(app_config, histories):
    buf = io.StringIO()
    run_report(app_config, histories, out=buf)
    output = buf.getvalue()
    assert "https://example.com/health" in output


def test_run_report_ends_with_newline(app_config, histories):
    buf = io.StringIO()
    run_report(app_config, histories, out=buf)
    assert buf.getvalue().endswith("\n")


def test_run_report_defaults_to_stdout(app_config, histories):
    with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
        run_report(app_config, histories)
        output = mock_stdout.getvalue()
    assert "https://example.com/health" in output


def test_run_report_empty_histories(app_config):
    buf = io.StringIO()
    # Pass empty history objects — should not raise.
    empty_histories = {
        ep.url: EndpointHistory(max_size=50) for ep in app_config.endpoints
    }
    run_report(app_config, empty_histories, out=buf)
    assert len(buf.getvalue()) > 0
