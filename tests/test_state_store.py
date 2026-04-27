"""Tests for routewatch/state_store.py."""

from __future__ import annotations

import pytest

from routewatch.config import AlertConfig, AppConfig, EndpointConfig
from routewatch.history import EndpointHistory
from routewatch.notifier import NotifierState
from routewatch.state_store import build_stores


@pytest.fixture()
def two_endpoint_config():
    return AppConfig(
        endpoints=[
            EndpointConfig(url="https://a.example", timeout_s=5.0, slow_threshold_ms=300),
            EndpointConfig(url="https://b.example", timeout_s=5.0, slow_threshold_ms=300),
        ],
        alert=AlertConfig(webhook_url="https://hook.example", cooldown_s=60),
        interval_s=10,
        history_size=25,
    )


def test_build_stores_returns_entry_per_endpoint(two_endpoint_config):
    histories, states = build_stores(two_endpoint_config)
    assert set(histories.keys()) == {"https://a.example", "https://b.example"}
    assert set(states.keys()) == {"https://a.example", "https://b.example"}


def test_build_stores_history_type(two_endpoint_config):
    histories, _ = build_stores(two_endpoint_config)
    for h in histories.values():
        assert isinstance(h, EndpointHistory)


def test_build_stores_state_type(two_endpoint_config):
    _, states = build_stores(two_endpoint_config)
    for s in states.values():
        assert isinstance(s, NotifierState)


def test_build_stores_history_max_size(two_endpoint_config):
    histories, _ = build_stores(two_endpoint_config)
    for h in histories.values():
        assert h.max_size == two_endpoint_config.history_size


def test_build_stores_history_url(two_endpoint_config):
    histories, _ = build_stores(two_endpoint_config)
    for url, h in histories.items():
        assert h.url == url


def test_build_stores_empty_endpoints():
    cfg = AppConfig(
        endpoints=[],
        alert=AlertConfig(webhook_url="https://hook.example", cooldown_s=60),
        interval_s=10,
        history_size=50,
    )
    histories, states = build_stores(cfg)
    assert histories == {}
    assert states == {}
