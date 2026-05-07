"""Tests for routewatch.tagging."""

from __future__ import annotations

import pytest

from routewatch.config import EndpointConfig
from routewatch.tagging import (
    endpoint_has_tag,
    filter_by_tag,
    filter_histories_by_tag,
    group_by_tag,
    tags_for,
)


def _ep(url: str, tags=None) -> EndpointConfig:
    return EndpointConfig(url=url, tags=tags or [])


# ---------------------------------------------------------------------------
# tags_for
# ---------------------------------------------------------------------------

def test_tags_for_empty():
    assert tags_for(_ep("http://a")) == []


def test_tags_for_normalises_case():
    ep = _ep("http://a", tags=["Prod", "EU"])
    assert tags_for(ep) == ["prod", "eu"]


def test_tags_for_strips_whitespace():
    ep = _ep("http://a", tags=["  web  ", " api"])
    assert tags_for(ep) == ["web", "api"]


def test_tags_for_ignores_blank_entries():
    ep = _ep("http://a", tags=["", "  ", "valid"])
    assert tags_for(ep) == ["valid"]


# ---------------------------------------------------------------------------
# endpoint_has_tag
# ---------------------------------------------------------------------------

def test_endpoint_has_tag_true():
    ep = _ep("http://a", tags=["prod"])
    assert endpoint_has_tag(ep, "PROD") is True


def test_endpoint_has_tag_false():
    ep = _ep("http://a", tags=["staging"])
    assert endpoint_has_tag(ep, "prod") is False


def test_endpoint_has_tag_no_tags():
    assert endpoint_has_tag(_ep("http://a"), "prod") is False


# ---------------------------------------------------------------------------
# filter_by_tag
# ---------------------------------------------------------------------------

def test_filter_by_tag_returns_matching():
    eps = [_ep("http://a", ["prod"]), _ep("http://b", ["staging"]), _ep("http://c", ["prod", "eu"])]
    result = filter_by_tag(eps, "prod")
    urls = [ep.url for ep in result]
    assert urls == ["http://a", "http://c"]


def test_filter_by_tag_empty_when_no_match():
    eps = [_ep("http://a", ["staging"])]
    assert filter_by_tag(eps, "prod") == []


# ---------------------------------------------------------------------------
# group_by_tag
# ---------------------------------------------------------------------------

def test_group_by_tag_single_tag():
    eps = [_ep("http://a", ["prod"]), _ep("http://b", ["staging"])]
    groups = group_by_tag(eps)
    assert [ep.url for ep in groups["prod"]] == ["http://a"]
    assert [ep.url for ep in groups["staging"]] == ["http://b"]


def test_group_by_tag_multi_tag_appears_in_each():
    ep = _ep("http://a", ["prod", "eu"])
    groups = group_by_tag([ep])
    assert ep in groups["prod"]
    assert ep in groups["eu"]


def test_group_by_tag_no_tags_uses_empty_key():
    ep = _ep("http://a")
    groups = group_by_tag([ep])
    assert ep in groups[""]


# ---------------------------------------------------------------------------
# filter_histories_by_tag
# ---------------------------------------------------------------------------

def test_filter_histories_by_tag():
    from routewatch.history import EndpointHistory

    ep_prod = _ep("http://prod", ["prod"])
    ep_staging = _ep("http://staging", ["staging"])
    histories = {
        "http://prod": EndpointHistory(max_size=10),
        "http://staging": EndpointHistory(max_size=10),
    }
    result = filter_histories_by_tag([ep_prod, ep_staging], histories, "prod")
    assert list(result.keys()) == ["http://prod"]
