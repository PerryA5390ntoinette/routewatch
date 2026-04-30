"""Retention policy: prune history entries older than a configurable TTL."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict

from routewatch.history import EndpointHistory


@dataclass
class RetentionPolicy:
    """Describes how long to keep check results."""

    max_age_seconds: float

    def is_expired(self, timestamp: float, now: float | None = None) -> bool:
        """Return True if *timestamp* is older than the TTL."""
        if now is None:
            now = time.time()
        return (now - timestamp) > self.max_age_seconds


def prune_history(history: EndpointHistory, policy: RetentionPolicy, now: float | None = None) -> int:
    """Remove entries from *history* that exceed the policy TTL.

    Returns the number of entries removed.
    """
    if now is None:
        now = time.time()

    before = len(history.results)
    history.results = [
        r for r in history.results if not policy.is_expired(r.checked_at, now)
    ]
    return before - len(history.results)


def prune_all(
    histories: Dict[str, EndpointHistory],
    policy: RetentionPolicy,
    now: float | None = None,
) -> Dict[str, int]:
    """Prune every history in *histories*.

    Returns a mapping of endpoint URL -> number of entries removed.
    """
    return {url: prune_history(hist, policy, now) for url, hist in histories.items()}
