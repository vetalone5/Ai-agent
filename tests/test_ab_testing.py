"""Tests for A/B testing constants."""

from src.agents.content_engine.ab_testing import (
    CTR_IMPROVEMENT_THRESHOLD,
    MIN_IMPRESSIONS_FOR_TEST,
    MIN_TEST_DURATION_DAYS,
)


def test_ab_test_constraints():
    assert MIN_IMPRESSIONS_FOR_TEST >= 50
    assert MIN_TEST_DURATION_DAYS >= 7
    assert CTR_IMPROVEMENT_THRESHOLD > 0
