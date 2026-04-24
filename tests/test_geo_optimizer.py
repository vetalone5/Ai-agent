"""Tests for GEO optimization quality checks."""

from src.agents.content_engine.geo_optimizer import build_geo_instructions, check_geo_quality


def test_geo_instructions_scale():
    low = build_geo_instructions(1, "guide")
    high = build_geo_instructions(5, "faq")
    assert len(high) > len(low)
    assert "answer-first" in low.lower() or "минимальная" in low.lower()
    assert "ОБЯЗАТЕЛЬНО" in high or "максимальная" in high.lower()


def test_geo_check_no_faq():
    text = "## Введение\nТекст без FAQ-секции.\n\n## Заключение\nКонец."
    issues = check_geo_quality(text, geo_score=3)
    types = [i["type"] for i in issues]
    assert "no_faq" in types


def test_geo_check_low_fact_density():
    text = "## Раздел\n" + "Просто текст без цифр и фактов. " * 100
    issues = check_geo_quality(text, geo_score=4)
    types = [i["type"] for i in issues]
    assert "low_fact_density" in types


def test_geo_high_score_answer_first():
    text = "## Что такое GEO?\n\nНу давайте разберёмся.\n\n## Зачем нужна?\n\nТоже непонятно."
    issues = check_geo_quality(text, geo_score=4)
    answer_issues = [i for i in issues if i["type"] == "no_answer_first"]
    assert len(answer_issues) >= 1
