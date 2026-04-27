"""CLI sub-command: show a live-refreshing dashboard of monitored endpoints."""

from __future__ import annotations

import time
import os
import sys
from typing import Optional

from routewatch.config import AppConfig
from routewatch.dashboard import build_dashboard_rows, render_dashboard
from routewatch.history import EndpointHistory


def _clear_screen() -> None:
    """Clear terminal screen in a cross-platform way."""
    os.system("cls" if os.name == "nt" else "clear")


def run_dashboard(
    config: AppConfig,
    histories: dict[str, EndpointHistory],
    refresh_seconds: int = 10,
    once: bool = False,
) -> None:
    """Print the dashboard, optionally refreshing every *refresh_seconds*.

    Parameters
    ----------
    config:
        Application configuration (used for slow-threshold).
    histories:
        Mapping of endpoint name -> EndpointHistory populated by the scheduler.
    refresh_seconds:
        How often to redraw the dashboard.  Ignored when *once* is True.
    once:
        If True, render once and return immediately (useful for testing / CI).
    """
    slow_ms = config.alert.response_time_threshold_ms if config.alert else 1000.0

    while True:
        if not once:
            _clear_screen()

        rows = build_dashboard_rows(histories, slow_threshold_ms=slow_ms)
        output = render_dashboard(rows)
        sys.stdout.write(output)
        sys.stdout.flush()

        if once:
            return

        try:
            time.sleep(refresh_seconds)
        except KeyboardInterrupt:
            sys.stdout.write("\nDashboard stopped.\n")
            return
