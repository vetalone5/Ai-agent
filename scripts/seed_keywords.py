"""Seed initial keywords for spioniro.ru SEO tracking."""
import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import async_session_factory
from src.models.keyword import Keyword

SEED_KEYWORDS = [
    ("аналитика упоминаний бренда в нейросетях", 320, "commercial"),
    ("мониторинг упоминаний в ai", 180, "commercial"),
    ("как узнать что говорит chatgpt о бренде", 210, "informational"),
    ("аналитика yandex gpt упоминания", 150, "commercial"),
    ("мониторинг бренда в gigachat", 90, "commercial"),
    ("seo аналитика ai поиск", 120, "informational"),
    ("видимость бренда в ней��осетях", 260, "commercial"),
    ("geo оптимизация", 440, "informational"),
    ("generative engine optimization", 580, "informational"),
    ("как попасть в ответы яндекс нейро", 310, "informational"),
    ("оптимизация для ai overviews", 240, "informational"),
    ("аналитика ai упоминаний конкурентов", 70, "commercial"),
    ("что такое geo оптимизац��я", 190, "informational"),
    ("мониторинг ai выдачи", 130, "commercial"),
    ("seo для нейросе��ей", 350, "informational"),
    ("как продвигаться в chatgpt", 280, "informational"),
    ("аналитика бренда yandex gpt gigachat chatgpt", 60, "commercial"),
    ("spioniro аналитика", 40, "navigational"),
    ("ai brand monitoring tool", 220, "commercial"),
    ("сервис аналитики ai упоминаний", 100, "commercial"),
]


async def seed() -> None:
    async with async_session_factory() as session:
        for query, freq, intent in SEED_KEYWORDS:
            existing = await session.execute(select(Keyword).where(Keyword.query == query))
            if existing.scalar_one_or_none():
                continue
            kw = Keyword(query=query, frequency=freq, intent=intent, source="seed")
            session.add(kw)
        await session.commit()
        print(f"Seeded {len(SEED_KEYWORDS)} keywords")


if __name__ == "__main__":
    asyncio.run(seed())
