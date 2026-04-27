"""Notifier: decides when to fire alerts based on endpoint history and thresholds."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict

from routewatch.alerting import send_alert
from routewatch.config import AlertConfig, EndpointConfig
from routewatch.history import EndpointHistory, error_rate, latest
from routewatch.monitor import CheckResult


@dataclass
class NotifierState:
    """Tracks per-endpoint alert suppression to avoid duplicate notifications."""

    # Maps endpoint URL -> True if an alert is currently "open" (already fired)
    active_alerts: Dict[str, bool] = field(default_factory=dict)


def _should_alert(
    result: CheckResult,
    history: EndpointHistory,
    endpoint_cfg: EndpointConfig,
    alert_cfg: AlertConfig,
    state: NotifierState,
) -> bool:
    """Return True when conditions warrant sending a new alert."""
    url = endpoint_cfg.url
    currently_active = state.active_alerts.get(url, False)

    # Determine whether the endpoint is in a bad state right now
    rate = error_rate(history)
    slow = (
        result.response_time_ms is not None
        and result.response_time_ms > endpoint_cfg.timeout_ms
    )
    bad = (not result.ok) or slow or (rate >= alert_cfg.error_rate_threshold)

    if bad and not currently_active:
        state.active_alerts[url] = True
        return True

    if not bad and currently_active:
        # Endpoint recovered — clear the active flag so future failures re-alert
        state.active_alerts[url] = False

    return False


def evaluate_and_notify(
    result: CheckResult,
    history: EndpointHistory,
    endpoint_cfg: EndpointConfig,
    alert_cfg: AlertConfig,
    state: NotifierState,
) -> bool:
    """Evaluate thresholds and send an alert if required.

    Returns True if an alert was dispatched, False otherwise.
    """
    if not _should_alert(result, history, endpoint_cfg, alert_cfg, state):
        return False

    send_alert(result, alert_cfg)
    return True
