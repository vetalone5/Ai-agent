"""Tests for content auto-updater logic."""

from src.agents.content_engine.auto_updater import (
    POSITION_DROP_THRESHOLD,
    STALE_CONTENT_DAYS,
    TRAFFIC_DROP_THRESHOLD,
)


def test_thresholds_reasonable():
    assert POSITION_DROP_THRESHOLD >= 3
    assert POSITION_DROP_THRESHOLD <= 10
    assert TRAFFIC_DROP_THRESHOLD >= 20
    assert TRAFFIC_DROP_THRESHOLD <= 50
    assert STALE_CONTENT_DAYS >= 90
    assert STALE_CONTENT_DAYS <= 365
