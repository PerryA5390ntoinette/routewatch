"""CLI command: show a summary grouped by endpoint tag."""

from __future__ import annotations

import io
from typing import Dict, List, Optional

from routewatch.config import AppConfig
from routewatch.history import EndpointHistory, average_response_time_ms, error_rate
from routewatch.tagging import group_by_tag

_COL_TAG = 16
_COL_URL = 36
_COL_AVG = 12
_COL_ERR = 10


def _format_header() -> str:
    return (
        f"{'TAG':<{_COL_TAG}} {'ENDPOINT':<{_COL_URL}} "
        f"{'AVG (ms)':>{_COL_AVG}} {'ERR %':>{_COL_ERR}}"
    )


def _format_row(
    tag: str,
    url: str,
    avg_ms: Optional[float],
    err_pct: float,
) -> str:
    avg_str = f"{avg_ms:.1f}" if avg_ms is not None else "—"
    err_str = f"{err_pct * 100:.1f}%"
    return (
        f"{tag:<{_COL_TAG}} {url:<{_COL_URL}} "
        f"{avg_str:>{_COL_AVG}} {err_str:>{_COL_ERR}}"
    )


def run_tags(
    cfg: AppConfig,
    histories: Dict[str, EndpointHistory],
    out: io.TextIOBase,
    filter_tag: Optional[str] = None,
) -> None:
    """Write a tag-grouped endpoint summary to *out*."""
    endpoints = cfg.endpoints
    groups = group_by_tag(endpoints)

    tag_keys: List[str] = sorted(groups.keys())
    if filter_tag is not None:
        needle = filter_tag.strip().lower()
        tag_keys = [k for k in tag_keys if k == needle]

    out.write(_format_header() + "\n")
    out.write("-" * (_COL_TAG + _COL_URL + _COL_AVG + _COL_ERR + 3) + "\n")

    for tag in tag_keys:
        display_tag = tag if tag else "(untagged)"
        for ep in groups[tag]:
            hist = histories.get(ep.url)
            avg = average_response_time_ms(hist) if hist else None
            err = error_rate(hist) if hist else 0.0
            out.write(_format_row(display_tag, ep.url, avg, err) + "\n")

    out.flush()
