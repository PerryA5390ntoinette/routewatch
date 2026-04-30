"""Tests for routewatch.commands.prune_history."""

from __future__ import annotations

import io
import pytest

from routewatch.config import AppConfig, EndpointConfig, AlertConfig
from routewatch.history import EndpointHistory, record
from routewatch.monitor import CheckResult
from routewatch.commands.prune_history import run_prune


NOW = 1_700_000_000.0


def _endpoint(url: str) -> EndpointConfig:
    return EndpointConfig(url=url, interval_seconds=30, timeout_seconds=5)


def _make_result(url: str, age: float) -> CheckResult:
    return CheckResult(
        url=url,
        status_code=200,
        response_time_ms=40.0,
        error=None,
        checked_at=NOW - age,
    )


@pytest.fixture()
def app_config():
    cfg = AppConfig(
        endpoints=[_endpoint("https://example.com")],
        alert=AlertConfig(webhook_url="https://hooks.example.com", threshold_ms=500),
    )
    cfg.retention_seconds = 120
    return cfg


@pytest.fixture()
def histories():
    h = EndpointHistory(url="https://example.com", max_size=20)
    for age in (300, 60, 10):
        record(h, _make_result("https://example.com", age))
    return {"https://example.com": h}


def test_run_prune_writes_output(app_config, histories):
    out = io.StringIO()
    run_prune(app_config, histories, out=out)
    assert len(out.getvalue()) > 0


def test_run_prune_removes_stale_entries(app_config, histories):
    run_prune(app_config, histories, out=io.StringIO())
    assert len(histories["https://example.com"].results) == 2


def test_run_prune_reports_count(app_config, histories):
    out = io.StringIO()
    run_prune(app_config, histories, out=out)
    assert "1" in out.getvalue()


def test_run_prune_no_policy_skips(histories):
    cfg = AppConfig(
        endpoints=[_endpoint("https://example.com")],
        alert=AlertConfig(webhook_url="https://hooks.example.com", threshold_ms=500),
    )
    out = io.StringIO()
    run_prune(cfg, histories, out=out)
    assert "nothing pruned" in out.getvalue().lower()


def test_run_prune_nothing_removed_message(app_config, histories):
    # Make all entries fresh so nothing is pruned
    h = EndpointHistory(url="https://example.com", max_size=20)
    record(h, _make_result("https://example.com", 5))
    fresh_histories = {"https://example.com": h}
    out = io.StringIO()
    run_prune(app_config, fresh_histories, out=out)
    assert "no entries removed" in out.getvalue().lower()
