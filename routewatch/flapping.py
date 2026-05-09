"""Flapping detection — identifies endpoints that oscillate between healthy and unhealthy states."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from routewatch.history import EndpointHistory
from routewatch.monitor import CheckResult, is_healthy


_MIN_SAMPLES = 4  # need at least this many results to detect flapping


@dataclass(frozen=True)
class FlappingResult:
    url: str
    is_flapping: bool
    transitions: int          # number of healthy<->unhealthy state changes
    sample_count: int
    transition_rate: Optional[float]  # transitions / (sample_count - 1), None if insufficient data
    status: str               # "flapping" | "stable" | "no_data"


def _count_transitions(results: List[CheckResult]) -> int:
    """Count the number of times the health state changes between consecutive results."""
    if len(results) < 2:
        return 0
    transitions = 0
    prev = is_healthy(results[0])
    for result in results[1:]:
        current = is_healthy(result)
        if current != prev:
            transitions += 1
        prev = current
    return transitions


def detect_flapping(
    history: EndpointHistory,
    *,
    threshold: float = 0.4,
    min_samples: int = _MIN_SAMPLES,
) -> FlappingResult:
    """Detect whether an endpoint is flapping.

    Args:
        history: The endpoint's recorded check history.
        threshold: Transition rate (0.0–1.0) above which the endpoint is considered flapping.
                   Defaults to 0.4 (40% of consecutive pairs changed state).
        min_samples: Minimum number of samples required to make a determination.
    """
    from routewatch.history import all_results  # local import to avoid circular issues

    results = all_results(history)
    n = len(results)

    if n < min_samples:
        return FlappingResult(
            url=history.url,
            is_flapping=False,
            transitions=0,
            sample_count=n,
            transition_rate=None,
            status="no_data",
        )

    transitions = _count_transitions(results)
    rate = transitions / (n - 1)
    flapping = rate >= threshold

    return FlappingResult(
        url=history.url,
        is_flapping=flapping,
        transitions=transitions,
        sample_count=n,
        transition_rate=rate,
        status="flapping" if flapping else "stable",
    )


def detect_all(
    histories: dict[str, EndpointHistory],
    *,
    threshold: float = 0.4,
    min_samples: int = _MIN_SAMPLES,
) -> List[FlappingResult]:
    """Run flapping detection across all tracked endpoints."""
    return [
        detect_flapping(h, threshold=threshold, min_samples=min_samples)
        for h in histories.values()
    ]
