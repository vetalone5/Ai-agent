"""Platform finder: discovers relevant sites for link placement."""

import logging
from typing import Any

from sqlalchemy import select

from src.models.backlink import Backlink
from src.models.site_audit import Competitor

logger = logging.getLogger(__name__)

RUSSIAN_EXCHANGES = [
    {"name": "GoGetLinks", "type": "exchange", "url": "https://gogetlinks.net", "strength": "manual selection, format control"},
    {"name": "Miralinks", "type": "exchange", "url": "https://miralinks.ru", "strength": "49K+ donors, strict moderation"},
    {"name": "SAPE", "type": "exchange", "url": "https://sape.ru", "strength": "huge base, rental links"},
    {"name": "Kwork", "type": "marketplace", "url": "https://kwork.ru", "strength": "link services marketplace"},
    {"name": "Rookee", "type": "automated", "url": "https://rookee.ru", "strength": "automated platform"},
]

CONTENT_PLATFORMS = [
    {"name": "VC.ru", "domain": "vc.ru", "da": 85, "style": "expert", "audience": "3-10K/article"},
    {"name": "Яндекс.Дзен", "domain": "dzen.ru", "da": 90, "style": "conversational", "audience": "100K-1M"},
    {"name": "Хабр", "domain": "habr.com", "da": 88, "style": "technical", "audience": "5-50K/article"},
    {"name": "Яндекс.Кью", "domain": "yandex.ru/q", "da": 92, "style": "expert_answers", "audience": "varies"},
    {"name": "Pikabu", "domain": "pikabu.ru", "da": 80, "style": "casual", "audience": "10-100K"},
]


class PlatformFinder:
    def __init__(self, session_factory: Any, claude_client: Any) -> None:
        self._session_factory = session_factory
        self._claude = claude_client

    async def find_platforms(self, keyword: str, content_type: str = "guide") -> dict[str, Any]:
        """Find best platforms for distributing content on a given topic."""
        competitor_backlinks = await self._get_competitor_domains()

        prompt = f"""Тема статьи: {keyword}
Тип контента: {content_type}

Доступные площадки для размещения:
{self._format_platforms()}

Домены конкурентов с бэклинками: {competitor_backlinks[:10]}

Выбери 3-5 лучших площадок для размещения этого контента.
Для каждой укажи: название, почему подходит, рекомендуемый формат.
Ответь JSON: {{"platforms": [{{"name": "...", "reason": "...", "format": "..."}}]}}"""

        response = await self._claude.complete(
            system_prompt="Ты — SEO-специалист по линкбилдингу в России.",
            user_prompt=prompt,
            max_tokens=800,
        )
        return {"keyword": keyword, "recommendations": response, "exchanges": RUSSIAN_EXCHANGES}

    async def get_donor_criteria(self) -> dict[str, Any]:
        """Return quality criteria for link donors."""
        return {
            "trust_score_min": 30,
            "traffic_min": 500,
            "thematic_relevance": True,
            "checktrust_source": "checktrust.ru",
            "avoid": ["PBN", "link farms", "unmoderated forums", "sites with <100 pages"],
        }

    async def _get_competitor_domains(self) -> list[str]:
        async with self._session_factory() as session:
            result = await session.execute(select(Competitor.domain).limit(10))
            return [r[0] for r in result.all()]

    @staticmethod
    def _format_platforms() -> str:
        lines = []
        for p in CONTENT_PLATFORMS:
            lines.append(f"- {p['name']} (DA={p['da']}, стиль: {p['style']}, охват: {p['audience']})")
        return "\n".join(lines)
