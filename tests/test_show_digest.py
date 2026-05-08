"""Tests for routewatch.commands.show_digest."""
from __future__ import annotations

import io
from datetime import datetime, timezone

import pytest

from routewatch.config import AppConfig, EndpointConfig, AlertConfig
from routewatch.commands.show_digest import run_digest
from routewatch.history import EndpointHistory
from routewatch.monitor import CheckResult


def _make_result(url: str, ok: bool = True, rt: float = 150.0) -> CheckResult:
    return CheckResult(
        url=url,
        status_code=200 if ok else 0,
        response_time_ms=rt if ok else None,
        error=None if ok else "err",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@pytest.fixture()
def app_config():
    ep = EndpointConfig(
        url="http://alpha.test",
        interval_seconds=60,
        timeout_seconds=5,
        alert=AlertConfig(webhook_url="http://hook", response_time_threshold_ms=500),
    )
    return AppConfig(endpoints=[ep])


@pytest.fixture()
def histories(app_config):
    url = app_config.endpoints[0].url
    h = EndpointHistory(max_size=50)
    h.results.append(_make_result(url, ok=True, rt=100.0))
    h.results.append(_make_result(url, ok=True, rt=200.0))
    return {url: h}


def test_run_digest_writes_output(app_config, histories):
    buf = io.StringIO()
    run_digest(app_config, histories, out=buf)
    assert buf.getvalue().strip() != ""


def test_run_digest_contains_endpoint_url(app_config, histories):
    buf = io.StringIO()
    run_digest(app_config, histories, out=buf)
    assert "http://alpha.test" in buf.getvalue()


def test_run_digest_contains_window_label(app_config, histories):
    buf = io.StringIO()
    run_digest(app_config, histories, window_label="last-24h", out=buf)
    assert "last-24h" in buf.getvalue()


def test_run_digest_shows_grade(app_config, histories):
    buf = io.StringIO()
    run_digest(app_config, histories, out=buf)
    output = buf.getvalue()
    assert any(g in output for g in ("A", "B", "C", "D", "F", "n/a"))


def test_run_digest_empty_histories(app_config):
    buf = io.StringIO()
    run_digest(app_config, {}, out=buf)
    # Should still produce header without crashing
    assert "RouteWatch Digest" in buf.getvalue()
