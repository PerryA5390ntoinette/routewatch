"""CLI command: display endpoint health scores in a formatted table."""
from __future__ import annotations

import io
from typing import TextIO

from routewatch.config import AppConfig
from routewatch.history import EndpointHistory
from routewatch.scoring import HealthScore, compute_all

_COL_URL = 40
_COL_SCORE = 7
_COL_GRADE = 6
_COL_ERR = 10
_COL_AVG = 12
_COL_N = 8


def _format_header() -> str:
    return (
        f"{'ENDPOINT':<{_COL_URL}}"
        f"{'SCORE':>{_COL_SCORE}}"
        f"{'GRADE':>{_COL_GRADE}}"
        f"{'ERR %':>{_COL_ERR}}"
        f"{'AVG MS':>{_COL_AVG}}"
        f"{'SAMPLES':>{_COL_N}}"
    )


def _format_row(hs: HealthScore) -> str:
    avg = f"{hs.avg_response_ms:.1f}" if hs.avg_response_ms is not None else "—"
    url = hs.endpoint_url
    if len(url) > _COL_URL - 1:
        url = url[: _COL_URL - 4] + "..."
    return (
        f"{url:<{_COL_URL}}"
        f"{hs.score:>{_COL_SCORE}.1f}"
        f"{hs.grade:>{_COL_GRADE}}"
        f"{hs.error_rate_pct:>{_COL_ERR}.1f}"
        f"{avg:>{_COL_AVG}}"
        f"{hs.sample_count:>{_COL_N}}"
    )


def run_scoring(
    cfg: AppConfig,
    histories: dict[str, EndpointHistory],
    out: TextIO,
) -> None:
    scores = compute_all(cfg.endpoints, histories)

    separator = "-" * (_COL_URL + _COL_SCORE + _COL_GRADE + _COL_ERR + _COL_AVG + _COL_N)
    out.write("\nEndpoint Health Scores\n")
    out.write(separator + "\n")
    out.write(_format_header() + "\n")
    out.write(separator + "\n")

    if not scores:
        out.write("  No data available.\n")
    else:
        for hs in scores:
            out.write(_format_row(hs) + "\n")

    out.write(separator + "\n")
