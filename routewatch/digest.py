"""Periodic digest: summarise endpoint health across a time window."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List

from routewatch.history import EndpointHistory, average_response_time_ms, error_rate
from routewatch.scoring import HealthScore, compute_score
from routewatch.config import EndpointConfig


@dataclass
class DigestEntry:
    url: str
    total_checks: int
    error_rate_pct: float
    avg_response_ms: float | None
    score: HealthScore | None
    grade: str | None


@dataclass
class Digest:
    generated_at: str
    window_label: str
    entries: List[DigestEntry]

    @property
    def healthy_count(self) -> int:
        return sum(1 for e in self.entries if (e.grade or "F") not in ("D", "F"))

    @property
    def degraded_count(self) -> int:
        return len(self.entries) - self.healthy_count


def _build_entry(endpoint: EndpointConfig, history: EndpointHistory) -> DigestEntry:
    score = compute_score(endpoint, history)
    avg = average_response_time_ms(history)
    er = error_rate(history)
    return DigestEntry(
        url=endpoint.url,
        total_checks=len(history.results),
        error_rate_pct=round(er * 100, 2),
        avg_response_ms=round(avg, 2) if avg is not None else None,
        score=score,
        grade=score.grade if score else None,
    )


def build_digest(
    endpoints: List[EndpointConfig],
    histories: Dict[str, EndpointHistory],
    window_label: str = "recent",
) -> Digest:
    entries = [
        _build_entry(ep, histories[ep.url])
        for ep in endpoints
        if ep.url in histories
    ]
    return Digest(
        generated_at=datetime.now(timezone.utc).isoformat(),
        window_label=window_label,
        entries=entries,
    )


def format_digest_text(digest: Digest) -> str:
    lines: List[str] = [
        f"=== RouteWatch Digest ({digest.window_label}) ===",
        f"Generated : {digest.generated_at}",
        f"Endpoints : {len(digest.entries)}  "
        f"Healthy: {digest.healthy_count}  Degraded: {digest.degraded_count}",
        "",
        f"{'URL':<40} {'Checks':>7} {'Err%':>7} {'Avg ms':>9} {'Grade':>6}",
        "-" * 73,
    ]
    for e in digest.entries:
        avg = f"{e.avg_response_ms:.1f}" if e.avg_response_ms is not None else "n/a"
        lines.append(
            f"{e.url:<40} {e.total_checks:>7} {e.error_rate_pct:>7.1f} {avg:>9} {(e.grade or 'n/a'):>6}"
        )
    return "\n".join(lines)
