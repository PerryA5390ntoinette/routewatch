"""Endpoint health scoring: produces a 0-100 score from history data."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from routewatch.history import EndpointHistory, average_response_time_ms, error_rate
from routewatch.config import EndpointConfig

# Weights must sum to 1.0
_W_ERROR_RATE = 0.50
_W_RESPONSE_TIME = 0.30
_W_AVAILABILITY = 0.20


@dataclass(frozen=True)
class HealthScore:
    endpoint_url: str
    score: float          # 0.0 – 100.0; higher is better
    error_rate_pct: float
    avg_response_ms: Optional[float]
    sample_count: int
    grade: str            # A / B / C / D / F


def _grade(score: float) -> str:
    if score >= 90:
        return "A"
    if score >= 75:
        return "B"
    if score >= 60:
        return "C"
    if score >= 40:
        return "D"
    return "F"


def _response_time_score(avg_ms: Optional[float], threshold_ms: float) -> float:
    """Returns 0-100 based on how avg_ms compares to the configured threshold."""
    if avg_ms is None:
        return 0.0
    if avg_ms <= 0:
        return 100.0
    ratio = avg_ms / threshold_ms
    if ratio <= 1.0:
        return 100.0
    # Linearly degrade: at 2× threshold → 50 pts; at 4× threshold → 0 pts
    score = max(0.0, 100.0 - (ratio - 1.0) * 33.3)
    return round(score, 2)


def compute_score(cfg: EndpointConfig, history: EndpointHistory) -> HealthScore:
    """Compute a composite health score for a single endpoint."""
    from routewatch.history import latest as _latest

    samples = history.results
    n = len(samples)

    err_rate = error_rate(history)          # 0.0 – 1.0
    avg_ms = average_response_time_ms(history)
    threshold = cfg.response_time_limit_ms

    error_component = (1.0 - err_rate) * 100.0
    rt_component = _response_time_score(avg_ms, threshold)
    # Availability: 100 if we have samples, degrades only if history is empty
    availability_component = 100.0 if n > 0 else 0.0

    raw = (
        _W_ERROR_RATE * error_component
        + _W_RESPONSE_TIME * rt_component
        + _W_AVAILABILITY * availability_component
    )
    score = round(min(100.0, max(0.0, raw)), 2)

    return HealthScore(
        endpoint_url=cfg.url,
        score=score,
        error_rate_pct=round(err_rate * 100.0, 2),
        avg_response_ms=avg_ms,
        sample_count=n,
        grade=_grade(score),
    )


def compute_all(
    configs: list[EndpointConfig],
    histories: dict[str, EndpointHistory],
) -> list[HealthScore]:
    return [compute_score(cfg, histories[cfg.url]) for cfg in configs if cfg.url in histories]
