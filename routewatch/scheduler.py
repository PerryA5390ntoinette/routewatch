"""Scheduler for periodically checking endpoints."""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Callable, Awaitable

from routewatch.config import AppConfig
from routewatch.monitor import CheckResult, check_endpoint
from routewatch.alerting import send_alert

logger = logging.getLogger(__name__)


ResultCallback = Callable[[CheckResult], Awaitable[None]]


async def run_check_cycle(
    config: AppConfig,
    on_result: ResultCallback | None = None,
) -> list[CheckResult]:
    """Run a single check cycle for all configured endpoints."""
    tasks = [check_endpoint(ep) for ep in config.endpoints]
    results: list[CheckResult] = await asyncio.gather(*tasks)

    for result in results:
        logger.info(
            "checked %s status=%s response_time=%s",
            result.url,
            result.status_code,
            f"{result.response_time_ms:.1f}ms" if result.response_time_ms is not None else "N/A",
        )

        threshold_breached = (
            result.response_time_ms is not None
            and result.response_time_ms > config.alert.response_time_threshold_ms
        )

        if not result.is_healthy or threshold_breached:
            logger.warning("alert condition met for %s — sending alert", result.url)
            await send_alert(config.alert, result)

        if on_result is not None:
            await on_result(result)

    return results


async def start_scheduler(
    config: AppConfig,
    on_result: ResultCallback | None = None,
    stop_event: asyncio.Event | None = None,
) -> None:
    """Run check cycles on the configured interval until stop_event is set."""
    stop_event = stop_event or asyncio.Event()
    interval = config.check_interval_seconds

    logger.info(
        "scheduler started — %d endpoint(s), interval=%ds",
        len(config.endpoints),
        interval,
    )

    while not stop_event.is_set():
        cycle_start = datetime.now(timezone.utc)
        try:
            await run_check_cycle(config, on_result)
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("unexpected error during check cycle: %s", exc)

        elapsed = (datetime.now(timezone.utc) - cycle_start).total_seconds()
        sleep_for = max(0.0, interval - elapsed)

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=sleep_for)
        except asyncio.TimeoutError:
            pass

    logger.info("scheduler stopped")
