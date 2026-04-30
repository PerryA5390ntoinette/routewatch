"""Command: print recent check history for each endpoint."""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from typing import Dict, IO

from routewatch.config import AppConfig
from routewatch.history import EndpointHistory


_DATE_FMT = "%Y-%m-%d %H:%M:%S"


def _format_row(index: int, result) -> str:
    """Format a single CheckResult as a table row."""
    ts = datetime.fromtimestamp(result.checked_at, tz=timezone.utc).strftime(_DATE_FMT)
    status = "OK   " if result.is_healthy else "FAIL "
    rt = f"{result.response_time_ms:7.1f} ms" if result.response_time_ms is not None else "    N/A   "
    error = f"  {result.error}" if result.error else ""
    return f"  {index:>3}  {ts}  {status}  {rt}{error}"


def run_history(
    app_config: AppConfig,
    histories: Dict[str, EndpointHistory],
    *,
    limit: int = 10,
    out: IO[str] = sys.stdout,
) -> None:
    """Print the *limit* most-recent results for every configured endpoint."""
    for endpoint in app_config.endpoints:
        url = endpoint.url
        history = histories.get(url)

        out.write(f"\n{'─' * 60}\n")
        out.write(f"  Endpoint : {url}\n")

        if history is None or len(history.results) == 0:
            out.write("  No data recorded yet.\n")
            continue

        results = list(history.results)[-limit:]
        out.write(f"  Showing last {len(results)} of {len(history.results)} check(s)\n")
        out.write(f"  {'#':>3}  {'Timestamp (UTC)':19}  {'Status':5}  {'Response Time'}\n")
        out.write(f"  {'─'*3}  {'─'*19}  {'─'*5}  {'─'*13}\n")

        for i, result in enumerate(results, start=1):
            out.write(_format_row(i, result) + "\n")

    out.write(f"\n{'─' * 60}\n")
