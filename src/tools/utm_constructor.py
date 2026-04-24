"""UTM link constructor for tracking content performance across platforms."""

from urllib.parse import urlencode, urlparse, urlunparse

from src.config.constants import Platform
from src.config.settings import settings

PLATFORM_SOURCE_MAP: dict[Platform, str] = {
    Platform.BLOG: "blog",
    Platform.VC_RU: "vcru",
    Platform.DZEN: "dzen",
    Platform.HABR: "habr",
    Platform.TELEGRAM: "telegram",
    Platform.YANDEX_KYU: "yandex_kyu",
}


def build_utm_url(
    platform: Platform,
    campaign: str,
    content: str = "",
    base_url: str | None = None,
    path: str = "",
) -> str:
    """Build a full UTM-tagged URL."""
    base = base_url or settings.target_site_url
    source = PLATFORM_SOURCE_MAP.get(platform, platform.value)

    params = {
        "utm_source": source,
        "utm_medium": "content",
        "utm_campaign": _slugify(campaign),
    }
    if content:
        params["utm_content"] = _slugify(content)

    parsed = urlparse(base)
    url = urlunparse((parsed.scheme, parsed.netloc, path or parsed.path, "", urlencode(params), ""))
    return url


def build_article_utm_links(
    article_slug: str,
    keyword: str,
    platforms: list[Platform] | None = None,
) -> dict[str, str]:
    """Build UTM links for all target platforms for an article."""
    if platforms is None:
        platforms = [Platform.VC_RU, Platform.DZEN, Platform.TELEGRAM]

    links: dict[str, str] = {}
    for platform in platforms:
        links[platform.value] = build_utm_url(
            platform=platform,
            campaign=keyword,
            content=article_slug,
            path=f"/blog/{article_slug}",
        )
    return links


def _slugify(text: str) -> str:
    return text.lower().replace(" ", "-").replace("_", "-")[:50]
