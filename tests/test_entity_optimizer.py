"""Tests for entity optimizer."""

import pytest

from src.agents.ai_visibility.entity_optimizer import EntityOptimizer


@pytest.mark.asyncio
async def test_audit_entity_presence():
    optimizer = EntityOptimizer(claude_client=None)
    result = await optimizer.audit_entity_presence()
    assert result["brand"] == "spioniro"
    assert "wikidata" in result["sources"]
    assert "google_business" in result["sources"]


@pytest.mark.asyncio
async def test_generate_organization_schema():
    optimizer = EntityOptimizer(claude_client=None)
    schema = await optimizer.generate_organization_schema()
    assert schema["@type"] == "Organization"
    assert schema["name"] == "Spioniro"
    assert schema["url"] == "https://spioniro.ru"
    assert "knowsAbout" in schema
    assert "AI Brand Analytics" in schema["knowsAbout"]
