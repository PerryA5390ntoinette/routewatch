"""CLI command — display flapping detection results for all monitored endpoints."""
from __future__ import annotations

import io
from typing import TextIO

from routewatch.config import AppConfig
from routewatch.flapping import FlappingResult, detect_all
from routewatch.history import EndpointHistory


_HEADER = f"{'ENDPOINT':<40} {'STATUS':<12} {'TRANSITIONS':>12} {'SAMPLES':>8} {'RATE':>8}"
_SEP = "-" * len(_HEADER)


def _fmt_rate(rate: float | None) -> str:
    if rate is None:
        return "    n/a"
    return f"{rate * 100:6.1f}%"


def _status_symbol(result: FlappingResult) -> str:
    if result.status == "flapping":
        return "⚡ flapping"
    if result.status == "stable":
        return "✔ stable"
    return "– no data"


def _format_row(result: FlappingResult) -> str:
    url = result.url if len(result.url) <= 40 else result.url[:37] + "..."
    return (
        f"{url:<40} "
        f"{_status_symbol(result):<12} "
        f"{result.transitions:>12} "
        f"{result.sample_count:>8} "
        f"{_fmt_rate(result.transition_rate):>8}"
    )


def run_flapping(
    cfg: AppConfig,
    histories: dict[str, EndpointHistory],
    *,
    out: TextIO | None = None,
    threshold: float = 0.4,
) -> None:
    """Print a flapping-detection summary table to *out* (defaults to stdout)."""
    import sys

    sink = out or sys.stdout
    results = detect_all(histories, threshold=threshold)

    sink.write(_HEADER + "\n")
    sink.write(_SEP + "\n")
    for r in results:
        sink.write(_format_row(r) + "\n")

    flapping_count = sum(1 for r in results if r.is_flapping)
    sink.write(_SEP + "\n")
    sink.write(f"{flapping_count} of {len(results)} endpoint(s) currently flapping.\n")
