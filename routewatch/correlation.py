"""Correlation analysis between endpoint response times.

Computes pairwise Pearson correlation coefficients across endpoints so that
operators can spot endpoints that tend to degrade together — a signal that
they share infrastructure, an upstream dependency, or a common failure mode.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from routewatch.history import EndpointHistory
from routewatch.monitor import CheckResult


@dataclass(frozen=True)
class CorrelationPair:
    """Pearson correlation between two endpoints."""

    endpoint_a: str
    endpoint_b: str
    # None when there are fewer than 2 overlapping samples
    coefficient: Optional[float]
    sample_count: int

    @property
    def strength(self) -> str:
        """Human-readable description of the correlation strength."""
        if self.coefficient is None:
            return "insufficient data"
        r = abs(self.coefficient)
        if r >= 0.9:
            return "very strong"
        if r >= 0.7:
            return "strong"
        if r >= 0.5:
            return "moderate"
        if r >= 0.3:
            return "weak"
        return "negligible"

    @property
    def direction(self) -> str:
        """'positive', 'negative', or 'none'."""
        if self.coefficient is None or abs(self.coefficient) < 0.05:
            return "none"
        return "positive" if self.coefficient > 0 else "negative"


def _response_times(history: EndpointHistory) -> List[Tuple[float, Optional[float]]]:
    """Return (timestamp, response_time_ms) pairs for results that have a
    response time recorded.  Results with no response time are excluded so
    that network errors don't skew the correlation.
    """
    pairs: List[Tuple[float, Optional[float]]] = []
    for result in history.results:
        if result.response_time_ms is not None:
            pairs.append((result.checked_at.timestamp(), result.response_time_ms))
    return pairs


def _pearson(xs: List[float], ys: List[float]) -> Optional[float]:
    """Compute the Pearson correlation coefficient for two equal-length lists.

    Returns None when the standard deviation of either series is zero (constant
    series) or when fewer than 2 samples are provided.
    """
    n = len(xs)
    if n < 2:
        return None

    mean_x = sum(xs) / n
    mean_y = sum(ys) / n

    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    denom_x = math.sqrt(sum((x - mean_x) ** 2 for x in xs))
    denom_y = math.sqrt(sum((y - mean_y) ** 2 for y in ys))

    if denom_x == 0.0 or denom_y == 0.0:
        return None

    return num / (denom_x * denom_y)


def _align_series(
    a: List[Tuple[float, Optional[float]]],
    b: List[Tuple[float, Optional[float]]],
    tolerance_s: float = 5.0,
) -> Tuple[List[float], List[float]]:
    """Match samples from two series by timestamp within *tolerance_s* seconds.

    Uses a greedy nearest-neighbour approach: for each sample in *a* we look
    for the closest unmatched sample in *b*.  This handles slight clock skew
    between check cycles.
    """
    used: set = set()
    xs: List[float] = []
    ys: List[float] = []

    b_sorted = sorted(b, key=lambda t: t[0])

    for ts_a, rt_a in a:
        best_idx: Optional[int] = None
        best_diff = tolerance_s

        for i, (ts_b, rt_b) in enumerate(b_sorted):
            if i in used:
                continue
            diff = abs(ts_a - ts_b)
            if diff <= best_diff:
                best_diff = diff
                best_idx = i

        if best_idx is not None and rt_a is not None:
            _, rt_b = b_sorted[best_idx]
            if rt_b is not None:
                xs.append(rt_a)
                ys.append(rt_b)
                used.add(best_idx)

    return xs, ys


def compute_correlation(
    url_a: str,
    history_a: EndpointHistory,
    url_b: str,
    history_b: EndpointHistory,
    tolerance_s: float = 5.0,
) -> CorrelationPair:
    """Compute the Pearson correlation between two endpoint histories."""
    series_a = _response_times(history_a)
    series_b = _response_times(history_b)

    xs, ys = _align_series(series_a, series_b, tolerance_s=tolerance_s)
    coeff = _pearson(xs, ys)

    return CorrelationPair(
        endpoint_a=url_a,
        endpoint_b=url_b,
        coefficient=coeff,
        sample_count=len(xs),
    )


def compute_all(
    histories: Dict[str, EndpointHistory],
    tolerance_s: float = 5.0,
) -> List[CorrelationPair]:
    """Return all unique endpoint pairs sorted by absolute correlation (descending)."""
    urls = sorted(histories.keys())
    pairs: List[CorrelationPair] = []

    for i in range(len(urls)):
        for j in range(i + 1, len(urls)):
            url_a, url_b = urls[i], urls[j]
            pair = compute_correlation(
                url_a, histories[url_a],
                url_b, histories[url_b],
                tolerance_s=tolerance_s,
            )
            pairs.append(pair)

    pairs.sort(
        key=lambda p: abs(p.coefficient) if p.coefficient is not None else -1.0,
        reverse=True,
    )
    return pairs
