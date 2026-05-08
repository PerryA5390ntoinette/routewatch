"""Latency budget tracking: measures how much of an endpoint's allowed
response-time budget has been consumed on average."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from routewatch.config import EndpointConfig
from routewatch.history import EndpointHistory, average_response_time_ms


@dataclass
class BudgetResult:
    url: str
    budget_ms: float
    avg_ms: Optional[float]
    consumed_pct: Optional[float]  # 0–100+
    remaining_ms: Optional[float]
    status: str  # "ok" | "warning" | "exceeded" | "no_data"


_WARNING_THRESHOLD = 80.0  # percent consumed before warning


def compute_budget(endpoint: EndpointConfig, history: EndpointHistory) -> BudgetResult:
    """Compute how much of the latency budget has been consumed."""
    budget_ms = float(endpoint.response_time_threshold_ms)
    avg = average_response_time_ms(history)

    if avg is None:
        return BudgetResult(
            url=endpoint.url,
            budget_ms=budget_ms,
            avg_ms=None,
            consumed_pct=None,
            remaining_ms=None,
            status="no_data",
        )

    consumed_pct = (avg / budget_ms) * 100.0
    remaining_ms = budget_ms - avg

    if consumed_pct > 100.0:
        status = "exceeded"
    elif consumed_pct >= _WARNING_THRESHOLD:
        status = "warning"
    else:
        status = "ok"

    return BudgetResult(
        url=endpoint.url,
        budget_ms=budget_ms,
        avg_ms=round(avg, 2),
        consumed_pct=round(consumed_pct, 2),
        remaining_ms=round(remaining_ms, 2),
        status=status,
    )


def compute_all(
    endpoints: list[EndpointConfig],
    histories: dict[str, EndpointHistory],
) -> list[BudgetResult]:
    """Compute budget results for every configured endpoint."""
    return [compute_budget(ep, histories[ep.url]) for ep in endpoints]
