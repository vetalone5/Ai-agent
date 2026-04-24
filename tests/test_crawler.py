"""Tests for the crawler HTML parsing logic."""

from src.tools.crawler import Crawler


def test_extract_domain():
    c = Crawler.__new__(Crawler)
    c._base_url = "https://spioniro.ru"
    assert c._is_same_domain("https://spioniro.ru/blog/test")
    assert not c._is_same_domain("https://google.com/test")


def test_slug_extraction():
    from src.agents.content_engine.seo_optimizer import _build_slug
    slug = _build_slug("Как работает GEO-оптимизация в 2026 году")
    assert slug.isascii()
    assert " " not in slug
    assert len(slug) > 5
