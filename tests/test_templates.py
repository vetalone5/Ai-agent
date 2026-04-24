"""Tests for content templates."""

from src.agents.content_engine.templates import TEMPLATES, get_template
from src.config.constants import ContentType


def test_all_content_types_have_templates():
    for ct in ContentType:
        template = get_template(ct)
        assert template is not None, f"No template for {ct}"
        assert "name" in template
        assert "structure" in template
        assert "word_range" in template
        assert "prompt_hint" in template


def test_word_ranges_valid():
    for ct, template in TEMPLATES.items():
        word_min, word_max = template["word_range"]
        assert word_min > 0
        assert word_max > word_min
        assert word_max <= 6000


def test_structures_not_empty():
    for ct, template in TEMPLATES.items():
        assert len(template["structure"]) >= 3, f"Template {ct} has too few sections"


def test_faq_template():
    t = get_template(ContentType.FAQ)
    assert "FAQ" in t["name"] or "Вопросы" in t["name"]
    assert t["word_range"][0] >= 1000


def test_glossary_template():
    t = get_template(ContentType.GLOSSARY)
    assert "Глоссарий" in t["name"]
    assert "AI" in t["prompt_hint"] or "терм" in t["prompt_hint"].lower()
