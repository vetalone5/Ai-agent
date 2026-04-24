"""Yandex.Dzen cross-posting for traffic diversification."""

import logging
from typing import Any

import httpx

from src.config.constants import Platform

logger = logging.getLogger(__name__)


class DzenPublisher:
    """Cross-posts articles to Yandex.Dzen for traffic diversification.

    Yandex penalizes sites dependent on a single traffic source.
    Dzen (DA>80, 50M+ monthly uniques) provides both traffic and link equity.
    """

    def __init__(self, api_token: str = "") -> None:
        self._token = api_token
        self._http = httpx.AsyncClient(timeout=30.0)

    async def publish(self, article: dict[str, Any]) -> dict[str, Any]:
        """Adapt and publish article to Dzen.

        Dzen style: clickbait title, short paragraphs, conversational,
        focus on readability (дочитываемость).
        """
        adapted = self._adapt_for_dzen(article)

        if not self._token:
            logger.info("Dzen: dry run (no token). Would publish: %s", adapted["title"][:60])
            return {"status": "dry_run", "title": adapted["title"], "platform": Platform.DZEN}

        try:
            resp = await self._http.post(
                "https://dzen.ru/api/v1/editor/publication",
                headers={"Authorization": f"OAuth {self._token}"},
                json={
                    "title": adapted["title"],
                    "content": adapted["content"],
                    "type": "article",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            logger.info("Dzen: published '%s' → %s", adapted["title"][:40], data.get("url", ""))
            return {"status": "published", "url": data.get("url"), "platform": Platform.DZEN}
        except Exception as e:
            logger.error("Dzen publish failed: %s", e)
            return {"status": "error", "error": str(e), "platform": Platform.DZEN}

    def _adapt_for_dzen(self, article: dict[str, Any]) -> dict[str, Any]:
        """Adapt article for Dzen format."""
        content = article.get("content_md", "")
        title = article.get("title", "")

        paragraphs = content.split("\n\n")
        short_paragraphs = []
        for p in paragraphs:
            p = p.strip()
            if not p:
                continue
            if p.startswith("#"):
                short_paragraphs.append(p)
                continue
            sentences = p.replace(". ", ".\n").split("\n")
            for i in range(0, len(sentences), 2):
                chunk = ". ".join(s.strip() for s in sentences[i:i+2] if s.strip())
                if chunk:
                    short_paragraphs.append(chunk)

        adapted_content = "\n\n".join(short_paragraphs[:40])

        utm_source = "dzen"
        site_url = article.get("published_url", "")
        if site_url:
            cta = f"\n\n---\nПолная версия статьи: [{title}]({site_url}?utm_source={utm_source}&utm_medium=content)"
            adapted_content += cta

        return {"title": title, "content": adapted_content}
