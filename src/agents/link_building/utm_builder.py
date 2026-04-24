"""UTM builder for link building campaigns."""

from src.config.constants import Platform
from src.tools.utm_constructor import build_article_utm_links, build_utm_url


class UTMBuilder:
    """Builds UTM-tagged links for link building campaigns."""

    def build_for_article(self, article_slug: str, keyword: str) -> dict[str, str]:
        return build_article_utm_links(article_slug, keyword)

    def build_for_outreach(self, target_platform: str, campaign: str) -> str:
        platform_map = {
            "vcru": Platform.VC_RU,
            "dzen": Platform.DZEN,
            "habr": Platform.HABR,
            "telegram": Platform.TELEGRAM,
            "yandex_kyu": Platform.YANDEX_KYU,
        }
        platform = platform_map.get(target_platform, Platform.BLOG)
        return build_utm_url(platform=platform, campaign=campaign)
