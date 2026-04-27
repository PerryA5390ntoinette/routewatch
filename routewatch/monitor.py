"""Core monitoring logic for RouteWatch.

Handles HTTP endpoint checking, response time measurement,
and threshold breach detection.
"""

import time
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import httpx

from routewatch.config import EndpointConfig, AlertConfig

logger = logging.getLogger(__name__)


@dataclass
class CheckResult:
    """Result of a single endpoint health check."""

    endpoint_name: str
    url: str
    timestamp: datetime
    status_code: Optional[int] = None
    response_time_ms: Optional[float] = None
    success: bool = False
    error: Optional[str] = None
    threshold_breached: bool = False

    @property
    def is_healthy(self) -> bool:
        """Return True if the check passed without a threshold breach."""
        return self.success and not self.threshold_breached


def check_endpoint(
    endpoint: EndpointConfig,
    alert_config: AlertConfig,
    timeout: float = 10.0,
) -> CheckResult:
    """Perform a single HTTP check against the given endpoint.

    Args:
        endpoint: Configuration for the endpoint to check.
        alert_config: Alert thresholds and settings.
        timeout: Request timeout in seconds.

    Returns:
        A CheckResult capturing the outcome of the check.
    """
    now = datetime.now(tz=timezone.utc)
    result = CheckResult(
        endpoint_name=endpoint.name,
        url=endpoint.url,
        timestamp=now,
    )

    try:
        start = time.perf_counter()
        response = httpx.request(
            method=endpoint.method,
            url=endpoint.url,
            headers=endpoint.headers or {},
            timeout=timeout,
            follow_redirects=True,
        )
        elapsed_ms = (time.perf_counter() - start) * 1000

        result.status_code = response.status_code
        result.response_time_ms = round(elapsed_ms, 2)

        if response.status_code in endpoint.expected_status_codes:
            result.success = True
        else:
            result.error = (
                f"Unexpected status code {response.status_code}; "
                f"expected one of {endpoint.expected_status_codes}"
            )

        # Check response-time threshold
        if (
            result.success
            and alert_config.response_time_threshold_ms is not None
            and elapsed_ms > alert_config.response_time_threshold_ms
        ):
            result.threshold_breached = True
            logger.warning(
                "Threshold breached for %s: %.2f ms > %d ms",
                endpoint.name,
                elapsed_ms,
                alert_config.response_time_threshold_ms,
            )

    except httpx.TimeoutException as exc:
        result.error = f"Request timed out: {exc}"
        logger.error("Timeout checking %s: %s", endpoint.name, exc)
    except httpx.RequestError as exc:
        result.error = f"Request error: {exc}"
        logger.error("Error checking %s: %s", endpoint.name, exc)

    if result.success and not result.threshold_breached:
        logger.info(
            "OK  %s  %s  %s ms",
            endpoint.name,
            result.status_code,
            result.response_time_ms,
        )
    elif not result.success:
        logger.warning(
            "FAIL  %s  %s",
            endpoint.name,
            result.error,
        )

    return result
