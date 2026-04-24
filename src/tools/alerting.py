"""Monitoring and alerting: Telegram notifications for critical events."""

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class TelegramAlerter:
    """Sends alerts to Telegram for critical SEO events."""

    def __init__(self, bot_token: str = "", chat_id: str = "") -> None:
        self._bot_token = bot_token
        self._chat_id = chat_id
        self._http = httpx.AsyncClient(timeout=10.0)

    async def send(self, message: str, level: str = "info") -> bool:
        if not self._bot_token or not self._chat_id:
            logger.debug("Telegram not configured, skipping alert: %s", message[:80])
            return False

        emoji = {"critical": "⚠️", "warning": "⚠️", "info": "ℹ️", "success": "✅"}.get(level, "ℹ️")
        text = f"{emoji} *SEO Agents*\n\n{message}"

        try:
            resp = await self._http.post(
                f"https://api.telegram.org/bot{self._bot_token}/sendMessage",
                json={"chat_id": self._chat_id, "text": text, "parse_mode": "Markdown"},
            )
            return resp.status_code == 200
        except Exception as e:
            logger.error("Telegram alert failed: %s", e)
            return False


class AlertManager:
    """Centralized alert manager that decides when and what to alert."""

    def __init__(self, telegram: TelegramAlerter) -> None:
        self._tg = telegram

    async def on_position_drop(self, keyword: str, old_pos: int, new_pos: int, engine: str) -> None:
        drop = new_pos - old_pos
        if drop >= 10:
            await self._tg.send(
                f"*Position Drop* ({engine})\n"
                f"Keyword: `{keyword}`\n"
                f"Position: {old_pos} -> {new_pos} (drop: {drop})",
                level="critical",
            )

    async def on_traffic_anomaly(self, metric: str, value: float, threshold: float) -> None:
        await self._tg.send(
            f"*Traffic Anomaly*\n"
            f"Metric: {metric}\n"
            f"Value: {value:.1f} (threshold: {threshold:.1f})",
            level="warning",
        )

    async def on_article_published(self, title: str, url: str) -> None:
        await self._tg.send(
            f"*Article Published*\n"
            f"Title: {title}\n"
            f"URL: {url}",
            level="success",
        )

    async def on_task_failed(self, task_id: int, task_type: str, error: str) -> None:
        await self._tg.send(
            f"*Task Failed*\n"
            f"ID: {task_id}\n"
            f"Type: {task_type}\n"
            f"Error: {error[:200]}",
            level="critical",
        )

    async def on_weekly_report(self, summary: str) -> None:
        await self._tg.send(f"*Weekly Report*\n\n{summary[:500]}", level="info")

    async def on_indexing_complete(self, url: str, results: dict[str, Any]) -> None:
        engines = ", ".join(f"{k}: {'OK' if v else 'FAIL'}" for k, v in results.items())
        await self._tg.send(
            f"*Indexing Submitted*\n"
            f"URL: {url}\n"
            f"Results: {engines}",
            level="info",
        )
