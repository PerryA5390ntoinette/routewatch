"""Exports monitoring data to JSON for external consumption or persistence."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from routewatch.history import EndpointHistory, average_response_time_ms, error_rate, latest
from routewatch.reporter import summarise


def _serialise_result(result: Any) -> dict:
    """Convert a CheckResult to a JSON-serialisable dict."""
    return {
        "endpoint": result.endpoint,
        "status_code": result.status_code,
        "response_time_ms": result.response_time_ms,
        "error": result.error,
        "timestamp": result.timestamp.isoformat() if result.timestamp else None,
    }


def export_history(history: EndpointHistory) -> dict:
    """Export a single endpoint's history to a serialisable dict."""
    last = latest(history)
    return {
        "endpoint": history.endpoint,
        "capacity": history.capacity,
        "total_checks": len(history.results),
        "average_response_time_ms": average_response_time_ms(history),
        "error_rate": error_rate(history),
        "latest": _serialise_result(last) if last else None,
    }


def export_all(histories: dict[str, EndpointHistory]) -> dict:
    """Export all endpoint histories to a JSON-serialisable report dict."""
    generated_at = datetime.now(timezone.utc).isoformat()
    endpoints = [
        export_history(h) for h in histories.values()
    ]
    return {
        "generated_at": generated_at,
        "endpoint_count": len(endpoints),
        "endpoints": endpoints,
    }


def dump_json(histories: dict[str, EndpointHistory], indent: int = 2) -> str:
    """Serialise all histories to a JSON string."""
    return json.dumps(export_all(histories), indent=indent)
