"""Register the 'digest' sub-command with the RouteWatch CLI."""
from __future__ import annotations

import argparse
from typing import Dict

from routewatch.config import AppConfig
from routewatch.commands.show_digest import run_digest
from routewatch.history import EndpointHistory


def register(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    """Attach the *digest* sub-command to *subparsers*."""
    parser: argparse.ArgumentParser = subparsers.add_parser(
        "digest",
        help="Show a health digest summary across all monitored endpoints.",
    )
    parser.add_argument(
        "--window",
        default="recent",
        metavar="LABEL",
        help="Descriptive label for the time window (default: 'recent').",
    )
    parser.set_defaults(func=_handle)


def _handle(
    args: argparse.Namespace,
    config: AppConfig,
    histories: Dict[str, EndpointHistory],
) -> None:
    run_digest(
        config=config,
        histories=histories,
        window_label=args.window,
    )
