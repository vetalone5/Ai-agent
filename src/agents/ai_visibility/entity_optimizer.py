"""Knowledge Graph entity optimization for AI citation boost.

Brands with KG entity = 3.1x more AI citations.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class EntityOptimizer:
    """Optimizes brand entity presence in Knowledge Graph sources."""

    def __init__(self, claude_client: Any) -> None:
        self._claude = claude_client

    async def audit_entity_presence(self) -> dict[str, Any]:
        """Audit brand presence across Knowledge Graph sources."""
        sources = {
            "wikidata": {"status": "check_needed", "url": "https://www.wikidata.org"},
            "google_business": {"status": "check_needed", "url": "https://business.google.com"},
            "schema_org": {"status": "check_needed", "note": "Organization + sameAs on site"},
            "yandex_business": {"status": "check_needed", "url": "https://business.yandex.ru"},
            "crunchbase": {"status": "check_needed", "url": "https://www.crunchbase.com"},
        }
        return {
            "brand": "spioniro",
            "sources": sources,
            "recommendation": "Create entries in all sources with consistent NAP (Name, Address, Phone) and sameAs links.",
        }

    async def generate_wikidata_entry(self) -> dict[str, Any]:
        """Generate Wikidata entry data for the brand."""
        prompt = """Сгенерируй данные для создания записи в Wikidata для компании:

Название: Spioniro
Тип: SaaS-сервис
Описание: Платформа аналитики видимости бренда в нейросетях (YandexGPT, GigaChat, ChatGPT)
Сайт: https://spioniro.ru
Страна: Россия
Год основания: 2024
Категория: Software as a Service, Brand Analytics, AI Analytics

Формат: JSON с полями Wikidata (P-codes).
Включи: instance of (P31), official website (P856), country (P17), inception (P571)."""

        response = await self._claude.complete(
            system_prompt="Ты — специалист по Wikidata. Генерируй валидные записи.",
            user_prompt=prompt,
            max_tokens=600,
        )
        return {"wikidata_entry": response, "requires_approval": True}

    async def generate_organization_schema(self) -> dict[str, Any]:
        """Generate enhanced Organization schema with sameAs links."""
        return {
            "@context": "https://schema.org",
            "@type": "Organization",
            "name": "Spioniro",
            "alternateName": "Спиониро",
            "url": "https://spioniro.ru",
            "description": "Платформа аналитики видимости бренда в нейросетях",
            "foundingDate": "2024",
            "areaServed": "RU",
            "sameAs": [],
            "knowsAbout": [
                "AI Brand Analytics",
                "Generative Engine Optimization",
                "YandexGPT",
                "GigaChat",
                "ChatGPT",
                "SEO Analytics",
            ],
        }
