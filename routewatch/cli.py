"""Command-line entry point for routewatch."""

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

    sub.add_parser("dashboard", help="Live auto-refreshing dashboard.")
    sub.add_parser("report", help="Print a one-shot summary report.")
    sub.add_parser("status", help="Print current status for every endpoint.")
    sub.add_parser("history", help="Print recent check history.")

    export_p = sub.add_parser("export", help="Export history snapshot as JSON.")
    export_p.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    export_p.add_argument("--out", metavar="FILE", help="Write to FILE instead of stdout.")

    prune_p = sub.add_parser("prune", help="Remove expired history entries.")
    prune_p.add_argument("--max-age-hours", type=float, default=24.0, metavar="H",
                         help="Discard entries older than H hours (default: 24).")

    sub.add_parser("check", help="Run one check pass and exit (non-zero if any endpoint unhealthy).")

    return parser


def main(argv: list[str] | None = None) -> int:  # noqa: UP007
    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    config = load_config_from_env()
    try:
        validate_config(config)
    except ValueError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    histories, states = build_stores(config)

    if args.command == "dashboard":
        from routewatch.commands.show_dashboard import run_dashboard
        run_dashboard(config, histories)

    elif args.command == "report":
        from routewatch.commands.show_report import run_report
        run_report(config, histories)

    elif args.command == "status":
        from routewatch.commands.show_status import run_status
        run_status(config, histories)

    elif args.command == "history":
        from routewatch.commands.show_history import run_history
        run_history(config, histories)

    elif args.command == "export":
        from routewatch.commands.export_snapshot import run_export
        run_export(config, histories, pretty=args.pretty, out_path=args.out)

    elif args.command == "prune":
        from routewatch.commands.prune_history import run_prune
        run_prune(config, histories, max_age_hours=args.max_age_hours)

    elif args.command == "check":
        from routewatch.commands.check_once import run_check_once
        failures = run_check_once(config, histories, states, notify=True)
        return 1 if failures else 0

    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
