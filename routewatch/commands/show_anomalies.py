"""CLI command: print anomaly-detection results for all monitored endpoints."""

from __future__ import annotations

import io
from typing import IO

from routewatch.anomaly import AnomalyResult, detect_all
from routewatch.config import AppConfig
from routewatch.history import EndpointHistory

_COL = ("%-40s", "%-12s", "%-10s", "%-10s", "%-8s", "%s")
_HEADERS = ("ENDPOINT", "RESP (ms)", "MEAN (ms)", "STDDEV", "Z-SCORE", "STATUS")


def _fmt(v: float | None, decimals: int = 1) -> str:
    return f"{v:.{decimals}f}" if v is not None else "n/a"


def _format_header() -> str:
    parts = [fmt % h for fmt, h in zip(_COL, _HEADERS)]
    line = "  ".join(parts)
    return line + "\n" + "-" * len(line)


def _format_row(a: AnomalyResult) -> str:
    url = a.url[:38] + ".." if len(a.url) > 40 else a.url
    status = "⚠ ANOMALY" if a.is_anomaly else "ok"
    parts = [
        _COL[0] % url,
        _COL[1] % _fmt(a.response_time_ms),
        _COL[2] % _fmt(a.mean_ms),
        _COL[3] % _fmt(a.stddev_ms),
        _COL[4] % _fmt(a.z_score, 2),
        _COL[5] % status,
    ]
    return "  ".join(parts)


def run_anomalies(
    cfg: AppConfig,
    histories: dict[str, EndpointHistory],
    out: IO[str] | None = None,
    sigma_threshold: float = 2.5,
) -> None:
    """Write a formatted anomaly report to *out* (defaults to stdout)."""
    import sys

    sink = out or sys.stdout
    anomalies = detect_all(histories, sigma_threshold=sigma_threshold)

    sink.write(_format_header() + "\n")
    for a in anomalies:
        sink.write(_format_row(a) + "\n")

    flagged = [a for a in anomalies if a.is_anomaly]
    sink.write(f"\n{len(flagged)} anomal{'y' if len(flagged) == 1 else 'ies'} detected "
               f"out of {len(anomalies)} endpoint(s).\n")
