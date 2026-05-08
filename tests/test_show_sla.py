"""Unit tests for routewatch.commands.show_sla."""
from __future__ import annotations

import datetime
import io
from unittest.mock import MagicMock

import pytest

from routewatch.history import EndpointHistory, record
from routewatch.monitor import CheckResult
from routewatch.commands.show_sla import run_sla


def _make_result(url: str, *, ok: bool = True) -> CheckResult:
    return CheckResult(
        url=url,
        status_code=200 if ok else None,
        response_time_ms=100.0 if ok else None,
        error=None if ok else "timeout",
        timestamp=datetime.datetime.utcnow(),
    )


def _endpoint(url: str, sla_target_pct: float = 99.9):
    ep = MagicMock()
    ep.url = url
    ep.sla_target_pct = sla_target_pct
    return ep


@pytest.fixture()
def app_config():
    cfg = MagicMock()
    cfg.endpoints = [
        _endpoint("http://alpha.example.com"),
        _endpoint("http://beta.example.com", sla_target_pct=95.0),
    ]
    return cfg


@pytest.fixture()
def histories(app_config):
    result = {}
    for ep in app_config.endpoints:
        h = EndpointHistory(url=ep.url, max_size=200)
        for _ in range(9):
            record(h, _make_result(ep.url, ok=True))
        record(h, _make_result(ep.url, ok=False))
        result[ep.url] = h
    return result


def test_run_sla_writes_output(app_config, histories):
    out = io.StringIO()
    run_sla(app_config, histories, out=out)
    assert len(out.getvalue()) > 0


def test_run_sla_contains_endpoint_url(app_config, histories):
    out = io.StringIO()
    run_sla(app_config, histories, out=out)
    assert "http://alpha.example.com" in out.getvalue()


def test_run_sla_shows_header(app_config, histories):
    out = io.StringIO()
    run_sla(app_config, histories, out=out)
    text = out.getvalue()
    assert "Target" in text
    assert "Actual" in text


def test_run_sla_shows_summary_line(app_config, histories):
    out = io.StringIO()
    run_sla(app_config, histories, out=out)
    assert "meeting SLA" in out.getvalue()


def test_run_sla_empty_histories(app_config):
    empty = {ep.url: EndpointHistory(url=ep.url, max_size=100) for ep in app_config.endpoints}
    out = io.StringIO()
    run_sla(app_config, empty, out=out)
    assert "n/a" in out.getvalue()


def test_run_sla_no_endpoints():
    cfg = MagicMock()
    cfg.endpoints = []
    out = io.StringIO()
    run_sla(cfg, {}, out=out)
    assert "No endpoint data" in out.getvalue()
