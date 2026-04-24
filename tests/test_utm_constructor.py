"""Tests for UTM link constructor."""

from src.config.constants import Platform
from src.tools.utm_constructor import build_article_utm_links, build_utm_url


def test_build_utm_url():
    url = build_utm_url(Platform.VC_RU, campaign="geo-optimization")
    assert "utm_source=vcru" in url
    assert "utm_medium=content" in url
    assert "utm_campaign=geo-optimization" in url


def test_build_utm_url_with_content():
    url = build_utm_url(Platform.DZEN, campaign="test", content="article-1")
    assert "utm_content=article-1" in url
    assert "utm_source=dzen" in url


def test_build_article_utm_links():
    links = build_article_utm_links("my-article", "geo optimization")
    assert "vcru" in links
    assert "dzen" in links
    assert "telegram" in links
    for platform, url in links.items():
        assert "utm_source=" in url
        assert "utm_campaign=" in url


def test_utm_slugifies_campaign():
    url = build_utm_url(Platform.HABR, campaign="GEO Оптимизация 2026")
    assert "geo-" in url.lower()
    assert " " not in url
