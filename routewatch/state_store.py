"""Factory helpers that build the shared histories and notifier-state dicts."""

from __future__ import annotations

from typing import Dict, Tuple

from routewatch.config import AppConfig
from routewatch.history import EndpointHistory
from routewatch.notifier import NotifierState


def build_stores(
    app_config: AppConfig,
) -> Tuple[Dict[str, EndpointHistory], Dict[str, NotifierState]]:
    """Return (histories, states) keyed by endpoint URL.

    Both dicts are pre-populated so every configured endpoint has an entry
    before the first check runs.
    """
    histories: Dict[str, EndpointHistory] = {}
    states: Dict[str, NotifierState] = {}

    for ep in app_config.endpoints:
        histories[ep.url] = EndpointHistory(
            url=ep.url,
            max_size=app_config.history_size,
        )
        states[ep.url] = NotifierState()

    return histories, states
