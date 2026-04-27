"""Tests for routewatch.reporter."""

from __future__ import annotations

import pytest

from routewatch.history import EndpointHistory, record
from routewatch.monitor import CheckResult
from routewatch.reporter import (
    EndpointSummary,
    build_report,
    format_report_text,
    summarise,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def make_result(url: str, healthy: bool, status_code: int = 200, rt_ms: float = 120.0) -> CheckResult:
    return CheckResult(
        url=url,
        healthy=healthy,
        status_code=status_code,
        response_time_ms=rt_ms if healthy else None,
        error=None if healthy else "timeout",
    )


@pytest.fixture()
def history_with_data() -> EndpointHistory:
    h: EndpointHistory = []
    record(h, make_result("https://example.com", True, 200, 100.0))
    record(h, make_result("https://example.com", True, 200, 200.0))
    record(h, make_result("https://example.com", False, 503, None))
    return h


# ---------------------------------------------------------------------------
# summarise
# ---------------------------------------------------------------------------


def test_summarise_healthy_fields(history_with_data: EndpointHistory) -> None:
    s = summarise("https://example.com", history_with_data)
    assert s.url == "https://example.com"
    assert s.last_status_code == 503
    assert s.healthy is False
    assert s.error_rate_pct == pytest.approx(33.33, abs=0.1)


def test_summarise_avg_response_time(history_with_data: EndpointHistory) -> None:
    s = summarise("https://example.com", history_with_data)
    # Only two healthy results have response times: 100 + 200 = avg 150
    assert s.avg_response_time_ms == pytest.approx(150.0)


def test_summarise_empty_history() -> None:
    s = summarise("https://empty.io", [])
    assert s.last_status_code is None
    assert s.last_response_time_ms is None
    assert s.avg_response_time_ms is None
    assert s.error_rate_pct == 0.0
    assert s.healthy is False


# ---------------------------------------------------------------------------
# build_report
# ---------------------------------------------------------------------------


def test_build_report_returns_one_per_endpoint() -> None:
    h1: EndpointHistory = []
    h2: EndpointHistory = []
    record(h1, make_result("https://a.io", True))
    record(h2, make_result("https://b.io", False))
    report = build_report({"https://a.io": h1, "https://b.io": h2})
    assert len(report) == 2
    urls = {s.url for s in report}
    assert urls == {"https://a.io", "https://b.io"}


def test_build_report_empty_histories() -> None:
    assert build_report({}) == []


# ---------------------------------------------------------------------------
# format_report_text
# ---------------------------------------------------------------------------


def test_format_report_text_contains_url(history_with_data: EndpointHistory) -> None:
    summaries = build_report({"https://example.com": history_with_data})
    text = format_report_text(summaries)
    assert "https://example.com" in text
    assert "FAIL" in text


def test_format_report_text_no_endpoints() -> None:
    text = format_report_text([])
    assert "No endpoints" in text
