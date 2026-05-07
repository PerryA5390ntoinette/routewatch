"""Tests for routewatch.scoring and routewatch.commands.show_scoring."""
from __future__ import annotations

import io
from datetime import datetime, timezone

import pytest

from routewatch.config import EndpointConfig, AlertConfig
from routewatch.history import EndpointHistory, record
from routewatch.monitor import CheckResult
from routewatch.scoring import compute_score, compute_all, HealthScore, _grade, _response_time_score
from routewatch.commands.show_scoring import run_scoring


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _ep(url: str = "http://example.com", limit_ms: float = 500.0) -> EndpointConfig:
    return EndpointConfig(url=url, interval_seconds=30, response_time_limit_ms=limit_ms)


def _make_result(url: str, ok: bool, ms: float | None) -> CheckResult:
    return CheckResult(
        url=url,
        status_code=200 if ok else None,
        response_time_ms=ms,
        error=None if ok else "timeout",
        timestamp=datetime.now(timezone.utc),
    )


def _history_with(results: list[CheckResult]) -> EndpointHistory:
    h = EndpointHistory(max_size=100)
    for r in results:
        record(h, r)
    return h


# ---------------------------------------------------------------------------
# _grade
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("score,expected", [
    (95, "A"), (90, "A"),
    (80, "B"), (75, "B"),
    (65, "C"), (60, "C"),
    (50, "D"), (40, "D"),
    (39, "F"), (0, "F"),
])
def test_grade_bands(score, expected):
    assert _grade(score) == expected


# ---------------------------------------------------------------------------
# _response_time_score
# ---------------------------------------------------------------------------

def test_rt_score_below_threshold_is_100():
    assert _response_time_score(200.0, 500.0) == 100.0


def test_rt_score_at_threshold_is_100():
    assert _response_time_score(500.0, 500.0) == 100.0


def test_rt_score_double_threshold_is_degraded():
    score = _response_time_score(1000.0, 500.0)
    assert 40.0 < score < 70.0


def test_rt_score_none_is_zero():
    assert _response_time_score(None, 500.0) == 0.0


# ---------------------------------------------------------------------------
# compute_score
# ---------------------------------------------------------------------------

def test_perfect_score_all_healthy():
    ep = _ep(limit_ms=500.0)
    results = [_make_result(ep.url, True, 100.0) for _ in range(10)]
    h = _history_with(results)
    hs = compute_score(ep, h)
    assert hs.score == 100.0
    assert hs.grade == "A"
    assert hs.error_rate_pct == 0.0


def test_score_degrades_with_errors():
    ep = _ep(limit_ms=500.0)
    results = (
        [_make_result(ep.url, True, 100.0)] * 5
        + [_make_result(ep.url, False, None)] * 5
    )
    h = _history_with(results)
    hs = compute_score(ep, h)
    assert hs.score < 100.0
    assert hs.error_rate_pct == 50.0


def test_score_zero_on_empty_history():
    ep = _ep()
    h = EndpointHistory(max_size=50)
    hs = compute_score(ep, h)
    assert hs.score == 0.0
    assert hs.sample_count == 0
    assert hs.grade == "F"


def test_score_fields_populated():
    ep = _ep(url="http://test.io", limit_ms=300.0)
    h = _history_with([_make_result(ep.url, True, 150.0)] * 4)
    hs = compute_score(ep, h)
    assert hs.endpoint_url == "http://test.io"
    assert hs.avg_response_ms == pytest.approx(150.0)
    assert hs.sample_count == 4


# ---------------------------------------------------------------------------
# compute_all
# ---------------------------------------------------------------------------

def test_compute_all_returns_one_per_endpoint():
    eps = [_ep(f"http://ep{i}.io") for i in range(3)]
    histories = {ep.url: _history_with([_make_result(ep.url, True, 50.0)]) for ep in eps}
    scores = compute_all(eps, histories)
    assert len(scores) == 3


def test_compute_all_skips_missing_history():
    eps = [_ep("http://a.io"), _ep("http://b.io")]
    histories = {"http://a.io": _history_with([_make_result("http://a.io", True, 50.0)])}
    scores = compute_all(eps, histories)
    assert len(scores) == 1


# ---------------------------------------------------------------------------
# run_scoring (command)
# ---------------------------------------------------------------------------

@pytest.fixture
def app_config():
    from routewatch.config import AppConfig, AlertConfig
    eps = [_ep("http://alpha.io"), _ep("http://beta.io")]
    alert = AlertConfig(webhook_url="http://hook", response_time_threshold_ms=500.0)
    return AppConfig(endpoints=eps, alert=alert, history_max_size=50)


@pytest.fixture
def histories(app_config):
    out = {}
    for ep in app_config.endpoints:
        out[ep.url] = _history_with([_make_result(ep.url, True, 120.0)] * 5)
    return out


def test_run_scoring_writes_output(app_config, histories):
    buf = io.StringIO()
    run_scoring(app_config, histories, buf)
    assert len(buf.getvalue()) > 0


def test_run_scoring_contains_endpoint_url(app_config, histories):
    buf = io.StringIO()
    run_scoring(app_config, histories, buf)
    assert "http://alpha.io" in buf.getvalue()


def test_run_scoring_contains_grade(app_config, histories):
    buf = io.StringIO()
    run_scoring(app_config, histories, buf)
    output = buf.getvalue()
    assert any(g in output for g in ("A", "B", "C", "D", "F"))


def test_run_scoring_no_data_message(app_config):
    buf = io.StringIO()
    run_scoring(app_config, {}, buf)
    assert "No data" in buf.getvalue()
