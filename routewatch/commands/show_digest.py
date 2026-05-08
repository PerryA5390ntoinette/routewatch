"""CLI command: show a health digest across all monitored endpoints."""
from __future__ import annotations

import sys
from typing import Dict, TextIO

from routewatch.config import AppConfig
from routewatch.digest import build_digest, format_digest_text
from routewatch.history import EndpointHistory


def run_digest(
    config: AppConfig,
    histories: Dict[str, EndpointHistory],
    window_label: str = "recent",
    out: TextIO = sys.stdout,
) -> None:
    """Build and print a digest report to *out*."""
    digest = build_digest(
        endpoints=config.endpoints,
        histories=histories,
        window_label=window_label,
    )
    out.write(format_digest_text(digest))
    out.write("\n")
