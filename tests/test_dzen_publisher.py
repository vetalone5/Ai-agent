"""Tests for Dzen publisher content adaptation."""

from src.tools.dzen_publisher import DzenPublisher


def test_adapt_for_dzen_shortens_paragraphs():
    pub = DzenPublisher()
    article = {
        "title": "Тестовая статья",
        "content_md": "## Введение\n\nПервое предложение. Второе предложение. Третье предложение. Четвертое предложение.\n\n## Раздел\n\nЕщё текст.",
        "published_url": "https://spioniro.ru/blog/test",
    }
    adapted = pub._adapt_for_dzen(article)
    assert adapted["title"] == "Тестовая статья"
    assert "utm_source=dzen" in adapted["content"]
    paragraphs = [p for p in adapted["content"].split("\n\n") if p.strip()]
    for p in paragraphs:
        if not p.startswith("#") and not p.startswith("---"):
            assert len(p.split(". ")) <= 3 or len(p) < 300


def test_adapt_adds_cta_link():
    pub = DzenPublisher()
    article = {
        "title": "Заголовок",
        "content_md": "Текст статьи.",
        "published_url": "https://spioniro.ru/blog/slug",
    }
    adapted = pub._adapt_for_dzen(article)
    assert "spioniro.ru" in adapted["content"]
    assert "utm_source=dzen" in adapted["content"]
