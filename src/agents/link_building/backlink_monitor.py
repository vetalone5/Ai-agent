"""Backlink health monitoring."""

import logging
from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy import select, update

from src.models.backlink import Backlink

logger = logging.getLogger(__name__)


class BacklinkMonitor:
    """Monitors health of acquired backlinks: alive, trust score, relevance."""

    def __init__(self, session_factory: Any) -> None:
        self._session_factory = session_factory
        self._http = httpx.AsyncClient(timeout=15.0, follow_redirects=True)

    async def check_all_backlinks(self) -> dict[str, Any]:
        """Check all tracked backlinks for health."""
        backlinks = await self._get_backlinks()
        alive, dead, errors = 0, 0, 0

        for bl in backlinks:
            try:
                status = await self._check_link(bl["source_url"], bl["target_url"])
                if status == "alive":
                    alive += 1
                else:
                    dead += 1
                    await self._update_status(bl["id"], "dead")
            except Exception:
                errors += 1

        logger.info("Backlink check: %d alive, %d dead, %d errors (of %d)",
                     alive, dead, errors, len(backlinks))
        return {"total": len(backlinks), "alive": alive, "dead": dead, "errors": errors}

    async def add_backlink(
        self,
        source_url: str,
        target_url: str,
        anchor_text: str,
        platform: str,
    ) -> int:
        """Register a new backlink for tracking."""
        from urllib.parse import urlparse
        domain = urlparse(source_url).netloc

        async with self._session_factory() as session:
            bl = Backlink(
                source_url=source_url,
                source_domain=domain,
                target_url=target_url,
                anchor_text=anchor_text,
                platform=platform,
                status="active",
            )
            session.add(bl)
            await session.commit()
            await session.refresh(bl)
            return bl.id

    async def _check_link(self, source_url: str, target_url: str) -> str:
        """Check if source_url still contains a link to target_url."""
        try:
            resp = await self._http.get(source_url)
            if resp.status_code >= 400:
                return "dead"
            if target_url in resp.text or "spioniro.ru" in resp.text:
                return "alive"
            return "link_removed"
        except Exception:
            return "error"

    async def _get_backlinks(self) -> list[dict[str, Any]]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(Backlink).where(Backlink.status.in_(["active", "pending"]))
            )
            return [
                {"id": b.id, "source_url": b.source_url, "target_url": b.target_url,
                 "source_domain": b.source_domain, "status": b.status}
                for b in result.scalars().all()
            ]

    async def _update_status(self, backlink_id: int, status: str) -> None:
        async with self._session_factory() as session:
            await session.execute(
                update(Backlink).where(Backlink.id == backlink_id).values(
                    status=status, updated_at=datetime.now(timezone.utc)
                )
            )
            await session.commit()
