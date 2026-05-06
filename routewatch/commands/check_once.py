"""check_once command – run a single check pass and print results immediately."""

from __future__ import annotations

import sys
from io import TextIOBase
from typing import Dict

from routewatch.config import AppConfig
from routewatch.monitor import check_endpoint, is_healthy
from routewatch.history import EndpointHistory, record
from routewatch.notifier import NotifierState, evaluate_and_notify


_STATUS_SYMBOL: Dict[bool, str] = {True: "✓", False: "✗"}


def run_check_once(
    config: AppConfig,
    histories: Dict[str, EndpointHistory],
    states: Dict[str, NotifierState],
    *,
    out: TextIOBase = sys.stdout,
    notify: bool = True,
) -> int:
    """Perform one check per configured endpoint, print a summary line for each.

    Returns the number of unhealthy endpoints found (0 = all OK).
    """
    failures = 0

    for endpoint in config.endpoints:
        result = check_endpoint(endpoint)
        record(histories[endpoint.url], result)

        healthy = is_healthy(result, endpoint)
        symbol = _STATUS_SYMBOL[healthy]
        rt = f"{result.response_time_ms:.0f} ms" if result.response_time_ms is not None else "N/A"
        status_code = result.status_code if result.status_code is not None else "ERR"

        out.write(f"{symbol}  {endpoint.url}  [{status_code}]  {rt}\n")

        if not healthy:
            failures += 1
            if result.error:
                out.write(f"   error: {result.error}\n")

        if notify:
            evaluate_and_notify(
                endpoint,
                config.alert,
                histories[endpoint.url],
                states[endpoint.url],
            )

    out.write(f"\n{len(config.endpoints)} endpoint(s) checked, {failures} unhealthy.\n")
    return failures
