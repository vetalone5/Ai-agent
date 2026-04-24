"""Seed initial competitors for spioniro.ru."""
import asyncio

from sqlalchemy import select

from src.db.session import async_session_factory
from src.models.site_audit import Competitor

SEED_COMPETITORS = [
    ("brand24.com", "Brand24", "https://brand24.com/blog", "International brand monitoring"),
    ("mention.com", "Mention", "https://mention.com/en/blog", "Social media monitoring"),
    ("brandanalytics.ru", "Brand Analytics", "https://brandanalytics.ru/blog", "Russian brand analytics"),
    ("semanticforce.net", "SemanticForce", "https://semanticforce.net/blog", "AI-powered brand monitoring"),
    ("youscan.io", "YouScan", "https://youscan.io/blog", "Social listening platform"),
]


async def seed() -> None:
    async with async_session_factory() as session:
        for domain, name, blog_url, notes in SEED_COMPETITORS:
            existing = await session.execute(
                select(Competitor).where(Competitor.domain == domain)
            )
            if existing.scalar_one_or_none():
                continue
            comp = Competitor(domain=domain, name=name, blog_url=blog_url, notes=notes)
            session.add(comp)
        await session.commit()
        print(f"Seeded {len(SEED_COMPETITORS)} competitors")


if __name__ == "__main__":
    asyncio.run(seed())
