"""Tests for routewatch.commands.show_comparison."""
from __future__ import annotations

import datetime
import io

import pytest

from routewatch.commands.show_comparison import run_comparison
from routewatch.config import AppConfig, EndpointConfig, AlertConfig
from routewatch.history import EndpointHistory, record
from routewatch.monitor import CheckResult


def _make_result(url: str, response_time_ms: float = 120.0, status: int = 200) -> CheckResult:
    return CheckResult(
        url=url,
        status_code=status,
        response_time_ms=response_time_ms,
        error=None,
        timestamp=datetime.datetime.utcnow(),
    )


@pytest.fixture()
def app_config():
    endpoints = [
        EndpointConfig(url="https://alpha.example.com", interval_seconds=30),
        EndpointConfig(url="https://beta.example.com", interval_seconds=30),
    ]
    alert = AlertConfig(webhook_url="https://hooks.example.com", threshold_ms=500)
    return AppConfig(endpoints=endpoints, alert=alert)


@pytest.fixture()
def histories():
    alpha = EndpointHistory(url="https://alpha.example.com", max_size=50)
    for _ in range(3):
        record(alpha, _make_result("https://alpha.example.com", response_time_ms=90.0))

    beta = EndpointHistory(url="https://beta.example.com", max_size=50)
    for _ in range(3):
        record(beta, _make_result("https://beta.example.com", response_time_ms=250.0))

    return {
        "https://alpha.example.com": alpha,
        "https://beta.example.com": beta,
    }


def test_run_comparison_writes_output(app_config, histories):
    out = io.StringIO()
    run_comparison(app_config, histories, out)
    assert len(out.getvalue()) > 0


def test_run_comparison_contains_header(app_config, histories):
    out = io.StringIO()
    run_comparison(app_config, histories, out)
    assert "Endpoint Comparison" in out.getvalue()


def test_run_comparison_contains_endpoint_url(app_config, histories):
    out = io.StringIO()
    run_comparison(app_config, histories, out)
    assert "https://alpha.example.com" in out.getvalue()


def test_run_comparison_contains_rank_column(app_config, histories):
    out = io.StringIO()
    run_comparison(app_config, histories, out)
    assert "Rank" in out.getvalue()


def test_run_comparison_both_endpoints_present(app_config, histories):
    out = io.StringIO()
    run_comparison(app_config, histories, out)
    text = out.getvalue()
    assert "https://alpha.example.com" in text
    assert "https://beta.example.com" in text


def test_run_comparison_empty_histories(app_config):
    out = io.StringIO()
    run_comparison(app_config, {}, out)
    # Should still write header without crashing
    assert "Endpoint Comparison" in out.getvalue()
