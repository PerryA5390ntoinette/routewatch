"""Tests for routewatch.commands.show_tags."""

from __future__ import annotations

import io
from datetime import datetime, timezone

import pytest

from routewatch.config import AlertConfig, AppConfig, EndpointConfig
from routewatch.history import EndpointHistory
from routewatch.monitor import CheckResult
from routewatch.commands.show_tags import run_tags


def _make_result(url: str, ok: bool = True, ms: float = 120.0) -> CheckResult:
    return CheckResult(
        url=url,
        status_code=200 if ok else 500,
        response_time_ms=ms if ok else None,
        error=None if ok else "err",
        timestamp=datetime.now(timezone.utc),
    )


@pytest.fixture()
def app_config():
    return AppConfig(
        endpoints=[
            EndpointConfig(url="http://api", tags=["prod", "api"]),
            EndpointConfig(url="http://web", tags=["prod"]),
            EndpointConfig(url="http://dev", tags=["staging"]),
            EndpointConfig(url="http://bare"),
        ],
        alert=AlertConfig(webhook_url="http://hook", threshold_ms=500, error_rate_threshold=0.5),
        interval_seconds=30,
        history_size=10,
    )


@pytest.fixture()
def histories(app_config):
    hists = {}
    for ep in app_config.endpoints:
        h = EndpointHistory(max_size=10)
        from routewatch.history import record
        record(h, _make_result(ep.url))
        hists[ep.url] = h
    return hists


def test_run_tags_writes_output(app_config, histories):
    out = io.StringIO()
    run_tags(app_config, histories, out)
    assert len(out.getvalue()) > 0


def test_run_tags_contains_header(app_config, histories):
    out = io.StringIO()
    run_tags(app_config, histories, out)
    assert "TAG" in out.getvalue()
    assert "ENDPOINT" in out.getvalue()


def test_run_tags_shows_all_urls(app_config, histories):
    out = io.StringIO()
    run_tags(app_config, histories, out)
    text = out.getvalue()
    for ep in app_config.endpoints:
        assert ep.url in text


def test_run_tags_filter_tag(app_config, histories):
    out = io.StringIO()
    run_tags(app_config, histories, out, filter_tag="staging")
    text = out.getvalue()
    assert "http://dev" in text
    assert "http://api" not in text
    assert "http://web" not in text


def test_run_tags_untagged_label(app_config, histories):
    out = io.StringIO()
    run_tags(app_config, histories, out)
    assert "(untagged)" in out.getvalue()


def test_run_tags_avg_response_time_shown(app_config, histories):
    out = io.StringIO()
    run_tags(app_config, histories, out)
    # default result has 120.0 ms
    assert "120.0" in out.getvalue()


def test_run_tags_filter_nonexistent_tag(app_config, histories):
    out = io.StringIO()
    run_tags(app_config, histories, out, filter_tag="nope")
    lines = [l for l in out.getvalue().splitlines() if l.strip() and not l.startswith(("TAG", "-"))]
    assert lines == []
