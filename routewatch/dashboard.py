"""Simple text-based dashboard renderer for routewatch status overview."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List

from routewatch.history import EndpointHistory
from routewatch.reporter import EndpointSummary, summarise

_STATUS_OK = "\u2705 UP"
_STATUS_SLOW = "\u26a0\ufe0f  SLOW"
_STATUS_DOWN = "\u274c DOWN"
_COL_WIDTH = 28


@dataclass
class DashboardRow:
    name: str
    url: str
    status: str
    avg_ms: str
    error_rate: str
    checks: int


def _status_label(summary: EndpointSummary, slow_threshold_ms: float) -> str:
    if summary.checks == 0:
        return "\u2753 NO DATA"
    if summary.error_rate > 0.0:
        return _STATUS_DOWN
    if summary.avg_response_time_ms is not None and summary.avg_response_time_ms > slow_threshold_ms:
        return _STATUS_SLOW
    return _STATUS_OK


def build_dashboard_rows(
    histories: dict[str, EndpointHistory],
    slow_threshold_ms: float = 1000.0,
) -> List[DashboardRow]:
    rows: List[DashboardRow] = []
    for name, history in histories.items():
        summary = summarise(history)
        avg = (
            f"{summary.avg_response_time_ms:.1f} ms"
            if summary.avg_response_time_ms is not None
            else "n/a"
        )
        rows.append(
            DashboardRow(
                name=name,
                url=summary.url,
                status=_status_label(summary, slow_threshold_ms),
                avg_ms=avg,
                error_rate=f"{summary.error_rate * 100:.1f}%",
                checks=summary.checks,
            )
        )
    return rows


def render_dashboard(rows: List[DashboardRow]) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    header = f"RouteWatch Dashboard  —  {now}\n"
    separator = "-" * 80
    col = f"{{:<{_COL_WIDTH}}}"
    titles = (
        col.format("Endpoint")
        + col.format("Status")
        + "{:<12}".format("Avg RT")
        + "{:<10}".format("Err Rate")
        + "Checks"
    )
    lines = [header, separator, titles, separator]
    for row in rows:
        lines.append(
            col.format(row.name[:_COL_WIDTH - 1])
            + col.format(row.status)
            + "{:<12}".format(row.avg_ms)
            + "{:<10}".format(row.error_rate)
            + str(row.checks)
        )
    lines.append(separator)
    return "\n".join(lines) + "\n"
