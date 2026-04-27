"""CLI command: print a human-readable summary report for all monitored endpoints."""

from __future__ import annotations

import sys
from typing import Dict

from routewatch.config import AppConfig
from routewatch.history import EndpointHistory
from routewatch.reporter import build_report, format_report_text


def run_report(
    config: AppConfig,
    histories: Dict[str, EndpointHistory],
    *,
    out=None,
) -> None:
    """Build and print a text report to *out* (defaults to stdout).

    Parameters
    ----------
    config:
        Application configuration (used to obtain endpoint metadata).
    histories:
        Mapping of endpoint URL -> EndpointHistory collected so far.
    out:
        File-like object to write output to.  Defaults to ``sys.stdout``.
    """
    if out is None:
        out = sys.stdout

    report = build_report(config.endpoints, histories)
    text = format_report_text(report)
    out.write(text)
    if not text.endswith("\n"):
        out.write("\n")
