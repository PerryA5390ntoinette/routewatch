"""Endpoint tagging support — attach arbitrary string tags to endpoints
and filter/group results by tag at query time."""

from __future__ import annotations

from typing import Dict, Iterable, List

from routewatch.config import EndpointConfig
from routewatch.history import EndpointHistory


def tags_for(endpoint: EndpointConfig) -> List[str]:
    """Return the normalised tag list for an endpoint (may be empty)."""
    raw = getattr(endpoint, "tags", None) or []
    return [t.strip().lower() for t in raw if t.strip()]


def endpoint_has_tag(endpoint: EndpointConfig, tag: str) -> bool:
    """Return True if *endpoint* carries *tag* (case-insensitive)."""
    return tag.strip().lower() in tags_for(endpoint)


def filter_by_tag(
    endpoints: Iterable[EndpointConfig],
    tag: str,
) -> List[EndpointConfig]:
    """Return only the endpoints that carry *tag*."""
    return [ep for ep in endpoints if endpoint_has_tag(ep, tag)]


def group_by_tag(
    endpoints: Iterable[EndpointConfig],
) -> Dict[str, List[EndpointConfig]]:
    """Return a mapping of tag -> list of endpoints that carry that tag.

    Endpoints with multiple tags appear under each of their tags.
    Endpoints with no tags appear under the empty-string key ``""``.
    """
    groups: Dict[str, List[EndpointConfig]] = {}
    for ep in endpoints:
        ep_tags = tags_for(ep)
        if not ep_tags:
            groups.setdefault("", []).append(ep)
        else:
            for t in ep_tags:
                groups.setdefault(t, []).append(ep)
    return groups


def filter_histories_by_tag(
    endpoints: List[EndpointConfig],
    histories: Dict[str, EndpointHistory],
    tag: str,
) -> Dict[str, EndpointHistory]:
    """Return the subset of *histories* whose endpoint carries *tag*."""
    matched_urls = {ep.url for ep in filter_by_tag(endpoints, tag)}
    return {url: h for url, h in histories.items() if url in matched_urls}
