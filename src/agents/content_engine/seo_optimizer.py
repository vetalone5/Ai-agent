"""SEO optimization: meta tags, internal links, keyword density."""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

SEO_RULES_PROMPT = """Правила SEO-оптимизации (2026):

Title: до 60 символов, ключевик в начале или середине, не дублирует H1.
Description: до 160 символов, НЕ дублирует Title, содержит CTA (узнайте, попробуйте).
H1: один на страницу, содержит ключевик, ≠ Title.
Ключевые слова: 5-8 раз на 3000 слов основной ключ + синонимы и LSI.
Внутренние ссылки: 2-5 штук с естественными анкорами (не «тут», не «здесь»).
Schema.org: BlogPosting, FAQPage, HowTo — зависит от типа.
URL: транслитерация, через дефис, до 60 символов, без стоп-слов.
"""


def generate_meta(
    title: str,
    keyword: str,
    content_type: str,
    article_text: str,
) -> dict[str, str]:
    """Generate meta title, description, and slug."""
    meta_title = _build_meta_title(title, keyword)
    meta_description = _build_meta_description(keyword, content_type)
    slug = _build_slug(title)
    h1 = _build_h1(title, keyword)

    return {
        "meta_title": meta_title[:70],
        "meta_description": meta_description[:170],
        "slug": slug[:60],
        "h1": h1,
    }


def check_seo_quality(article: dict[str, Any]) -> list[dict[str, str]]:
    """Check article for SEO issues."""
    issues = []
    content = article.get("content_md", "")
    keyword = article.get("marker_keyword", "")
    meta_title = article.get("meta_title", "")
    meta_desc = article.get("meta_description", "")
    h1 = article.get("h1", "")
    word_count = len(content.split())

    if len(meta_title) > 70:
        issues.append({"type": "title_too_long", "detail": f"{len(meta_title)} chars"})
    if len(meta_desc) > 170:
        issues.append({"type": "desc_too_long", "detail": f"{len(meta_desc)} chars"})
    if keyword and keyword.lower() not in meta_title.lower():
        issues.append({"type": "keyword_not_in_title", "detail": keyword})
    if meta_title == h1:
        issues.append({"type": "title_equals_h1", "detail": "Title and H1 are identical"})
    if meta_title.lower() in meta_desc.lower():
        issues.append({"type": "desc_duplicates_title", "detail": "Description contains full Title"})

    if keyword and word_count > 0:
        count = content.lower().count(keyword.lower())
        density = count / (word_count / 1000)
        if density < 1.5:
            issues.append({"type": "low_keyword_density", "detail": f"{density:.1f} per 1000 words"})
        elif density > 4.0:
            issues.append({"type": "high_keyword_density", "detail": f"{density:.1f} per 1000 words (spam risk)"})

    internal_links = re.findall(r'\[([^\]]+)\]\(/[^)]+\)', content)
    if len(internal_links) < 2:
        issues.append({"type": "few_internal_links", "detail": f"Only {len(internal_links)} internal links"})
    bad_anchors = [a for a in internal_links if a.lower() in ("тут", "здесь", "ссылка", "click here")]
    if bad_anchors:
        issues.append({"type": "bad_anchors", "detail": f"Bad anchors: {bad_anchors}"})

    h2_count = content.count("## ")
    if h2_count < 3 and word_count > 1000:
        issues.append({"type": "few_h2", "detail": f"Only {h2_count} H2 headings"})

    return issues


def _build_meta_title(title: str, keyword: str) -> str:
    if keyword.lower() in title.lower():
        return title[:60]
    short_title = title[:40]
    return f"{keyword} — {short_title}"


def _build_meta_description(keyword: str, content_type: str) -> str:
    cta_map = {
        "guide": "Пошаговое руководство",
        "review": "Подробный обзор",
        "rating": "Рейтинг лучших",
        "comparison": "Детальное сравнение",
        "faq": "Ответы на вопросы",
        "glossary": "Словарь терминов",
    }
    cta = cta_map.get(content_type, "Полное руководство")
    return f"{cta}: {keyword}. Узнайте всё что нужно — с примерами и рекомендациями экспертов."


def _build_slug(title: str) -> str:
    translit_map = {
        "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "yo",
        "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
        "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
        "ф": "f", "х": "kh", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "shch",
        "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
    }
    stop_words = {"и", "в", "на", "с", "по", "для", "от", "к", "из", "не", "что", "как", "это"}
    slug = title.lower()
    result = []
    for char in slug:
        if char in translit_map:
            result.append(translit_map[char])
        elif char.isascii() and char.isalnum():
            result.append(char)
        elif char in (" ", "-", "_"):
            result.append("-")
    slug = "".join(result)
    slug = re.sub(r'-+', '-', slug).strip('-')
    words = slug.split('-')
    words = [w for w in words if w not in stop_words]
    return "-".join(words)


def _build_h1(title: str, keyword: str) -> str:
    if title == keyword:
        return f"{title}: полное руководство"
    return title
