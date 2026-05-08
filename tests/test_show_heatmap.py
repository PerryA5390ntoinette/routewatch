"""Unit tests for routewatch.commands.show_heatmap."""
from __future__ import annotations

from datetime import datetime, timezone
from io import StringIO

import pytest

from routewatch.config import AppConfig, EndpointConfig, AlertConfig
from routewatch.history import EndpointHistory
from routewatch.monitor import CheckResult
from routewatch.commands.show_heatmap import run_heatmap

_URL = "https://example.com/health"


def _make_result(hour: int, ms: float = 150.0) -> CheckResult:
    return CheckResult(
        url=_URL,
        status_code=200,
        response_time_ms=ms,
        checked_at=datetime(2024, 3, 1, hour, 0, 0, tzinfo=timezone.utc),
        error=None,
    )


@pytest.fixture()
def app_config() -> AppConfig:
    ep = EndpointConfig(url=_URL, interval_seconds=30, timeout_seconds=5)
    alert = AlertConfig(webhook_url="https://hooks.example.com", threshold_ms=500)
    return AppConfig(endpoints=[ep], alert=alert)


@pytest.fixture()
def histories() -> dict:
    h = EndpointHistory(url=_URL, max_size=200)
    for hour in range(24):
        h.results.append(_make_result(hour=hour, ms=100.0 + hour * 5))
    return {_URL: h}


def test_run_heatmap_writes_output(app_config, histories):
    out = StringIO()
    run_heatmap(app_config, histories, out=out)
    assert len(out.getvalue()) > 0


def test_run_heatmap_contains_endpoint_url(app_config, histories):
    out = StringIO()
    run_heatmap(app_config, histories, out=out)
    assert _URL in out.getvalue()


def test_run_heatmap_has_24_data_rows(app_config, histories):
    out = StringIO()
    run_heatmap(app_config, histories, out=out)
    lines = out.getvalue().splitlines()
    # header + separator + 24 data rows + separator + footnote
    data_lines = [l for l in lines if l and not l.startswith("-") and "URL" not in l and "peak" not in l]
    assert len(data_lines) == 24


def test_run_heatmap_marks_peak_hour(app_config, histories):
    out = StringIO()
    run_heatmap(app_config, histories, out=out)
    assert " *" in out.getvalue()


def test_run_heatmap_empty_history_no_crash(app_config):
    empty = {_URL: EndpointHistory(url=_URL, max_size=50)}
    out = StringIO()
    run_heatmap(app_config, empty, out=out)
    assert _URL in out.getvalue()
