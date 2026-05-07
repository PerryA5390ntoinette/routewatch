"""CLI command: display uptime summary table for all monitored endpoints."""
from __future__ import annotations

import io
from typing import Dict

from routewatch.config import AppConfig
from routewatch.history import EndpointHistory
from routewatch.uptime import compute_all, UptimeStats, DowntimeWindow

_COL_URL = 40
_COL_CHECKS = 8
_COL_UPTIME = 10
_COL_WINDOWS = 10


def _fmt_pct(pct: float) -> str:
    return f"{pct:.2f}%"


def _fmt_window(w: DowntimeWindow) -> str:
    end = w.ended_at.strftime("%H:%M:%S") if w.ended_at else "ongoing"
    return f"{w.started_at.strftime('%H:%M:%S')}–{end}"


def _format_header() -> str:
    return (
        f"{'ENDPOINT':<{_COL_URL}}"
        f"{'CHECKS':>{_COL_CHECKS}}"
        f"{'UPTIME':>{_COL_UPTIME}}"
        f"{'OUTAGES':>{_COL_WINDOWS}}"
    )


def _format_row(stats: UptimeStats) -> str:
    url = stats.endpoint_url[:_COL_URL - 1].ljust(_COL_URL)
    checks = str(stats.total_checks).rjust(_COL_CHECKS)
    uptime = _fmt_pct(stats.uptime_pct).rjust(_COL_UPTIME)
    outages = str(len(stats.downtime_windows)).rjust(_COL_WINDOWS)
    return f"{url}{checks}{uptime}{outages}"


def run_uptime(
    config: AppConfig,
    histories: Dict[str, EndpointHistory],
    out: io.TextIOBase = None,
) -> None:
    import sys
    if out is None:  # pragma: no cover
        out = sys.stdout

    all_stats = compute_all(histories)

    header = _format_header()
    separator = "-" * len(header)
    out.write(header + "\n")
    out.write(separator + "\n")

    for endpoint in config.endpoints:
        stats = all_stats.get(endpoint.url)
        if stats is None:
            continue
        out.write(_format_row(stats) + "\n")
        for window in stats.downtime_windows:
            out.write(f"  {'':>{_COL_URL - 2}}  {_fmt_window(window)}\n")
