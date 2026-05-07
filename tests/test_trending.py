"""Tests for routewatch.trending and routewatch.commands.show_trending."""

from __future__ import annotations

import datetime
from io import StringIO
from unittest.mock import MagicMock

import pytest

from routewatch.history import EndpointHistory, record
from routewatch.monitor import CheckResult
from routewatch.trending import (
    TrendStats,
    _slope,
    compute_all,
    compute_trend,
)
from routewatch.commands.show_trending import run_trending


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _make_result(url: str, ms: float | None, healthy: bool = True) -> CheckResult:
    return CheckResult(
        endpoint_url=url,
        status_code=200 if healthy else 0,
        response_time_ms=ms,
        error=None if healthy else "timeout",
        checked_at=datetime.datetime.utcnow(),
    )


def _history_with_times(url: str, times: list[float | None]) -> EndpointHistory:
    h = EndpointHistory(url=url, max_size=50)
    for t in times:
        record(h, _make_result(url, t))
    return h


# ---------------------------------------------------------------------------
# _slope
# ---------------------------------------------------------------------------

def test_slope_flat():
    assert _slope([100.0, 100.0, 100.0]) == pytest.approx(0.0)


def test_slope_increasing():
    assert _slope([10.0, 20.0, 30.0]) > 0


def test_slope_decreasing():
    assert _slope([30.0, 20.0, 10.0]) < 0


def test_slope_single_element():
    assert _slope([42.0]) == 0.0


# ---------------------------------------------------------------------------
# compute_trend
# ---------------------------------------------------------------------------

def test_compute_trend_stable():
    h = _history_with_times("http://a.test", [100.0, 102.0, 101.0, 99.0])
    stat = compute_trend(h, "http://a.test")
    assert stat.direction == "stable"
    assert stat.sample_count == 4


def test_compute_trend_degrading():
    # large upward slope
    h = _history_with_times("http://b.test", [50.0, 80.0, 110.0, 140.0, 170.0])
    stat = compute_trend(h, "http://b.test")
    assert stat.direction == "degrading"
    assert stat.slope_ms_per_check is not None and stat.slope_ms_per_check > 0


def test_compute_trend_improving():
    h = _history_with_times("http://c.test", [200.0, 160.0, 120.0, 80.0, 40.0])
    stat = compute_trend(h, "http://c.test")
    assert stat.direction == "improving"


def test_compute_trend_insufficient_data():
    h = _history_with_times("http://d.test", [150.0])
    stat = compute_trend(h, "http://d.test")
    assert stat.slope_ms_per_check is None
    assert stat.direction == "stable"
    assert stat.sample_count == 1


def test_compute_trend_skips_none_times():
    h = _history_with_times("http://e.test", [None, None, None])
    stat = compute_trend(h, "http://e.test")
    assert stat.sample_count == 0
    assert stat.slope_ms_per_check is None


# ---------------------------------------------------------------------------
# compute_all
# ---------------------------------------------------------------------------

def test_compute_all_returns_entry_per_url():
    histories = {
        "http://x.test": _history_with_times("http://x.test", [100.0, 110.0]),
        "http://y.test": _history_with_times("http://y.test", [200.0, 190.0]),
    }
    result = compute_all(histories)
    assert set(result.keys()) == {"http://x.test", "http://y.test"}
    assert isinstance(result["http://x.test"], TrendStats)


# ---------------------------------------------------------------------------
# run_trending (command)
# ---------------------------------------------------------------------------

@pytest.fixture()
def app_config():
    cfg = MagicMock()
    cfg.endpoints_by_url.return_value = ["http://svc.test"]
    return cfg


@pytest.fixture()
def histories():
    return {
        "http://svc.test": _history_with_times(
            "http://svc.test", [100.0, 120.0, 140.0, 160.0, 180.0]
        )
    }


def test_run_trending_writes_output(app_config, histories):
    out = StringIO()
    run_trending(app_config, histories, out=out)
    assert len(out.getvalue()) > 0


def test_run_trending_contains_endpoint_url(app_config, histories):
    out = StringIO()
    run_trending(app_config, histories, out=out)
    assert "http://svc.test" in out.getvalue()


def test_run_trending_contains_direction(app_config, histories):
    out = StringIO()
    run_trending(app_config, histories, out=out)
    assert "degrading" in out.getvalue()


def test_run_trending_header_present(app_config, histories):
    out = StringIO()
    run_trending(app_config, histories, out=out)
    assert "Endpoint" in out.getvalue()
    assert "Trend" in out.getvalue()
