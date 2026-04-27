"""Tests for routewatch.dashboard."""

from __future__ import annotations

import pytest

from routewatch.dashboard import (
    DashboardRow,
    _STATUS_DOWN,
    _STATUS_OK,
    _STATUS_SLOW,
    build_dashboard_rows,
    render_dashboard,
)
from routewatch.history import EndpointHistory, record
from routewatch.monitor import CheckResult


def _make_result(
    url: str = "http://example.com",
    status_code: int = 200,
    response_time_ms: float | None = 120.0,
    error: str | None = None,
) -> CheckResult:
    return CheckResult(
        url=url,
        status_code=status_code,
        response_time_ms=response_time_ms,
        error=error,
    )


@pytest.fixture()
def histories() -> dict[str, EndpointHistory]:
    h_ok = EndpointHistory(url="http://ok.example.com", maxlen=10)
    record(h_ok, _make_result(url="http://ok.example.com", response_time_ms=100.0))
    record(h_ok, _make_result(url="http://ok.example.com", response_time_ms=200.0))

    h_slow = EndpointHistory(url="http://slow.example.com", maxlen=10)
    record(h_slow, _make_result(url="http://slow.example.com", response_time_ms=1500.0))

    h_down = EndpointHistory(url="http://down.example.com", maxlen=10)
    record(
        h_down,
        _make_result(
            url="http://down.example.com",
            status_code=500,
            response_time_ms=None,
            error="connection refused",
        ),
    )

    return {"ok": h_ok, "slow": h_slow, "down": h_down}


def test_build_dashboard_rows_count(histories):
    rows = build_dashboard_rows(histories)
    assert len(rows) == 3


def test_ok_endpoint_status(histories):
    rows = build_dashboard_rows(histories)
    ok_row = next(r for r in rows if r.name == "ok")
    assert ok_row.status == _STATUS_OK


def test_slow_endpoint_status(histories):
    rows = build_dashboard_rows(histories, slow_threshold_ms=500.0)
    slow_row = next(r for r in rows if r.name == "slow")
    assert slow_row.status == _STATUS_SLOW


def test_down_endpoint_status(histories):
    rows = build_dashboard_rows(histories)
    down_row = next(r for r in rows if r.name == "down")
    assert down_row.status == _STATUS_DOWN


def test_avg_ms_formatted(histories):
    rows = build_dashboard_rows(histories)
    ok_row = next(r for r in rows if r.name == "ok")
    assert "ms" in ok_row.avg_ms
    assert "150.0" in ok_row.avg_ms


def test_empty_history_no_data():
    empty = EndpointHistory(url="http://empty.example.com", maxlen=10)
    rows = build_dashboard_rows({"empty": empty})
    assert rows[0].status == "\u2753 NO DATA"
    assert rows[0].checks == 0


def test_render_dashboard_contains_header(histories):
    rows = build_dashboard_rows(histories)
    output = render_dashboard(rows)
    assert "RouteWatch Dashboard" in output


def test_render_dashboard_contains_endpoint_names(histories):
    rows = build_dashboard_rows(histories)
    output = render_dashboard(rows)
    for name in ("ok", "slow", "down"):
        assert name in output


def test_render_dashboard_returns_string(histories):
    rows = build_dashboard_rows(histories)
    assert isinstance(render_dashboard(rows), str)
