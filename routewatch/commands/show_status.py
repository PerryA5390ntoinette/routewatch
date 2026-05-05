"""show_status command – print a one-shot status summary for every endpoint."""
from __future__ import annotations

import sys
from io import TextIOBase
from typing import Dict

from routewatch.config import AppConfig
from routewatch.history import EndpointHistory, average_response_time_ms, error_rate, latest
from routewatch.monitor import is_healthy

_COL_URL = 40
_COL_STATUS = 10
_COL_RESP = 14
_COL_ERR = 10


def _status_symbol(healthy: bool | None) -> str:
    if healthy is None:
        return "UNKNOWN"
    return "OK" if healthy else "FAIL"


def _format_header() -> str:
    return (
        f"{'ENDPOINT':<{_COL_URL}}"
        f"{'STATUS':<{_COL_STATUS}}"
        f"{'AVG RESP (ms)':<{_COL_RESP}}"
        f"{'ERR RATE':<{_COL_ERR}}"
    )


def _format_row(url: str, history: EndpointHistory) -> str:
    last = latest(history)
    healthy: bool | None = is_healthy(last, history.endpoint) if last is not None else None
    avg = average_response_time_ms(history)
    err = error_rate(history)

    avg_str = f"{avg:.1f}" if avg is not None else "n/a"
    err_str = f"{err * 100:.1f}%" if err is not None else "n/a"

    return (
        f"{url:<{_COL_URL}}"
        f"{_status_symbol(healthy):<{_COL_STATUS}}"
        f"{avg_str:<{_COL_RESP}}"
        f"{err_str:<{_COL_ERR}}"
    )


def run_status(
    config: AppConfig,
    histories: Dict[str, EndpointHistory],
    out: TextIOBase = sys.stdout,  # type: ignore[assignment]
) -> None:
    """Write a formatted status table for all configured endpoints to *out*."""
    separator = "-" * (_COL_URL + _COL_STATUS + _COL_RESP + _COL_ERR)
    out.write(_format_header() + "\n")
    out.write(separator + "\n")
    for ep in config.endpoints:
        history = histories.get(ep.url)
        if history is None:
            continue
        out.write(_format_row(ep.url, history) + "\n")
    out.write(separator + "\n")
