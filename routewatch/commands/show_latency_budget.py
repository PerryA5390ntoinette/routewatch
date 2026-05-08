"""CLI command: display latency budget consumption for all endpoints."""

from __future__ import annotations

import io
from typing import Optional

from routewatch.config import AppConfig
from routewatch.history import EndpointHistory
from routewatch.latency_budget import BudgetResult, compute_all

_HEADER = f"{'ENDPOINT':<40} {'BUDGET':>8} {'AVG':>8} {'CONSUMED':>9} {'REMAINING':>10}  STATUS"
_SEP = "-" * 90

_STATUS_SYMBOL = {
    "ok": "✓",
    "warning": "⚠",
    "exceeded": "✗",
    "no_data": "?",
}


def _fmt(value: Optional[float], unit: str = "ms") -> str:
    if value is None:
        return "N/A"
    return f"{value:.1f}{unit}"


def _format_row(r: BudgetResult) -> str:
    symbol = _STATUS_SYMBOL.get(r.status, "?")
    consumed = f"{r.consumed_pct:.1f}%" if r.consumed_pct is not None else "N/A"
    return (
        f"{r.url:<40} "
        f"{_fmt(r.budget_ms):>8} "
        f"{_fmt(r.avg_ms):>8} "
        f"{consumed:>9} "
        f"{_fmt(r.remaining_ms):>10}  "
        f"{symbol} {r.status}"
    )


def run_latency_budget(
    config: AppConfig,
    histories: dict[str, EndpointHistory],
    out: io.TextIOBase | None = None,
) -> None:
    import sys

    sink = out or sys.stdout
    results = compute_all(config.endpoints, histories)

    lines = [_HEADER, _SEP]
    for r in results:
        lines.append(_format_row(r))
    lines.append("")

    sink.write("\n".join(lines) + "\n")
