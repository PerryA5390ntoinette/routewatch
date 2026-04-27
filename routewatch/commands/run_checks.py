"""Command: run a single round of checks against all configured endpoints."""

from __future__ import annotations

import asyncio
from typing import Dict

from routewatch.config import AppConfig
from routewatch.history import EndpointHistory, record
from routewatch.monitor import check_endpoint
from routewatch.notifier import NotifierState, evaluate_and_notify


async def _check_one(
    endpoint_cfg,
    history: EndpointHistory,
    state: NotifierState,
    alert_cfg,
) -> None:
    result = await check_endpoint(endpoint_cfg)
    record(history, result)
    await evaluate_and_notify(endpoint_cfg, alert_cfg, history, state)


async def run_checks_async(
    app_config: AppConfig,
    histories: Dict[str, EndpointHistory],
    states: Dict[str, NotifierState],
) -> None:
    """Run checks for every endpoint concurrently."""
    tasks = [
        _check_one(
            ep,
            histories[ep.url],
            states[ep.url],
            app_config.alert,
        )
        for ep in app_config.endpoints
    ]
    await asyncio.gather(*tasks)


def run_checks(
    app_config: AppConfig,
    histories: Dict[str, EndpointHistory],
    states: Dict[str, NotifierState],
) -> None:
    """Synchronous wrapper around run_checks_async."""
    asyncio.run(run_checks_async(app_config, histories, states))
