"""CLI command: prune stale history entries according to a retention policy."""

from __future__ import annotations

import sys
from typing import Dict

from routewatch.config import AppConfig
from routewatch.history import EndpointHistory
from routewatch.retention import RetentionPolicy, prune_all


def run_prune(
    cfg: AppConfig,
    histories: Dict[str, EndpointHistory],
    *,
    out=None,
) -> None:
    """Prune history entries older than *cfg.retention_seconds* and report results."""
    if out is None:
        out = sys.stdout

    max_age = getattr(cfg, "retention_seconds", None)
    if max_age is None:
        out.write("No retention policy configured — nothing pruned.\n")
        return

    policy = RetentionPolicy(max_age_seconds=float(max_age))
    removed = prune_all(histories, policy)

    total = sum(removed.values())
    if total == 0:
        out.write("Retention prune complete: no entries removed.\n")
        return

    out.write(f"Retention prune complete: {total} entr{'y' if total == 1 else 'ies'} removed.\n")
    for url, count in removed.items():
        if count:
            out.write(f"  {url}: {count} removed\n")
