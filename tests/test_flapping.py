"""Tests for routewatch.flapping and routewatch.commands.show_flapping."""
from __future__ import annotations

import io
from datetime import datetime, timezone

import pytest

from routewatch.config import AlertConfig, EndpointConfig
from routewatch.flapping import FlappingResult, detect_all, detect_flapping
from routewatch.history import EndpointHistory, record
from routewatch.monitor import CheckResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_result(url: str, *, ok: bool, rt: float = 120.0) -> CheckResult:
    return CheckResult(
        url=url,
        status_code=200 if ok else 500,
        response_time_ms=rt if ok else None,
        error=None if ok else "connection error",
        timestamp=datetime.now(timezone.utc),
    )


def _history_with(url: str, pattern: list[bool], max_size: int = 50) -> EndpointHistory:
    """Build an EndpointHistory from a list of booleans (True=healthy, False=unhealthy)."""
    h = EndpointHistory(url=url, max_size=max_size)
    for ok in pattern:
        record(h, _make_result(url, ok=ok))
    return h


# ---------------------------------------------------------------------------
# detect_flapping unit tests
# ---------------------------------------------------------------------------

def test_no_data_when_fewer_than_min_samples():
    h = _history_with("http://a", [True, True])  # only 2 samples, default min=4
    result = detect_flapping(h)
    assert result.status == "no_data"
    assert result.is_flapping is False
    assert result.transition_rate is None


def test_stable_all_healthy():
    h = _history_with("http://a", [True, True, True, True, True])
    result = detect_flapping(h)
    assert result.status == "stable"
    assert result.is_flapping is False
    assert result.transitions == 0
    assert result.transition_rate == pytest.approx(0.0)


def test_stable_all_unhealthy():
    h = _history_with("http://a", [False, False, False, False])
    result = detect_flapping(h)
    assert result.status == "stable"
    assert result.transitions == 0


def test_flapping_alternating():
    # True/False alternating → transitions = 5 out of 5 pairs → rate = 1.0
    h = _history_with("http://a", [True, False, True, False, True, False])
    result = detect_flapping(h)
    assert result.is_flapping is True
    assert result.status == "flapping"
    assert result.transitions == 5
    assert result.transition_rate == pytest.approx(1.0)


def test_flapping_threshold_boundary():
    # 4 samples, 1 transition → rate = 1/3 ≈ 0.333 < 0.4 → stable
    h = _history_with("http://a", [True, True, True, False])
    result = detect_flapping(h, threshold=0.4)
    assert result.status == "stable"

    # same but threshold lowered to 0.3 → flapping
    result2 = detect_flapping(h, threshold=0.3)
    assert result2.status == "flapping"


def test_sample_count_recorded():
    h = _history_with("http://a", [True, False, True, False, True])
    result = detect_flapping(h)
    assert result.sample_count == 5


# ---------------------------------------------------------------------------
# detect_all
# ---------------------------------------------------------------------------

def test_detect_all_returns_entry_per_endpoint():
    histories = {
        "http://a": _history_with("http://a", [True, False, True, False]),
        "http://b": _history_with("http://b", [True, True, True, True]),
    }
    results = detect_all(histories)
    assert len(results) == 2


def test_detect_all_identifies_flapping_correctly():
    histories = {
        "http://flap": _history_with("http://flap", [True, False, True, False, True, False]),
        "http://ok": _history_with("http://ok", [True, True, True, True, True]),
    }
    results = {r.url: r for r in detect_all(histories)}
    assert results["http://flap"].is_flapping is True
    assert results["http://ok"].is_flapping is False


# ---------------------------------------------------------------------------
# show_flapping command
# ---------------------------------------------------------------------------

@pytest.fixture()
def app_config():
    from routewatch.config import AppConfig, AlertConfig
    return AppConfig(
        endpoints=[
            EndpointConfig(url="http://flap", interval_seconds=30),
            EndpointConfig(url="http://ok", interval_seconds=30),
        ],
        alert=AlertConfig(webhook_url="http://hook", response_time_threshold_ms=500),
        history_max_size=50,
    )


@pytest.fixture()
def histories():
    return {
        "http://flap": _history_with("http://flap", [True, False, True, False, True, False]),
        "http://ok": _history_with("http://ok", [True, True, True, True, True]),
    }


def test_run_flapping_writes_output(app_config, histories):
    from routewatch.commands.show_flapping import run_flapping
    buf = io.StringIO()
    run_flapping(app_config, histories, out=buf)
    assert len(buf.getvalue()) > 0


def test_run_flapping_contains_endpoint_url(app_config, histories):
    from routewatch.commands.show_flapping import run_flapping
    buf = io.StringIO()
    run_flapping(app_config, histories, out=buf)
    assert "http://flap" in buf.getvalue()
    assert "http://ok" in buf.getvalue()


def test_run_flapping_shows_flapping_status(app_config, histories):
    from routewatch.commands.show_flapping import run_flapping
    buf = io.StringIO()
    run_flapping(app_config, histories, out=buf)
    assert "flapping" in buf.getvalue()


def test_run_flapping_summary_line(app_config, histories):
    from routewatch.commands.show_flapping import run_flapping
    buf = io.StringIO()
    run_flapping(app_config, histories, out=buf)
    # Should contain a summary line mentioning count
    assert "endpoint(s) currently flapping" in buf.getvalue()
