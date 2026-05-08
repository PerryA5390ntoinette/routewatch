"""Register the 'heatmap' sub-command with the routewatch CLI."""
from __future__ import annotations

import argparse
from typing import Dict

from routewatch.commands.show_heatmap import run_heatmap
from routewatch.config import AppConfig
from routewatch.history import EndpointHistory


def register(subparsers: "argparse._SubParsersAction") -> None:  # type: ignore[type-arg]
    """Attach the heatmap sub-command to *subparsers*."""
    parser: argparse.ArgumentParser = subparsers.add_parser(
        "heatmap",
        help="Show hourly response-time heatmap for all monitored endpoints.",
    )
    parser.add_argument(
        "--url",
        metavar="URL",
        default=None,
        help="Restrict output to a single endpoint URL.",
    )
    parser.set_defaults(func=_handle)


def _handle(
    args: argparse.Namespace,
    config: AppConfig,
    histories: Dict[str, EndpointHistory],
) -> None:
    filtered = histories
    if getattr(args, "url", None):
        filtered = {
            url: h for url, h in histories.items() if url == args.url
        }
        if not filtered:
            print(f"No history found for URL: {args.url}")
            return
    run_heatmap(config, filtered)
