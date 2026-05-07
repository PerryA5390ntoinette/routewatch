"""Baseline response-time tracking.

Captures a rolling baseline (median) for each endpoint so that the
notifier can fire "slower than usual" alerts even when the absolute
threshold has not been crossed.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from typing import List, Optional

from routewatch.history import EndpointHistory


@dataclass
class BaselineStats:
    url: str
    sample_count: int
    median_ms: Optional[float]
    p95_ms: Optional[float]


def _response_times(history: EndpointHistory) -> List[float]:
    """Return all non-None response times from *history* in recorded order."""
    return [
        r.response_time_ms
        for r in history.results
        if r.response_time_ms is not None
    ]


def compute_baseline(history: EndpointHistory) -> BaselineStats:
    """Compute median and p95 from the available history window."""
    times = _response_times(history)
    if not times:
        return BaselineStats(
            url=history.url,
            sample_count=0,
            median_ms=None,
            p95_ms=None,
        )

    sorted_times = sorted(times)
    median = statistics.median(sorted_times)
    idx = max(int(len(sorted_times) * 0.95) - 1, 0)
    p95 = sorted_times[idx]

    return BaselineStats(
        url=history.url,
        sample_count=len(times),
        median_ms=round(median, 2),
        p95_ms=round(p95, 2),
    )


def is_slower_than_baseline(
    response_time_ms: float,
    baseline: BaselineStats,
    multiplier: float = 2.0,
) -> bool:
    """Return True when *response_time_ms* exceeds *multiplier* × baseline median.

    Returns False when there is no baseline yet.
    """
    if baseline.median_ms is None:
        return False
    return response_time_ms > baseline.median_ms * multiplier


def compute_all(
    histories: dict[str, EndpointHistory],
) -> dict[str, BaselineStats]:
    """Convenience wrapper — compute baselines for every endpoint."""
    return {url: compute_baseline(h) for url, h in histories.items()}
