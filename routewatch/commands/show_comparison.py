"""CLI command: show a ranked comparison table of all monitored endpoints."""
from __future__ import annotations

import io
from typing import Dict, TextIO

from routewatch.comparison import compare_endpoints, ComparisonRow
from routewatch.config import AppConfig
from routewatch.history import EndpointHistory


def _fmt(value: float | None, decimals: int = 1) -> str:
    if value is None:
        return "n/a"
    return f"{value:.{decimals}f}"


def _format_header() -> str:
    return (
        f"{'Rank':<6} {'URL':<40} {'Avg RT (ms)':<14} "
        f"{'Err Rate %':<12} {'Baseline Mdn (ms)':<18}"
    )


def _format_row(row: ComparisonRow) -> str:
    return (
        f"{row.rank:<6} {row.url:<40} "
        f"{_fmt(row.avg_response_time_ms):<14} "
        f"{_fmt(row.error_rate_pct):<12} "
        f"{_fmt(row.baseline_median_ms):<18}"
    )


def run_comparison(
    config: AppConfig,
    histories: Dict[str, EndpointHistory],
    out: TextIO,
) -> None:
    """Render a ranked endpoint comparison table to *out*."""
    rows = compare_endpoints(histories)

    out.write("Endpoint Comparison\n")
    out.write("=" * 94 + "\n")
    out.write(_format_header() + "\n")
    out.write("-" * 94 + "\n")

    for row in rows:
        out.write(_format_row(row) + "\n")

    out.write("=" * 94 + "\n")
