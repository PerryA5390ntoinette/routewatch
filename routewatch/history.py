"""In-memory ring-buffer for storing recent check results per URL."""

from collections import deque
from dataclasses import dataclass, field
from typing import Deque

from routewatch.monitor import CheckResult

DEFAULT_MAX_ENTRIES = 100


@dataclass
class EndpointHistory:
    """Stores the last *max_entries* results for a single endpoint."""

    url: str
    max_entries: int = DEFAULT_MAX_ENTRIES
    results: Deque[CheckResult] = field(default_factory=deque)

    def record(self, result: CheckResult) -> None:
        if len(self.results) >= self.max_entries:
            self.results.popleft()
        self.results.append(result)

    @property
    def latest(self) -> CheckResult | None:
        return self.results[-1] if self.results else None

    def average_response_time_ms(self) -> float | None:
        times = [
            r.response_time_ms
            for r in self.results
            if r.response_time_ms is not None
        ]
        return sum(times) / len(times) if times else None

    def error_rate(self) -> float:
        if not self.results:
            return 0.0
        failures = sum(1 for r in self.results if not r.is_healthy)
        return failures / len(self.results)

    def consecutive_failures(self) -> int:
        """Return the number of consecutive failures at the tail of results.

        Useful for alerting logic that should only trigger after N failures
        in a row rather than on isolated errors.
        """
        count = 0
        for result in reversed(self.results):
            if not result.is_healthy:
                count += 1
            else:
                break
        return count


class HistoryStore:
    """Container for per-endpoint history buffers."""

    def __init__(self, max_entries: int = DEFAULT_MAX_ENTRIES) -> None:
        self._max_entries = max_entries
        self._store: dict[str, EndpointHistory] = {}

    def record(self, result: CheckResult) -> None:
        if result.url not in self._store:
            self._store[result.url] = EndpointHistory(
                url=result.url, max_entries=self._max_entries
            )
        self._store[result.url].record(result)

    def get(self, url: str) -> EndpointHistory | None:
        return self._store.get(url)

    def all_urls(self) -> list[str]:
        return list(self._store.keys())

    def summary(self) -> list[dict]:
        rows = []
        for url, hist in self._store.items():
            rows.append(
                {
                    "url": url,
                    "checks": len(hist.results),
                    "avg_response_time_ms": hist.average_response_time_ms(),
                    "error_rate": hist.error_rate(),
                    "last_status": hist.latest.status_code if hist.latest else None,
                    "consecutive_failures": hist.consecutive_failures(),
                }
            )
        return rows
