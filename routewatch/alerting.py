"""Webhook alerting module for routewatch."""

import json
import logging
import time
from typing import Optional

import httpx

from routewatch.config import AlertConfig
from routewatch.monitor import CheckResult

logger = logging.getLogger(__name__)


def build_payload(result: CheckResult, config: AlertConfig) -> dict:
    """Build the webhook payload from a failed check result."""
    return {
        "alert": {
            "endpoint": result.url,
            "status": "unhealthy",
            "status_code": result.status_code,
            "response_time_ms": round(result.response_time_ms, 2) if result.response_time_ms is not None else None,
            "error": result.error,
            "timestamp": result.timestamp,
        },
        "thresholds": {
            "max_response_time_ms": config.max_response_time_ms,
            "expected_status_codes": config.expected_status_codes,
        },
    }


def send_alert(
    result: CheckResult,
    config: AlertConfig,
    timeout: float = 5.0,
) -> bool:
    """Send an alert to the configured webhook URL.

    Returns True if the alert was delivered successfully, False otherwise.
    """
    payload = build_payload(result, config)
    headers = {"Content-Type": "application/json"}
    if config.webhook_secret:
        headers["X-RouteWatch-Secret"] = config.webhook_secret

    for attempt in range(1, config.retry_attempts + 1):
        try:
            response = httpx.post(
                config.webhook_url,
                content=json.dumps(payload),
                headers=headers,
                timeout=timeout,
            )
            response.raise_for_status()
            logger.info(
                "Alert sent for %s (attempt %d/%d): HTTP %d",
                result.url,
                attempt,
                config.retry_attempts,
                response.status_code,
            )
            return True
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "Alert delivery failed for %s (attempt %d/%d): HTTP %d",
                result.url,
                attempt,
                config.retry_attempts,
                exc.response.status_code,
            )
        except httpx.RequestError as exc:
            logger.warning(
                "Alert delivery error for %s (attempt %d/%d): %s",
                result.url,
                attempt,
                config.retry_attempts,
                exc,
            )

        if attempt < config.retry_attempts:
            time.sleep(config.retry_delay_seconds)

    logger.error("Failed to deliver alert for %s after %d attempts.", result.url, config.retry_attempts)
    return False
