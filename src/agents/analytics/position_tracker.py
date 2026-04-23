import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.constants import SearchEngine
from src.models.keyword import Keyword, Position
from src.tools.google_search_console import GoogleSearchConsoleClient
from src.tools.yandex_webmaster import YandexWebmasterClient

logger = logging.getLogger(__name__)


class PositionTracker:
    def __init__(self, session_factory: Any) -> None:
        self._session_factory = session_factory
        self._gsc = GoogleSearchConsoleClient()
        self._ywm = YandexWebmasterClient()

    async def collect_positions(self) -> dict[str, int]:
        """Collect positions from both search engines. Returns counts."""
        counts = {"yandex": 0, "google": 0}

        try:
            yandex_data = await self._collect_yandex()
            counts["yandex"] = len(yandex_data)
        except Exception as e:
            logger.error("Failed to collect Yandex positions: %s", e)

        try:
            google_data = await self._collect_google()
            counts["google"] = len(google_data)
        except Exception as e:
            logger.error("Failed to collect Google positions: %s", e)

        logger.info("Positions collected: Yandex=%d, Google=%d", counts["yandex"], counts["google"])
        return counts

    async def _collect_yandex(self) -> list[dict[str, Any]]:
        raw = await self._ywm.get_search_queries()
        parsed = self._ywm.parse_query_rows(raw)
        await self._save_positions(parsed, SearchEngine.YANDEX)
        return parsed

    async def _collect_google(self) -> list[dict[str, Any]]:
        raw = await self._gsc.get_search_analytics()
        parsed = self._gsc.parse_analytics_rows(raw)
        await self._save_positions(parsed, SearchEngine.GOOGLE)
        return parsed

    async def _save_positions(
        self, data: list[dict[str, Any]], engine: SearchEngine
    ) -> None:
        async with self._session_factory() as session:
            for row in data:
                query_text = row.get("query", "")
                if not query_text:
                    continue

                keyword = await self._get_or_create_keyword(session, query_text)

                position = Position(
                    keyword_id=keyword.id,
                    search_engine=engine,
                    position=int(row.get("position", row.get("avg_position", 0))),
                    url=row.get("page", row.get("url", "")),
                    clicks=int(row.get("clicks", 0)),
                    impressions=int(row.get("impressions", 0)),
                    ctr=float(row.get("ctr", 0)),
                )
                session.add(position)

            await session.commit()

    @staticmethod
    async def _get_or_create_keyword(session: AsyncSession, query: str) -> Keyword:
        result = await session.execute(select(Keyword).where(Keyword.query == query))
        keyword = result.scalar_one_or_none()
        if not keyword:
            keyword = Keyword(query=query, source="search_console")
            session.add(keyword)
            await session.flush()
        return keyword

    async def get_top_positions(self, engine: SearchEngine, limit: int = 50) -> list[dict[str, Any]]:
        """Get current top positions."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(Position)
                .where(Position.search_engine == engine)
                .order_by(Position.created_at.desc())
                .limit(limit)
            )
            positions = result.scalars().all()
            return [
                {
                    "keyword_id": p.keyword_id,
                    "position": p.position,
                    "url": p.url,
                    "clicks": p.clicks,
                    "impressions": p.impressions,
                    "ctr": p.ctr,
                }
                for p in positions
            ]
