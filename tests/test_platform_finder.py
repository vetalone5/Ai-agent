"""Tests for platform finder constants."""

from src.agents.link_building.platform_finder import CONTENT_PLATFORMS, RUSSIAN_EXCHANGES


def test_exchanges_defined():
    assert len(RUSSIAN_EXCHANGES) >= 5
    names = [e["name"] for e in RUSSIAN_EXCHANGES]
    assert "GoGetLinks" in names
    assert "Miralinks" in names


def test_content_platforms_defined():
    assert len(CONTENT_PLATFORMS) >= 5
    domains = [p["domain"] for p in CONTENT_PLATFORMS]
    assert "vc.ru" in domains
    assert "dzen.ru" in domains
    assert "habr.com" in domains


def test_platforms_have_da():
    for p in CONTENT_PLATFORMS:
        assert "da" in p
        assert p["da"] >= 70
