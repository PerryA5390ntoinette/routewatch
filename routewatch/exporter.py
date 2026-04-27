"""Serialise endpoint histories to JSON for external consumption."""

from __future__ import annotations

import json
from typing import Any, Dict

from routewatch.history import (
    EndpointHistory,
    average_response_time_ms,
    error_rate,
    latest,
)
from routewatch.monitor import CheckResult


def _serialise_result(result: CheckResult) -> Dict[str, Any]:
    """Convert a :class:`CheckResult` to a JSON-serialisable dict."""
    return {
        "url": result.url,
        "timestamp": result.timestamp.isoformat(),
        "status_code": result.status_code,
        "response_time_ms": result.response_time_ms,
        "error": result.error,
    }


def export_history(history: EndpointHistory) -> Dict[str, Any]:
    """Return a summary dict for a single endpoint history."""
    last = latest(history)
    return {
        "url": history.url,
        "sample_count": len(history.results),
        "average_response_time_ms": average_response_time_ms(history),
        "error_rate": error_rate(history),
        "latest": _serialise_result(last) if last is not None else None,
        "results": [_serialise_result(r) for r in history.results],
    }


def export_all(histories: Dict[str, EndpointHistory]) -> Dict[str, Any]:
    """Serialise every tracked endpoint into a single mapping."""
    return {url: export_history(h) for url, h in histories.items()}


def dump_json(
    histories: Dict[str, EndpointHistory],
    indent: int | None = 2,
) -> str:
    """Return a JSON string representing all endpoint histories."""
    return json.dumps(export_all(histories), indent=indent, default=str)
