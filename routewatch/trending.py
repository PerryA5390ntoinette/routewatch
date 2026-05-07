"""Trend analysis for endpoint response times.

Computes a simple linear regression slope over recent response time
samples to classify whether an endpoint's latency is improving,
stable, or degrading.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from routewatch.history import EndpointHistory, average_response_time_ms
from routewatch.monitor import CheckResult


@dataclass
class TrendStats:
    endpoint_url: str
    sample_count: int
    slope_ms_per_check: Optional[float]  # positive = getting slower
    direction: str  # "improving", "stable", "degrading"


_DEGRADING_THRESHOLD = 5.0   # ms per check
_IMPROVING_THRESHOLD = -5.0  # ms per check


def _slope(values: list[float]) -> float:
    """Return the least-squares slope for an evenly-spaced sequence."""
    n = len(values)
    if n < 2:
        return 0.0
    x_mean = (n - 1) / 2.0
    y_mean = sum(values) / n
    numerator = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
    denominator = sum((i - x_mean) ** 2 for i in range(n))
    if denominator == 0.0:
        return 0.0
    return numerator / denominator


def compute_trend(history: EndpointHistory, url: str) -> TrendStats:
    """Compute a TrendStats for *history*."""
    results: list[CheckResult] = list(history)  # newest-last iteration
    times = [
        r.response_time_ms
        for r in results
        if r.response_time_ms is not None
    ]

    if len(times) < 2:
        return TrendStats(
            endpoint_url=url,
            sample_count=len(times),
            slope_ms_per_check=None,
            direction="stable",
        )

    slope = _slope(times)
    if slope >= _DEGRADING_THRESHOLD:
        direction = "degrading"
    elif slope <= _IMPROVING_THRESHOLD:
        direction = "improving"
    else:
        direction = "stable"

    return TrendStats(
        endpoint_url=url,
        sample_count=len(times),
        slope_ms_per_check=round(slope, 3),
        direction=direction,
    )


def compute_all(
    histories: dict[str, EndpointHistory],
) -> dict[str, TrendStats]:
    """Return a TrendStats mapping for every endpoint in *histories*."""
    return {url: compute_trend(h, url) for url, h in histories.items()}
