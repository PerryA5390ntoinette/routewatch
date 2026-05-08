"""CLI command: show SLA compliance for all monitored endpoints."""
from __future__ import annotations

import sys
from typing import IO, Optional

from routewatch.config import AppConfig
from routewatch.history import EndpointHistory
from routewatch.sla import SLAResult, compute_all

_TICK = "\u2713"
_CROSS = "\u2717"
_UNKNOWN = "?"


def _fmt_pct(value: Optional[float]) -> str:
    if value is None:
        return "n/a"
    return f"{value:.2f}%"


def _status_symbol(result: SLAResult) -> str:
    if result.met is None:
        return _UNKNOWN
    return _TICK if result.met else _CROSS


def _format_header() -> str:
    return f"{'Status':<8} {'Endpoint':<45} {'Target':>8} {'Actual':>8} {'Samples':>8}"


def _format_row(result: SLAResult) -> str:
    symbol = _status_symbol(result)
    return (
        f"{symbol:<8} {result.url:<45} "
        f"{_fmt_pct(result.target_pct):>8} "
        f"{_fmt_pct(result.actual_pct):>8} "
        f"{result.sample_count:>8}"
    )


def run_sla(
    config: AppConfig,
    histories: dict[str, EndpointHistory],
    out: IO[str] = sys.stdout,
) -> None:
    """Print an SLA compliance table to *out*."""
    results = compute_all(config.endpoints, histories)

    out.write("SLA Compliance Report\n")
    out.write("=" * 80 + "\n")
    out.write(_format_header() + "\n")
    out.write("-" * 80 + "\n")

    if not results:
        out.write("No endpoint data available.\n")
        return

    for row in results:
        out.write(_format_row(row) + "\n")

    met = sum(1 for r in results if r.met is True)
    total = len(results)
    out.write("-" * 80 + "\n")
    out.write(f"Endpoints meeting SLA: {met}/{total}\n")
