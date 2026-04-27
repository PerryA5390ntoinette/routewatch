"""Summary reporter: formats and emits periodic status reports for all monitored endpoints."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from routewatch.history import EndpointHistory, average_response_time_ms, error_rate, latest


@dataclass
class EndpointSummary:
    url: str
    last_status_code: int | None
    last_response_time_ms: float | None
    avg_response_time_ms: float | None
    error_rate_pct: float
    healthy: bool


def summarise(url: str, history: EndpointHistory) -> EndpointSummary:
    """Build a summary snapshot for a single endpoint from its history."""
    last = latest(history)
    last_status = last.status_code if last else None
    last_rt = last.response_time_ms if last else None
    last_healthy = last.healthy if last else False

    return EndpointSummary(
        url=url,
        last_status_code=last_status,
        last_response_time_ms=last_rt,
        avg_response_time_ms=average_response_time_ms(history),
        error_rate_pct=round(error_rate(history) * 100, 2),
        healthy=last_healthy,
    )


def build_report(histories: dict[str, EndpointHistory]) -> List[EndpointSummary]:
    """Return a list of summaries for every tracked endpoint."""
    return [summarise(url, h) for url, h in histories.items()]


def format_report_text(summaries: List[EndpointSummary]) -> str:
    """Render summaries as a human-readable text block."""
    if not summaries:
        return "No endpoints monitored yet."

    lines = ["RouteWatch Status Report", "=" * 40]
    for s in summaries:
        status_label = "OK" if s.healthy else "FAIL"
        avg = f"{s.avg_response_time_ms:.1f} ms" if s.avg_response_time_ms is not None else "n/a"
        last_rt = f"{s.last_response_time_ms:.1f} ms" if s.last_response_time_ms is not None else "n/a"
        lines.append(
            f"[{status_label}] {s.url}\n"
            f"  Last: {s.last_status_code} in {last_rt} | "
            f"Avg: {avg} | Errors: {s.error_rate_pct}%"
        )
    return "\n".join(lines)
