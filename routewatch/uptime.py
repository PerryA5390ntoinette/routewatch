"""Uptime tracking: computes uptime percentage and downtime windows from history."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

from routewatch.history import EndpointHistory, all_results
from routewatch.monitor import CheckResult, is_healthy


@dataclass
class DowntimeWindow:
    started_at: datetime
    ended_at: Optional[datetime]  # None means still ongoing

    @property
    def duration_seconds(self) -> Optional[float]:
        if self.ended_at is None:
            return None
        return (self.ended_at - self.started_at).total_seconds()


@dataclass
class UptimeStats:
    endpoint_url: str
    total_checks: int
    healthy_checks: int
    uptime_pct: float
    downtime_windows: List[DowntimeWindow] = field(default_factory=list)


def compute_uptime(history: EndpointHistory) -> UptimeStats:
    """Compute uptime statistics from an endpoint's history."""
    results: List[CheckResult] = list(all_results(history))
    if not results:
        return UptimeStats(
            endpoint_url=history.endpoint_url,
            total_checks=0,
            healthy_checks=0,
            uptime_pct=100.0,
            downtime_windows=[],
        )

    healthy_count = sum(1 for r in results if is_healthy(r))
    total = len(results)
    uptime_pct = (healthy_count / total) * 100.0

    windows = _extract_downtime_windows(results)
    return UptimeStats(
        endpoint_url=history.endpoint_url,
        total_checks=total,
        healthy_checks=healthy_count,
        uptime_pct=round(uptime_pct, 2),
        downtime_windows=windows,
    )


def _extract_downtime_windows(results: List[CheckResult]) -> List[DowntimeWindow]:
    """Walk results in chronological order and group consecutive failures."""
    sorted_results = sorted(results, key=lambda r: r.checked_at)
    windows: List[DowntimeWindow] = []
    window_start: Optional[datetime] = None

    for result in sorted_results:
        healthy = is_healthy(result)
        if not healthy and window_start is None:
            window_start = result.checked_at
        elif healthy and window_start is not None:
            windows.append(DowntimeWindow(started_at=window_start, ended_at=result.checked_at))
            window_start = None

    if window_start is not None:
        windows.append(DowntimeWindow(started_at=window_start, ended_at=None))

    return windows


def compute_all(histories: dict) -> dict[str, UptimeStats]:
    """Compute uptime stats for all endpoints keyed by URL."""
    return {url: compute_uptime(h) for url, h in histories.items()}
