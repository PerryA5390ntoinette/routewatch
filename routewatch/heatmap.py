"""Hourly response-time heatmap aggregation.

Builds a 24-slot (hour-of-day) summary for a single endpoint so callers
can spot recurring slow periods.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from routewatch.history import EndpointHistory


@dataclass
class HourBucket:
    hour: int  # 0-23
    sample_count: int = 0
    avg_response_ms: Optional[float] = None
    error_count: int = 0


@dataclass
class HeatmapResult:
    url: str
    buckets: List[HourBucket] = field(default_factory=list)  # always 24 entries


def _empty_buckets() -> List[HourBucket]:
    return [HourBucket(hour=h) for h in range(24)]


def compute_heatmap(url: str, history: EndpointHistory) -> HeatmapResult:
    """Aggregate history records into 24 hourly buckets."""
    buckets = _empty_buckets()
    totals: Dict[int, float] = {h: 0.0 for h in range(24)}

    for result in history.results:
        hour = result.checked_at.hour
        bucket = buckets[hour]
        bucket.sample_count += 1
        if result.error is not None:
            bucket.error_count += 1
        if result.response_time_ms is not None:
            totals[hour] += result.response_time_ms

    for bucket in buckets:
        valid = bucket.sample_count - bucket.error_count
        if valid > 0:
            bucket.avg_response_ms = round(totals[bucket.hour] / valid, 2)

    return HeatmapResult(url=url, buckets=buckets)


def compute_all(
    histories: Dict[str, EndpointHistory]
) -> Dict[str, HeatmapResult]:
    """Compute heatmaps for every tracked endpoint."""
    return {url: compute_heatmap(url, hist) for url, hist in histories.items()}


def peak_hour(result: HeatmapResult) -> Optional[int]:
    """Return the hour with the highest average response time, or None."""
    candidates = [
        b for b in result.buckets if b.avg_response_ms is not None
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda b: b.avg_response_ms).hour  # type: ignore[arg-type]
