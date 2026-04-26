"""Configuration management for RouteWatch.

Loads and validates settings from environment variables or a config file.
"""

import os
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class EndpointConfig:
    """Configuration for a single monitored endpoint."""

    url: str
    name: str
    method: str = "GET"
    timeout_seconds: float = 10.0
    # Alert if response time exceeds this value (milliseconds)
    response_time_threshold_ms: float = 2000.0
    # Alert if status code is not in this list
    expected_status_codes: List[int] = field(default_factory=lambda: [200])
    # Optional headers to include in the request
    headers: dict = field(default_factory=dict)


@dataclass
class AlertConfig:
    """Configuration for alert delivery."""

    webhook_url: str
    # Minimum seconds between repeated alerts for the same endpoint
    cooldown_seconds: int = 300
    # Number of consecutive failures before alerting
    failure_threshold: int = 1


@dataclass
class AppConfig:
    """Top-level application configuration."""

    endpoints: List[EndpointConfig]
    alert: AlertConfig
    # How often to poll endpoints (seconds)
    poll_interval_seconds: int = 60
    # Log level: DEBUG, INFO, WARNING, ERROR
    log_level: str = "INFO"


def load_config_from_env() -> AppConfig:
    """Build a minimal AppConfig from environment variables.

    Useful for quick single-endpoint monitoring without a config file.
    Expects:
        ROUTEWATCH_URL          - endpoint URL to monitor (required)
        ROUTEWATCH_WEBHOOK_URL  - webhook URL for alerts (required)
        ROUTEWATCH_NAME         - friendly name for the endpoint
        ROUTEWATCH_THRESHOLD_MS - response time threshold in ms
        ROUTEWATCH_POLL_INTERVAL - poll interval in seconds
        ROUTEWATCH_LOG_LEVEL    - log level string
    """
    url = os.environ.get("ROUTEWATCH_URL")
    webhook_url = os.environ.get("ROUTEWATCH_WEBHOOK_URL")

    if not url:
        raise ValueError("ROUTEWATCH_URL environment variable is required.")
    if not webhook_url:
        raise ValueError("ROUTEWATCH_WEBHOOK_URL environment variable is required.")

    endpoint = EndpointConfig(
        url=url,
        name=os.environ.get("ROUTEWATCH_NAME", url),
        response_time_threshold_ms=float(
            os.environ.get("ROUTEWATCH_THRESHOLD_MS", 2000.0)
        ),
    )

    alert = AlertConfig(
        webhook_url=webhook_url,
        cooldown_seconds=int(os.environ.get("ROUTEWATCH_COOLDOWN", 300)),
        failure_threshold=int(os.environ.get("ROUTEWATCH_FAILURE_THRESHOLD", 1)),
    )

    return AppConfig(
        endpoints=[endpoint],
        alert=alert,
        poll_interval_seconds=int(os.environ.get("ROUTEWATCH_POLL_INTERVAL", 60)),
        log_level=os.environ.get("ROUTEWATCH_LOG_LEVEL", "INFO").upper(),
    )


def validate_config(config: AppConfig) -> None:
    """Raise ValueError if the config contains invalid values."""
    if not config.endpoints:
        raise ValueError("At least one endpoint must be configured.")

    for ep in config.endpoints:
        if not ep.url.startswith(("http://", "https://")):
            raise ValueError(f"Endpoint URL must start with http:// or https://: {ep.url}")
        if ep.timeout_seconds <= 0:
            raise ValueError(f"Timeout must be positive for endpoint: {ep.name}")
        if ep.response_time_threshold_ms <= 0:
            raise ValueError(f"Response time threshold must be positive for endpoint: {ep.name}")

    if not config.alert.webhook_url.startswith(("http://", "https://")):
        raise ValueError("Alert webhook URL must start with http:// or https://")

    if config.poll_interval_seconds <= 0:
        raise ValueError("Poll interval must be a positive integer.")
