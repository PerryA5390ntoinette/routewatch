"""Tests for routewatch.exporter."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from routewatch.exporter import dump_json, export_all, export_history
from routewatch.history import EndpointHistory, record
from routewatch.monitor import CheckResult


TS = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


def make_result(endpoint: str, status_code: int = 200, response_time_ms: float = 120.0, error: str | None = None) -> CheckResult:
    return CheckResult(
        endpoint=endpoint,
        status_code=status_code,
        response_time_ms=response_time_ms,
        error=error,
        timestamp=TS,
    )


@pytest.fixture()
def populated_history() -> EndpointHistory:
    h = EndpointHistory(endpoint="https://example.com/health", capacity=10)
    record(h, make_result("https://example.com/health", 200, 100.0))
    record(h, make_result("https://example.com/health", 200, 200.0))
    record(h, make_result("https://example.com/health", 500, None, "timeout"))
    return h


def test_export_history_fields(populated_history: EndpointHistory) -> None:
    data = export_history(populated_history)
    assert data["endpoint"] == "https://example.com/health"
    assert data["total_checks"] == 3
    assert data["capacity"] == 10
    assert isinstance(data["average_response_time_ms"], float)
    assert isinstance(data["error_rate"], float)


def test_export_history_error_rate(populated_history: EndpointHistory) -> None:
    data = export_history(populated_history)
    assert pytest.approx(data["error_rate"], abs=0.01) == 1 / 3


def test_export_history_latest_is_last_recorded(populated_history: EndpointHistory) -> None:
    data = export_history(populated_history)
    assert data["latest"] is not None
    assert data["latest"]["error"] == "timeout"


def test_export_history_empty() -> None:
    h = EndpointHistory(endpoint="https://empty.example.com", capacity=5)
    data = export_history(h)
    assert data["total_checks"] == 0
    assert data["latest"] is None
    assert data["average_response_time_ms"] is None


def test_export_all_structure(populated_history: EndpointHistory) -> None:
    histories = {populated_history.endpoint: populated_history}
    report = export_all(histories)
    assert report["endpoint_count"] == 1
    assert "generated_at" in report
    assert len(report["endpoints"]) == 1


def test_dump_json_is_valid_json(populated_history: EndpointHistory) -> None:
    histories = {populated_history.endpoint: populated_history}
    output = dump_json(histories)
    parsed = json.loads(output)
    assert parsed["endpoint_count"] == 1


def test_dump_json_timestamp_is_iso(populated_history: EndpointHistory) -> None:
    histories = {populated_history.endpoint: populated_history}
    output = dump_json(histories)
    parsed = json.loads(output)
    latest_ts = parsed["endpoints"][0]["latest"]["timestamp"]
    assert latest_ts == TS.isoformat()
