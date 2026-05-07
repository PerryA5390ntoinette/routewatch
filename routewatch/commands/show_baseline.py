"""CLI command: display baseline statistics for all monitored endpoints."""
from __future__ import annotations

import io
from typing import TextIO

from routewatch.baseline import BaselineStats, compute_all
from routewatch.config import AppConfig
from routewatch.history import EndpointHistory

_HEADER = f"{'ENDPOINT':<45} {'SAMPLES':>7} {'MEDIAN ms':>10} {'P95 ms':>10}"
_SEP = "-" * len(_HEADER)


def _fmt_float(value: float | None) -> str:
    return f"{value:>10.1f}" if value is not None else f"{'n/a':>10}"


def _format_row(stats: BaselineStats) -> str:
    url = stats.url if len(stats.url) <= 45 else stats.url[:42] + "..."
    return (
        f"{url:<45}"
        f" {stats.sample_count:>7}"
        f"{_fmt_float(stats.median_ms)}"
        f"{_fmt_float(stats.p95_ms)}"
    )


def run_baseline(
    config: AppConfig,
    histories: dict[str, EndpointHistory],
    out: TextIO | None = None,
    multiplier: float = 2.0,
) -> None:
    """Print a baseline summary table to *out* (defaults to stdout)."""
    import sys

    sink: TextIO = out or sys.stdout
    baselines = compute_all(histories)

    lines = [_HEADER, _SEP]
    for endpoint in config.endpoints:
        stats = baselines.get(endpoint.url)
        if stats is None:
            stats = BaselineStats(
                url=endpoint.url,
                sample_count=0,
                median_ms=None,
                p95_ms=None,
            )
        lines.append(_format_row(stats))

    lines.append(_SEP)
    lines.append(
        f"Baseline multiplier: {multiplier}×  "
        "(alert fires when response_time > multiplier × median)"
    )

    sink.write("\n".join(lines) + "\n")
