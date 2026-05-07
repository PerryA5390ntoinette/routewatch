"""Tests for routewatch/commands/show_trending.py."""

from __future__ import annotations

import io
from datetime import datetime, timezone
from typing import Dict

import pytest

from routewatch.commands.show_trending import run_trending
from routewatch.config import AlertConfig, AppConfig, EndpointConfig
from routewatch.history import EndpointHistory, record
from routewatch.monitor import CheckResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_result(url: str, response_time_ms: float, offset_s: float = 0.0) -> CheckResult:
    return CheckResult(
        url=url,
        status_code=200,
        response_time_ms=response_time_ms,
        error=None,
        timestamp=datetime(2024, 1, 1, 12, 0, int(offset_s), tzinfo=timezone.utc),
    )


@pytest.fixture()
def app_config() -> AppConfig:
    return AppConfig(
        endpoints=[
            EndpointConfig(url="https://api.example.com/health", interval_seconds=30),
            EndpointConfig(url="https://api.example.com/ready", interval_seconds=30),
        ],
        alert=AlertConfig(webhook_url="https://hooks.example.com", threshold_ms=500),
    )


@pytest.fixture()
def histories(app_config: AppConfig) -> Dict[str, EndpointHistory]:
    h: Dict[str, EndpointHistory] = {}
    for ep in app_config.endpoints:
        h[ep.url] = EndpointHistory(max_size=50)

    # Rising trend for first endpoint
    for i in range(10):
        record(h["https://api.example.com/health"], _make_result("https://api.example.com/health", 100.0 + i * 20, float(i * 10)))

    # Flat trend for second endpoint
    for i in range(10):
        record(h["https://api.example.com/ready"], _make_result("https://api.example.com/ready", 200.0, float(i * 10)))

    return h


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_run_trending_writes_output(app_config, histories):
    out = io.StringIO()
    run_trending(app_config, histories, out)
    assert len(out.getvalue()) > 0


def test_run_trending_contains_endpoint_url(app_config, histories):
    out = io.StringIO()
    run_trending(app_config, histories, out)
    assert "https://api.example.com/health" in out.getvalue()


def test_run_trending_contains_header(app_config, histories):
    out = io.StringIO()
    run_trending(app_config, histories, out)
    assert "Endpoint" in out.getvalue()
    assert "Slope" in out.getvalue()


def test_run_trending_rising_verdict(app_config, histories):
    out = io.StringIO()
    run_trending(app_config, histories, out)
    assert "degrading" in out.getvalue()


def test_run_trending_flat_verdict(app_config, histories):
    out = io.StringIO()
    run_trending(app_config, histories, out)
    assert "stable" in out.getvalue()


def test_run_trending_empty_history(app_config):
    empty: Dict[str, EndpointHistory] = {
        ep.url: EndpointHistory(max_size=50) for ep in app_config.endpoints
    }
    out = io.StringIO()
    run_trending(app_config, empty, out)
    assert "insufficient data" in out.getvalue()


def test_run_trending_row_count(app_config, histories):
    out = io.StringIO()
    run_trending(app_config, histories, out)
    lines = [l for l in out.getvalue().splitlines() if l.strip() and not set(l.strip()) <= set("-")]
    # header + 2 endpoint rows
    assert len(lines) >= 3
