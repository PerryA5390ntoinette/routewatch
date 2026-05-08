"""CLI command: show hourly response-time heatmap for all endpoints."""
from __future__ import annotations

from io import StringIO
from typing import Dict

from routewatch.config import AppConfig
from routewatch.heatmap import HeatmapResult, HourBucket, compute_all, peak_hour
from routewatch.history import EndpointHistory

_HEADER = f"{'URL':<40} {'HR':>3}  {'AVG ms':>8}  {'SAMPLES':>7}  {'ERRORS':>6}"
_SEP = "-" * len(_HEADER)


def _fmt_avg(bucket: HourBucket) -> str:
    if bucket.avg_response_ms is None:
        return "       -"
    return f"{bucket.avg_response_ms:>8.1f}"


def _format_rows(url: str, result: HeatmapResult) -> str:
    buf = StringIO()
    peak = peak_hour(result)
    short_url = url if len(url) <= 40 else url[:37] + "..."
    for bucket in result.buckets:
        marker = " *" if bucket.hour == peak else "  "
        buf.write(
            f"{short_url:<40} {bucket.hour:>3}  "
            f"{_fmt_avg(bucket)}  "
            f"{bucket.sample_count:>7}  "
            f"{bucket.error_count:>6}"
            f"{marker}\n"
        )
        short_url = ""  # only print URL on first row
    return buf.getvalue()


def run_heatmap(
    config: AppConfig,
    histories: Dict[str, EndpointHistory],
    out: "StringIO | None" = None,
) -> None:
    import sys

    sink = out if out is not None else sys.stdout
    results = compute_all(histories)

    sink.write(_HEADER + "\n")
    sink.write(_SEP + "\n")
    for url in config.endpoints_by_url():
        if url not in results:
            continue
        sink.write(_format_rows(url, results[url]))
        sink.write(_SEP + "\n")
    sink.write("  * = peak hour\n")
