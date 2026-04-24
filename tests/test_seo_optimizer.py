"""Tests for SEO optimizer: meta generation, slug, keyword checks."""

from src.agents.content_engine.seo_optimizer import (
    check_seo_quality,
    generate_meta,
)


def test_generate_meta_basic():
    meta = generate_meta(
        title="Что такое GEO-оптимизация",
        keyword="geo оптимизация",
        content_type="guide",
        article_text="Some text about geo optimization...",
    )
    assert "meta_title" in meta
    assert "meta_description" in meta
    assert "slug" in meta
    assert "h1" in meta
    assert len(meta["meta_title"]) <= 70
    assert len(meta["meta_description"]) <= 170


def test_slug_transliteration():
    meta = generate_meta(
        title="Как работает аналитика AI-упоминаний",
        keyword="аналитика ai упоминаний",
        content_type="guide",
        article_text="",
    )
    slug = meta["slug"]
    assert slug.isascii()
    assert " " not in slug
    assert "--" not in slug


def test_slug_no_cyrillic():
    meta = generate_meta(
        title="Сервис для мониторинга и аналитики",
        keyword="мониторинг",
        content_type="guide",
        article_text="",
    )
    slug = meta["slug"]
    assert slug.isascii()
    assert len(slug) > 5


def test_h1_not_equal_title():
    meta = generate_meta(
        title="GEO оптимизация",
        keyword="GEO оптимизация",
        content_type="guide",
        article_text="",
    )
    assert meta["h1"] != meta["meta_title"] or "руководство" in meta["h1"]


def test_seo_quality_check_few_links():
    issues = check_seo_quality({
        "content_md": "Just some text without any links at all. " * 100,
        "marker_keyword": "test keyword",
        "meta_title": "Test Title",
        "meta_description": "Test description",
        "h1": "Test H1",
    })
    issue_types = [i["type"] for i in issues]
    assert "few_internal_links" in issue_types


def test_seo_quality_keyword_density():
    text = "GEO оптимизация — важная тема. " + "Другой текст о разных вещах и идеях для бизнеса. " * 200
    issues = check_seo_quality({
        "content_md": text,
        "marker_keyword": "geo оптимизация",
        "meta_title": "GEO оптимизация: руководство",
        "meta_description": "Полное руководство по GEO",
        "h1": "Руководство по GEO оптимизации",
    })
    # Should not have spam-level density
    spam_issues = [i for i in issues if i["type"] == "high_keyword_density"]
    assert len(spam_issues) == 0
