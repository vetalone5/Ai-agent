"""Tests for knowledge graph client."""

import pytest

from src.tools.knowledge_graph import KnowledgeGraphClient


@pytest.mark.asyncio
async def test_verify_consistency():
    kg = KnowledgeGraphClient()
    result = await kg.verify_consistency("Spioniro", "https://spioniro.ru")
    assert result["brand"] == "Spioniro"
    assert "wikidata" in result["checks"]
    assert "google_business" in result["checks"]
    assert "recommendation" in result
