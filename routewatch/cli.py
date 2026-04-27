"""Minimal CLI entry-point for RouteWatch.

Usage:
    python -m routewatch.cli          # run with env-based config
    python -m routewatch.cli --report  # print a one-shot status report and exit
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from typing import Dict

from routewatch.config import load_config_from_env, validate_config
from routewatch.history import EndpointHistory
from routewatch.monitor import check_endpoint
from routewatch.reporter import build_report, format_report_text


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="routewatch",
        description="Lightweight HTTP endpoint monitor.",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Perform a single check of all endpoints, print a report, then exit.",
    )
    return parser


async def _one_shot_report() -> None:
    """Check every configured endpoint once and print a summary report."""
    config = load_config_from_env()
    errors = validate_config(config)
    if errors:
        for err in errors:
            print(f"Config error: {err}", file=sys.stderr)
        sys.exit(1)

    histories: Dict[str, EndpointHistory] = {}

    for ep in config.endpoints:
        result = await check_endpoint(ep)
        h: EndpointHistory = []
        from routewatch.history import record
        record(h, result)
        histories[ep.url] = h

    summaries = build_report(histories)
    print(format_report_text(summaries))


def main() -> None:
    parser = _build_arg_parser()
    args = parser.parse_args()

    if args.report:
        asyncio.run(_one_shot_report())
    else:
        # Defer import to avoid circular deps at module level
        from routewatch.scheduler import run  # type: ignore[import]
        asyncio.run(run())


if __name__ == "__main__":
    main()
