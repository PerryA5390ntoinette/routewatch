"""CLI command: display response-time trend for every monitored endpoint."""

from __future__ import annotations

import io
from typing import Dict

from routewatch.config import AppConfig
from routewatch.history import EndpointHistory
from routewatch.trending import TrendStats, compute_all

_COL_URL = 36
_COL_SAMPLES = 9
_COL_SLOPE = 14
_COL_DIRECTION = 12
_COL_VERDICT = 18


def _format_header() -> str:
    return (
        f"{'Endpoint':<{_COL_URL}}"
        f"{'Samples':>{_COL_SAMPLES}}"
        f"{'Slope(ms/s)':>{_COL_SLOPE}}"
        f"{'Direction':>{_COL_DIRECTION}}"
        f"{'Verdict':>{_COL_VERDICT}}"
    )


def _format_row(url: str, stats: TrendStats) -> str:
    if stats.sample_count == 0:
        return f"{url:<{_COL_URL}}{'0':>{_COL_SAMPLES}}{'n/a':>{_COL_SLOPE}}{'n/a':>{_COL_DIRECTION}}{'insufficient data':>{_COL_VERDICT}}"

    slope_str = f"{stats.slope_ms_per_s:+.3f}" if stats.slope_ms_per_s is not None else "n/a"

    if stats.slope_ms_per_s is None:
        direction = "n/a"
        verdict = "insufficient data"
    elif stats.slope_ms_per_s > 0.5:
        direction = "↑ rising"
        verdict = "degrading"
    elif stats.slope_ms_per_s < -0.5:
        direction = "↓ falling"
        verdict = "improving"
    else:
        direction = "→ flat"
        verdict = "stable"

    return (
        f"{url:<{_COL_URL}}"
        f"{stats.sample_count:>{_COL_SAMPLES}}"
        f"{slope_str:>{_COL_SLOPE}}"
        f"{direction:>{_COL_DIRECTION}}"
        f"{verdict:>{_COL_VERDICT}}"
    )


def run_trending(
    cfg: AppConfig,
    histories: Dict[str, EndpointHistory],
    out: io.TextIOBase,
) -> None:
    """Write a trending table to *out*."""
    all_stats = compute_all(histories)

    separator = "-" * (_COL_URL + _COL_SAMPLES + _COL_SLOPE + _COL_DIRECTION + _COL_VERDICT)
    out.write(_format_header() + "\n")
    out.write(separator + "\n")

    for ep in cfg.endpoints:
        stats = all_stats.get(ep.url, TrendStats(sample_count=0, slope_ms_per_s=None))
        out.write(_format_row(ep.url, stats) + "\n")
