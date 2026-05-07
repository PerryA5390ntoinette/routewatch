"""CLI command: display response-time trend for all monitored endpoints."""

from __future__ import annotations

import sys
from io import StringIO
from typing import IO

from routewatch.config import AppConfig
from routewatch.history import EndpointHistory
from routewatch.trending import TrendStats, compute_all

_DIRECTION_SYMBOL = {
    "improving": "\u2193",   # ↓
    "stable":    "\u2192",   # →
    "degrading": "\u2191",   # ↑
}

_COL_URL = 36
_COL_SAMPLES = 9
_COL_SLOPE = 14
_COL_TREND = 12


def _format_header() -> str:
    return (
        f"{'Endpoint':<{_COL_URL}}"
        f"{'Samples':>{_COL_SAMPLES}}"
        f"{'Slope(ms)':>{_COL_SLOPE}}"
        f"  {'Trend':<{_COL_TREND}}"
    )


def _format_row(stat: TrendStats) -> str:
    slope_str = (
        f"{stat.slope_ms_per_check:+.2f}"
        if stat.slope_ms_per_check is not None
        else "n/a"
    )
    symbol = _DIRECTION_SYMBOL.get(stat.direction, "?")
    trend_label = f"{symbol} {stat.direction}"
    return (
        f"{stat.endpoint_url:<{_COL_URL}}"
        f"{stat.sample_count:>{_COL_SAMPLES}}"
        f"{slope_str:>{_COL_SLOPE}}"
        f"  {trend_label:<{_COL_TREND}}"
    )


def run_trending(
    config: AppConfig,
    histories: dict[str, EndpointHistory],
    out: IO[str] = sys.stdout,
) -> None:
    """Write a trending table to *out*."""
    stats = compute_all(histories)

    buf = StringIO()
    buf.write(_format_header() + "\n")
    buf.write("-" * (_COL_URL + _COL_SAMPLES + _COL_SLOPE + 2 + _COL_TREND) + "\n")
    for url in config.endpoints_by_url():
        stat = stats.get(url)
        if stat is None:
            continue
        buf.write(_format_row(stat) + "\n")

    out.write(buf.getvalue())
