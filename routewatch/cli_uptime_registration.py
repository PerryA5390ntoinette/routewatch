"""Registers the 'uptime' subcommand with the routewatch CLI argument parser.

This module is intentionally thin — it wires together the arg-parser entry
point defined in cli.py with the run_uptime command, following the same
pattern used by other commands in the project.
"""
from __future__ import annotations

import argparse
import sys
from typing import Dict

from routewatch.config import AppConfig
from routewatch.history import EndpointHistory
from routewatch.commands.show_uptime import run_uptime


def register(subparsers: argparse._SubParsersAction) -> None:  # noqa: SLF001
    """Add the 'uptime' subcommand to *subparsers*."""
    parser: argparse.ArgumentParser = subparsers.add_parser(
        "uptime",
        help="Show uptime percentage and downtime windows for all endpoints.",
    )
    parser.set_defaults(func=_handle)


def _handle(
    args: argparse.Namespace,
    config: AppConfig,
    histories: Dict[str, EndpointHistory],
) -> int:
    """Invoked by the CLI dispatcher when the 'uptime' subcommand is selected."""
    run_uptime(config, histories, out=sys.stdout)
    return 0
