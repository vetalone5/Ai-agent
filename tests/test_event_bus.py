"""Tests for the event bus."""

import pytest

from src.core.event_bus import EventBus


@pytest.mark.asyncio
async def test_publish_subscribe():
    bus = EventBus()
    received = []

    async def handler(**data):
        received.append(data)

    bus.subscribe("test.event", handler)
    await bus.publish("test.event", key="value")

    assert len(received) == 1
    assert received[0]["key"] == "value"


@pytest.mark.asyncio
async def test_multiple_handlers():
    bus = EventBus()
    results = []

    async def handler_a(**data):
        results.append("a")

    async def handler_b(**data):
        results.append("b")

    bus.subscribe("multi", handler_a)
    bus.subscribe("multi", handler_b)
    await bus.publish("multi")

    assert "a" in results
    assert "b" in results


@pytest.mark.asyncio
async def test_unsubscribe():
    bus = EventBus()
    received = []

    async def handler(**data):
        received.append(1)

    bus.subscribe("unsub", handler)
    bus.unsubscribe("unsub", handler)
    await bus.publish("unsub")

    assert len(received) == 0


@pytest.mark.asyncio
async def test_handler_error_isolation():
    bus = EventBus()
    results = []

    async def bad_handler(**data):
        raise RuntimeError("boom")

    async def good_handler(**data):
        results.append("ok")

    bus.subscribe("err", bad_handler)
    bus.subscribe("err", good_handler)
    await bus.publish("err")

    assert results == ["ok"]
