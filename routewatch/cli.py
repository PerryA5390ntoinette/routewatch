"""Entry-point: parse CLI arguments and dispatch to command handlers."""
from __future__ import annotations

import argparse
import sys

from routewatch.config import load_config_from_env, validate_config
from routewatch.state_store import build_stores


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="routewatch",
        description="Lightweight HTTP endpoint monitor.",
    )
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    sub.add_parser("run", help="Run one round of checks and send alerts if needed.")
    sub.add_parser("dashboard", help="Display a live auto-refreshing dashboard.")
    sub.add_parser("report", help="Print a summary report for all endpoints.")

    history_p = sub.add_parser("history", help="Show recent check history for all endpoints.")
    history_p.add_argument(
        "--limit",
        type=int,
        default=10,
        metavar="N",
        help="Maximum number of results to show per endpoint (default: 10).",
    )

    export_p = sub.add_parser("export", help="Export history snapshot as JSON.")
    export_p.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")

    prune_p = sub.add_parser("prune", help="Remove expired history entries.")
    prune_p.add_argument(
        "--max-age-hours",
        type=float,
        default=24.0,
        metavar="H",
        help="Remove results older than H hours (default: 24).",
    )

    return parser


def main(argv: list[str] | None = None) -> None:  # pragma: no cover
    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    cfg = load_config_from_env()
    validate_config(cfg)
    stores = build_stores(cfg)
    histories = {url: s.history for url, s in stores.items()}
    states = {url: s.state for url, s in stores.items()}

    if args.command == "run":
        from routewatch.commands.run_checks import run_checks
        run_checks(cfg, stores)

    elif args.command == "dashboard":
        from routewatch.commands.show_dashboard import run_dashboard
        run_dashboard(cfg, histories)

    elif args.command == "report":
        from routewatch.commands.show_report import run_report
        run_report(cfg, histories)

    elif args.command == "history":
        from routewatch.commands.show_history import run_history
        run_history(cfg, histories, limit=args.limit)

    elif args.command == "export":
        from routewatch.commands.export_snapshot import run_export
        run_export(cfg, histories, pretty=args.pretty)

    elif args.command == "prune":
        from routewatch.commands.prune_history import run_prune
        run_prune(cfg, histories, max_age_hours=args.max_age_hours)
