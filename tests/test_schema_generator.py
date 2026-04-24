"""Tests for JSON-LD schema generation."""

import json

from src.agents.technical_seo.schema_generator import SchemaGenerator


def _make_article(**overrides):
    base = {
        "title": "Что такое GEO-оптимизация",
        "slug": "chto-takoe-geo-optimizatsiya",
        "h1": "GEO-оптимизация: полное руководство",
        "meta_title": "GEO-оптимизация для бизнеса в 2026",
        "meta_description": "Узнайте как оптимизировать контент для нейросетей",
        "content_md": "## Введение\nТекст.\n\n### Что такое GEO?\nОтвет на вопрос.\n\n### Зачем нужна?\nОтвет.",
        "word_count": 2500,
        "content_type": "guide",
        "marker_keyword": "geo оптимизация",
    }
    base.update(overrides)
    return base


def test_article_schema():
    gen = SchemaGenerator()
    schemas = gen.generate(_make_article())
    article_schema = next(s for s in schemas if s.get("@type") == "BlogPosting")
    assert article_schema["@context"] == "https://schema.org"
    assert "headline" in article_schema
    assert "author" in article_schema
    assert article_schema["inLanguage"] == "ru-RU"


def test_faq_schema():
    gen = SchemaGenerator()
    article = _make_article(content_type="faq")
    schemas = gen.generate(article)
    faq = next((s for s in schemas if s.get("@type") == "FAQPage"), None)
    assert faq is not None
    assert "mainEntity" in faq


def test_howto_schema():
    gen = SchemaGenerator()
    article = _make_article(content_type="guide")
    schemas = gen.generate(article)
    howto = next((s for s in schemas if s.get("@type") == "HowTo"), None)
    assert howto is not None
    assert "step" in howto


def test_breadcrumb_always_present():
    gen = SchemaGenerator()
    schemas = gen.generate(_make_article())
    breadcrumb = next((s for s in schemas if s.get("@type") == "BreadcrumbList"), None)
    assert breadcrumb is not None
    assert len(breadcrumb["itemListElement"]) == 3


def test_organization_always_present():
    gen = SchemaGenerator()
    schemas = gen.generate(_make_article())
    org = next((s for s in schemas if s.get("@type") == "Organization"), None)
    assert org is not None


def test_to_script_tags():
    gen = SchemaGenerator()
    schemas = gen.generate(_make_article())
    html = gen.to_script_tags(schemas)
    assert "application/ld+json" in html
    assert html.count("<script") == len(schemas)


def test_review_schema():
    gen = SchemaGenerator()
    schemas = gen.generate(_make_article(content_type="review"))
    review = next((s for s in schemas if s.get("@type") == "Review"), None)
    assert review is not None


def test_itemlist_schema():
    gen = SchemaGenerator()
    schemas = gen.generate(_make_article(content_type="rating"))
    itemlist = next((s for s in schemas if s.get("@type") == "ItemList"), None)
    assert itemlist is not None
