"""Anomaly detection: flag results that deviate significantly from baseline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from routewatch.baseline import BaselineStats, compute_baseline
from routewatch.history import EndpointHistory
from routewatch.monitor import CheckResult

# Number of standard deviations above the mean that triggers an anomaly.
_DEFAULT_SIGMA_THRESHOLD = 2.5


@dataclass(frozen=True)
class AnomalyResult:
    url: str
    response_time_ms: Optional[float]
    mean_ms: Optional[float]
    stddev_ms: Optional[float]
    z_score: Optional[float]
    is_anomaly: bool
    reason: str


def _stddev(times: list[float]) -> float:
    if len(times) < 2:
        return 0.0
    mean = sum(times) / len(times)
    variance = sum((t - mean) ** 2 for t in times) / len(times)
    return variance ** 0.5


def detect(
    result: CheckResult,
    history: EndpointHistory,
    sigma_threshold: float = _DEFAULT_SIGMA_THRESHOLD,
) -> AnomalyResult:
    """Return an AnomalyResult for *result* given the endpoint's *history*."""
    baseline: Optional[BaselineStats] = compute_baseline(history)

    if result.response_time_ms is None:
        return AnomalyResult(
            url=result.url,
            response_time_ms=None,
            mean_ms=None,
            stddev_ms=None,
            z_score=None,
            is_anomaly=False,
            reason="no response time (request failed)",
        )

    if baseline is None or baseline.mean_ms is None:
        return AnomalyResult(
            url=result.url,
            response_time_ms=result.response_time_ms,
            mean_ms=None,
            stddev_ms=None,
            z_score=None,
            is_anomaly=False,
            reason="insufficient history for anomaly detection",
        )

    times = [
        r.response_time_ms
        for r in history.results
        if r.response_time_ms is not None
    ]
    stddev = _stddev(times)

    if stddev == 0.0:
        return AnomalyResult(
            url=result.url,
            response_time_ms=result.response_time_ms,
            mean_ms=baseline.mean_ms,
            stddev_ms=0.0,
            z_score=None,
            is_anomaly=False,
            reason="zero variance in history",
        )

    z = (result.response_time_ms - baseline.mean_ms) / stddev
    is_anomaly = z > sigma_threshold

    return AnomalyResult(
        url=result.url,
        response_time_ms=result.response_time_ms,
        mean_ms=baseline.mean_ms,
        stddev_ms=stddev,
        z_score=round(z, 3),
        is_anomaly=is_anomaly,
        reason=f"z={z:.2f} {'exceeds' if is_anomaly else 'within'} threshold {sigma_threshold}",
    )


def detect_all(
    histories: dict[str, EndpointHistory],
    sigma_threshold: float = _DEFAULT_SIGMA_THRESHOLD,
) -> list[AnomalyResult]:
    """Run anomaly detection for the latest result in every history."""
    from routewatch.history import latest as _latest

    results = []
    for url, history in histories.items():
        last = _latest(history)
        if last is not None:
            results.append(detect(last, history, sigma_threshold))
    return results
