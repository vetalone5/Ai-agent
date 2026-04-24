"""Tests for constants and configuration."""

from src.config.constants import (
    ANTIDETECT_FORBIDDEN_PHRASES,
    GEO_SCORING,
    AgentType,
    ContentType,
    GeoScore,
    Platform,
    SearchEngine,
    TaskPriority,
    TaskStatus,
)


def test_agent_types_complete():
    assert len(AgentType) == 7
    assert AgentType.ORCHESTRATOR == "orchestrator"
    assert AgentType.ANALYTICS == "analytics"


def test_task_lifecycle_states():
    states = [s.value for s in TaskStatus]
    assert "created" in states
    assert "running" in states
    assert "needs_approval" in states
    assert "completed" in states
    assert "error" in states


def test_content_types_count():
    assert len(ContentType) == 12


def test_geo_scoring_coverage():
    for ct in ContentType:
        assert ct in GEO_SCORING, f"Missing GEO score for {ct}"
    assert GEO_SCORING[ContentType.FAQ] == 5
    assert GEO_SCORING[ContentType.GLOSSARY] == 5
    assert GEO_SCORING[ContentType.GUIDE] == 4


def test_antidetect_phrases_not_empty():
    assert len(ANTIDETECT_FORBIDDEN_PHRASES) >= 20


def test_platforms():
    assert Platform.BLOG == "blog"
    assert Platform.VC_RU == "vcru"
    assert Platform.DZEN == "dzen"
