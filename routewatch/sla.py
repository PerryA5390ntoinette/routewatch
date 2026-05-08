"""SLA (Service Level Agreement) tracking for monitored endpoints.

Computes whether an endpoint is meeting its configured SLA target,
expressed as a minimum uptime percentage over a rolling window.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from routewatch.config import EndpointConfig
from routewatch.history import EndpointHistory
from routewatch.uptime import compute_uptime


@dataclass(frozen=True)
class SLAResult:
    url: str
    target_pct: float
    actual_pct: Optional[float]   # None when there is no history
    met: Optional[bool]           # None when actual_pct is None
    sample_count: int


def compute_sla(endpoint: EndpointConfig, history: EndpointHistory) -> SLAResult:
    """Return an SLAResult for *endpoint* based on its current *history*."""
    target = getattr(endpoint, "sla_target_pct", 99.9)

    stats = compute_uptime(history)
    if stats.total_checks == 0:
        return SLAResult(
            url=endpoint.url,
            target_pct=target,
            actual_pct=None,
            met=None,
            sample_count=0,
        )

    actual = stats.uptime_pct
    return SLAResult(
        url=endpoint.url,
        target_pct=target,
        actual_pct=actual,
        met=actual >= target,
        sample_count=stats.total_checks,
    )


def compute_all(
    endpoints: list[EndpointConfig],
    histories: dict[str, EndpointHistory],
) -> list[SLAResult]:
    """Return SLA results for every endpoint in *endpoints*."""
    return [compute_sla(ep, histories[ep.url]) for ep in endpoints if ep.url in histories]
