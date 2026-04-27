"""CLI command: export a JSON snapshot of all endpoint histories."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict

from routewatch.config import AppConfig
from routewatch.exporter import dump_json
from routewatch.history import EndpointHistory


def run_export(
    config: AppConfig,
    histories: Dict[str, EndpointHistory],
    output_path: str | None = None,
    *,
    pretty: bool = True,
) -> None:
    """Serialise all histories to JSON and write to *output_path* or stdout.

    Parameters
    ----------
    config:
        Application configuration (used for metadata).
    histories:
        Mapping of endpoint URL -> :class:`EndpointHistory`.
    output_path:
        Filesystem path to write the snapshot.  When *None* the JSON is
        written to *stdout*.
    pretty:
        Indent the JSON output for human readability.
    """
    indent = 2 if pretty else None
    payload = dump_json(histories, indent=indent)

    if output_path is None:
        sys.stdout.write(payload)
        sys.stdout.write("\n")
    else:
        dest = Path(output_path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(payload, encoding="utf-8")
        print(f"Snapshot written to {dest}")
