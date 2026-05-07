"""Register the ``tags`` sub-command with the routewatch CLI argument parser."""

from __future__ import annotations

import argparse
import sys
from typing import Dict

from routewatch.config import AppConfig
from routewatch.history import EndpointHistory
from routewatch.commands.show_tags import run_tags


def register(subparsers: argparse._SubParsersAction) -> None:  # noqa: SLF001
    """Attach the *tags* sub-command to *subparsers*."""
    parser: argparse.ArgumentParser = subparsers.add_parser(
        "tags",
        help="Show endpoint summary grouped by tag",
    )
    parser.add_argument(
        "--filter",
        metavar="TAG",
        dest="filter_tag",
        default=None,
        help="Only show endpoints that carry this tag",
    )
    parser.set_defaults(_handler=_handle)


def _handle(
    args: argparse.Namespace,
    cfg: AppConfig,
    histories: Dict[str, EndpointHistory],
) -> None:
    run_tags(cfg, histories, sys.stdout, filter_tag=args.filter_tag)
