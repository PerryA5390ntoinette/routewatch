"""Tests for routewatch.commands.export_snapshot."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from routewatch.commands.export_snapshot import run_export
from routewatch.config import AlertConfig, AppConfig, EndpointConfig
from routewatch.history import EndpointHistory
from routewatch.monitor import CheckResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_result(url: str, ok: bool = True, response_ms: float = 120.0) -> CheckResult:
    return CheckResult(
        url=url,
        timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        status_code=200 if ok else 500,
        response_time_ms=response_ms,
        error=None if ok else "server error",
    )


@pytest.fixture()
def app_config() -> AppConfig:
    return AppConfig(
        endpoints=[
            EndpointConfig(url="https://example.com/health", interval_seconds=30),
        ],
        alert=AlertConfig(webhook_url="https://hooks.example.com/alert"),
    )


@pytest.fixture()
def histories() -> dict:
    url = "https://example.com/health"
    h = EndpointHistory(url=url, max_size=50)
    from routewatch.history import record

    record(h, _make_result(url, ok=True, response_ms=95.0))
    record(h, _make_result(url, ok=True, response_ms=110.0))
    return {url: h}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_run_export_stdout(app_config, histories, capsys):
    run_export(app_config, histories, output_path=None)
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert "https://example.com/health" in data


def test_run_export_stdout_pretty(app_config, histories, capsys):
    run_export(app_config, histories, output_path=None, pretty=True)
    captured = capsys.readouterr()
    # Pretty-printed JSON contains newlines beyond the trailing one
    assert captured.out.count("\n") > 2


def test_run_export_file(app_config, histories, tmp_path):
    dest = tmp_path / "snapshot.json"
    run_export(app_config, histories, output_path=str(dest))
    assert dest.exists()
    data = json.loads(dest.read_text())
    assert "https://example.com/health" in data


def test_run_export_file_creates_parents(app_config, histories, tmp_path):
    dest = tmp_path / "nested" / "dir" / "snapshot.json"
    run_export(app_config, histories, output_path=str(dest))
    assert dest.exists()


def test_run_export_file_prints_confirmation(app_config, histories, tmp_path, capsys):
    dest = tmp_path / "snapshot.json"
    run_export(app_config, histories, output_path=str(dest))
    captured = capsys.readouterr()
    assert "Snapshot written to" in captured.out


def test_run_export_empty_histories(app_config, capsys):
    run_export(app_config, {}, output_path=None)
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data == {}
