"""Sitemap.xml and robots.txt generation and management."""

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

from src.config.settings import settings
from src.models.article import Article

logger = logging.getLogger(__name__)


class SitemapManager:
    def __init__(self, session_factory: Any) -> None:
        self._session_factory = session_factory

    async def generate_sitemap(self) -> str:
        """Generate sitemap.xml content from published articles."""
        articles = await self._get_published_articles()

        urls = [
            {"loc": settings.target_site_url, "priority": "1.0", "changefreq": "daily"},
            {"loc": f"{settings.target_site_url}/blog", "priority": "0.9", "changefreq": "daily"},
        ]

        for article in articles:
            urls.append({
                "loc": f"{settings.target_site_url}/blog/{article['slug']}",
                "lastmod": article.get("updated_at", article.get("published_at", "")),
                "priority": "0.8" if article.get("geo_score", 0) >= 4 else "0.7",
                "changefreq": "weekly",
            })

        xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
        xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        for url in urls:
            xml += "  <url>\n"
            xml += f"    <loc>{url['loc']}</loc>\n"
            if url.get("lastmod"):
                xml += f"    <lastmod>{url['lastmod']}</lastmod>\n"
            xml += f"    <changefreq>{url.get('changefreq', 'weekly')}</changefreq>\n"
            xml += f"    <priority>{url.get('priority', '0.5')}</priority>\n"
            xml += "  </url>\n"
        xml += "</urlset>"

        logger.info("Sitemap generated: %d URLs", len(urls))
        return xml

    async def generate_robots_txt(self) -> str:
        """Generate robots.txt content."""
        site_url = settings.target_site_url
        return f"""User-agent: *
Allow: /
Disallow: /api/
Disallow: /admin/
Disallow: /dashboard/

User-agent: Googlebot
Allow: /

User-agent: YandexBot
Allow: /

Sitemap: {site_url}/sitemap.xml
Host: {site_url}
"""

    async def _get_published_articles(self) -> list[dict[str, Any]]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(Article)
                .where(Article.status == "published")
                .order_by(Article.published_at.desc())
            )
            return [
                {
                    "slug": a.slug,
                    "published_at": a.published_at.isoformat() if a.published_at else "",
                    "updated_at": a.updated_at.isoformat() if a.updated_at else "",
                    "geo_score": a.geo_score,
                }
                for a in result.scalars().all()
            ]
