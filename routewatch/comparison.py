"""Compare health metrics across endpoints to surface relative performance."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from routewatch.history import EndpointHistory, average_response_time_ms, error_rate
from routewatch.baseline import compute_baseline


@dataclass
class ComparisonRow:
    url: str
    avg_response_time_ms: Optional[float]
    error_rate_pct: float
    baseline_median_ms: Optional[float]
    rank: int  # 1 = best


def _sort_key(row: ComparisonRow):
    """Primary sort: error rate ascending; secondary: avg response time ascending."""
    rt = row.avg_response_time_ms if row.avg_response_time_ms is not None else float("inf")
    return (row.error_rate_pct, rt)


def compare_endpoints(
    histories: Dict[str, EndpointHistory],
) -> List[ComparisonRow]:
    """Return a ranked list of ComparisonRow, best-performing endpoint first."""
    rows: List[ComparisonRow] = []

    for url, history in histories.items():
        avg_rt = average_response_time_ms(history)
        er = error_rate(history) * 100.0
        baseline = compute_baseline(history)
        median_ms = baseline.median_ms if baseline else None

        rows.append(
            ComparisonRow(
                url=url,
                avg_response_time_ms=avg_rt,
                error_rate_pct=er,
                baseline_median_ms=median_ms,
                rank=0,
            )
        )

    rows.sort(key=_sort_key)
    for i, row in enumerate(rows, start=1):
        row.rank = i

    return rows
